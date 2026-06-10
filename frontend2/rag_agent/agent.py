import os
import io
import asyncio
from datetime import datetime
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.adk.agents import Agent
from pinecone import Pinecone
from google.api_core import retry

from sqlalchemy import create_engine, text

engine = create_engine(
    "postgresql+psycopg2://anakaren:Cupcake005@127.0.0.1:5432/LiverpoolT3"
)

is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})

genai.models.Models.generate_content = retry.Retry(
    predicate=is_retriable)(genai.models.Models.generate_content)

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

AGENT_MODEL = "gemini-1.5-flash-8b"
#AGENT_MODEL = "ollama/gemma3"
#EMBEDDING_MODEL = "ollama/embeddinggemma"


llm_client = genai.Client(api_key=google_api_key)

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index("litigiosagente")

def GeminiEmbeddingFunction(texts, embedding_task):
    response = llm_client.models.embed_content(
        model="models/text-embedding-004",
        #model=LiteLlm(EMBEDDING_MODEL),
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=embedding_task,
            output_dimensionality=1024, # Sin comillas, es un entero
        ),
    )
    return [e.values for e in response.embeddings]

def pinecone_search(query: str) -> str:
    """
    Busca en la base de datos interna información relevante sobre una consulta.
    Retorna el texto encontrado para que el agente lo analice.
    """
    query_embedding = GeminiEmbeddingFunction([query], "RETRIEVAL_QUERY")[0]
    results = index.query(vector=query_embedding, top_k=3, include_metadata=True)
    
    relevant_documents = [match['metadata'].get('page_content', '') for match in results['matches'] if match['metadata'].get('page_content')]
    # IMPORTANTE: Devolvemos un solo string con todo el contexto
    return "\n\n".join(relevant_documents)


def postgres_search(sql_query: str) -> str:
    """
    Ejecuta consultas SQL generadas por el modelo
    en la base de datos de Liverpool.
    """
    try:
        sql_query = sql_query.replace("FROM Ventas", 'FROM "Ventas"')
        sql_query = sql_query.replace("JOIN Ventas", 'JOIN "Ventas"')
        
        sql_query = sql_query.replace("FROM Marcas", 'FROM "Marcas"')
        sql_query = sql_query.replace("JOIN Marcas", 'JOIN "Marcas"')
        
        sql_query = sql_query.replace("FROM Costos", 'FROM "Costos"')
        sql_query = sql_query.replace("JOIN Costos", 'JOIN "Costos"')
        
        with engine.connect() as connection:
            # Ejecutamos la consulta
            result = connection.execute(text(sql_query))

            # Si es una consulta SELECT, obtenemos los datos
            if result.returns_rows:
                rows = [dict(row._mapping) for row in result]

                if not rows:
                    return "La consulta se ejecutó con éxito pero no devolvió resultados."

                return f"Resultados encontrados:\n{str(rows)}"

            return "Consulta ejecutada con éxito."

    except Exception as e:
        return f"Error en la base de datos: {str(e)}"



async def ingest_uploaded_file(tool_context, department: str = "Legal") -> str:
    """Retrieves the file, extracts original name, and indexes it into Pinecone."""
    

    display_name = None
    found_part = None

    for part in tool_context.user_content.parts:
        
        if hasattr(part, 'file_data') and part.file_data:
            found_part = part
        
            if part.file_data.file_uri:
                display_name = part.file_data.file_uri.split('/')[-1]
            break
        elif hasattr(part, 'inline_data') and part.inline_data:
            found_part = part
            break

    if not found_part:
        
        artifact_names = await tool_context.list_artifacts()
        if not artifact_names:
            return "No files found to process. Please upload a document."
        display_name = artifact_names[-1]
    else:
      
        final_save_name = display_name or f"upload_{datetime.now().strftime('%H%M%S')}.pdf"
        await tool_context.save_artifact(final_save_name, found_part)
        display_name = final_save_name

    artifact = await tool_context.load_artifact(display_name)
    raw_data = artifact.inline_data.data

   
    full_text = ""
    try:
        pdf_stream = io.BytesIO(raw_data)
        reader = PdfReader(pdf_stream)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"

    # Chunking and Pinecone Upsert with Metadata
    chunk_size = 1000
    overlap = 200
    text_chunks = [full_text[i : i + chunk_size] for i in range(0, len(full_text), chunk_size - overlap)]

    for i in range(0, len(text_chunks), 32):
        batch = text_chunks[i : i + 32]
        embeddings = GeminiEmbeddingFunction(batch, "RETRIEVAL_DOCUMENT")

        vectors = []
        for j, (text, embed) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id": f"{display_name}-{i+j}",
                "values": embed,
                "metadata": {
                    "page_content": text,
                    "source": display_name, # Original filename is now here
                    "dept": department
                }
            })
        index.upsert(vectors=vectors)

    return f"Successfully indexed '{display_name}' into the database."


async def routing_callback(callback_context, **kwargs):
    """Detects uploads in the user message to route to the Librarian."""
    user_content = callback_context.user_content
    
    # Check for file parts in the current message
    has_file = any(part.inline_data or part.file_data for part in user_content.parts)

    if has_file:
        callback_context.next_agent = "Librarian"
    else:
        callback_context.next_agent = "Researcher"
    return


librarian_agent = Agent(
    name="Librarian",
    instruction="Index the user's uploaded file into Pinecone using the ingest tool.",
    tools=[ingest_uploaded_file]
)

researcher_agent = Agent(
    name="Researcher",
    instruction="You are a retrieval expert. Use the pinecone_search tool to find exact info in Pinecone.",
    tools=[pinecone_search]
)

postgres_agent = Agent(
    name="PostgresConsultant",
    instruction="""
    You are a PostgreSQL database expert.

Your job is to answer questions about the internal business database.

You specialize in:
- Querying PostgreSQL databases
- Understanding business metrics
- Analyzing brand, sales, and cost information

WORKFLOW — always follow these steps in order:

1. Translate the user's natural language question into a PostgreSQL SQL query.

2. Take the exact SQL query returned by traductorSQL and pass it directly to postgres_search.

3. Present the results clearly and concisely to the user.

RULES — WORKFLOW:
- Never skip traductorSQL — always translate first.
- Always pass the SQL generated by traductorSQL directly to postgres_search without modifying it.
- If traductorSQL returns an error, inform the user and ask them to rephrase the question.

DATABASE CONTEXT:

Tables and relationships:

{
    'Marcas': [],

    'Ventas': [
        {
            'table': 'Marcas',
            'from_column': 'numero_registro',
            'to_column': 'numero_registro'
        }
    ],

    'Costos': [
        {
            'table': 'Marcas',
            'from_column': 'numero_registro',
            'to_column': 'numero_registro'
        }
    ]
}

Table schemas:

{
    'Marcas': {
        'expediente': 'integer',
        'denominacion': 'text',
        'tipo': 'text',
        'numero_registro': 'text',
        'clase': 'text',
        'descripcion': 'text',
        'fecha_presentacion': 'date',
        'estatus_tramite': 'text',
        'estatus_marca': 'text',
        'fecha_vencimiento': 'date',
        'fecha_concesion': 'date'
    },

    'Ventas': {
        'denominacion': 'text',
        'descripcion': 'text',
        'numero_registro': 'text',
        'fecha': 'date',
        'ventas_totales': 'float',
        'ingresos': 'float',
        'antiguedad_marca': 'integer',
        'numero_leads_web': 'integer',
        'calificacion_promedio_productos': 'float',
        'numero_devoluciones': 'integer',
        'renovo': 'boolean',
        'participacion_mercado': 'float',
        'participacion_mercado_promedio': 'float',
        'r_devoluciones': 'float',
        'r_leads': 'float',
        'r_ingresoxventa': 'float',
        'r_crecimiento': 'float',
        'r_roi': 'float'
    },

    'Costos': {
        'denominacion': 'text',
        'numero_registro': 'text',
        'fecha_costo': 'date',
        'costo_renovacion_IMPI': 'float',
        'costo_dec_uso_IMPI': 'float',
        'honorarios_legales_renov': 'float',
        'honorarios_legales_dec': 'float'
    }
}

SQL RULES:
- Generate ONLY PostgreSQL SELECT queries.
- NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.
- Use table names exactly as written:
  "Marcas"
  "Ventas"
  "Costos"
- Use joins when necessary based on relationships.
- Return ONLY the SQL query.
- Skip explanations, markdown, comments and extra text.
- Do not modify the SQL returned by traductorSQL.
- Present final answers using the results returned from postgres_search.
- If a question cannot be translated into a valid SQL query, explain the issue and ask the user to rephrase.
- Always prioritize accurate database retrieval over assumptions.

OUTPUT RULE:
Return only the SQL query when translating. Skip pre- and post-text.
""",
    
    tools=[postgres_search]
)

root_agent = Agent(
    name="Orchestrator",
    model=AGENT_MODEL,
    #model=LiteLlm(AGENT_MODEL),
    instruction="""
You are the system coordinator responsible for routing user requests to the appropriate sub-agent.

Analyze the user's input and follow these rules in order:

1. FILE UPLOAD DETECTION
   - If the user uploaded a file or document, delegate to the 'Librarian' sub-agent.

2. DATABASE / SQL DETECTION
   - If the user asks about SQL, PostgreSQL, database tables, schemas, records, queries, joins, inserts, updates, deletes, or requests database information, delegate to the 'postgres_agent'.

3. INTERNAL KNOWLEDGE QUESTIONS
   - If the user asks questions about internal company data, uploaded knowledge, documents, or stored information, delegate to the 'Researcher' sub-agent.

4. MULTI-STEP TASKS
   - If the user uploaded a file AND asks questions about it:
        First call 'Librarian'
        Then call 'Researcher'

   - If the user asks about BOTH uploaded/internal information AND database information:
        First call 'postgres_agent'
        Then call 'Researcher'

5. PRIORITY RULE
   - Database-related requests ALWAYS go to 'postgres_agent' before any other agent.

Return only the selected agent(s) and execution order.
""",
    
    sub_agents=[librarian_agent, researcher_agent,postgres_agent],
    before_agent_callback=routing_callback
)