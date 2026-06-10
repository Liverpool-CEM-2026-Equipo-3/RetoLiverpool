import os
import io
import json
from datetime import datetime

import pandas as pd
import psycopg2
import pytesseract

from PIL import Image
from pypdf import PdfReader
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.adk.agents import Agent
from pinecone import Pinecone
from google.api_core import retry


# ======================================================
# RETRY CONFIG
# ======================================================

is_retriable = lambda e: (
    isinstance(e, genai.errors.APIError)
    and e.code in {429, 503}
)

genai.models.Models.generate_content = retry.Retry(
    predicate=is_retriable
)(genai.models.Models.generate_content)


# ======================================================
# ENV
# ======================================================

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


# ======================================================
# MODELS
# ======================================================

AGENT_MODEL = "gemini-2.5-flash"

llm_client = genai.Client(api_key=google_api_key)


# ======================================================
# PINECONE
# ======================================================

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index("litigiosagente")


# ======================================================
# POSTGRES
# ======================================================

def get_postgres_connection():
    return psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )


def execute_sql_query(query: str) -> str:
    """
    Ejecuta SQL SELECT en PostgreSQL.
    """

    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute(query)

        rows = cur.fetchall()

        column_names = [
            desc[0]
            for desc in cur.description
        ]

        results = []

        for row in rows:
            results.append(
                dict(zip(column_names, row))
            )

        cur.close()
        conn.close()

        return json.dumps(
            results,
            default=str,
            ensure_ascii=False,
            indent=2
        )

    except Exception as e:
        return f"SQL Error: {str(e)}"


# ======================================================
# SQL AGENT TOOL
# ======================================================

def postgres_search(question: str) -> str:
    """
    Convierte preguntas de negocio
    a SQL y consulta PostgreSQL.
    """

    prompt = f"""
You are an expert PostgreSQL analyst.

Database schema:

TABLE "Marcas":
- expediente
- denominacion
- tipo
- numero_registro
- clase
- descripcion
- fecha_presentacion
- estatus_tramite
- estatus_marca
- fecha_vencimiento
- fecha_concesion

TABLE "Ventas":
- denominacion
- descripcion
- numero_registro
- fecha
- ventas_totales
- ingresos
- antiguedad_marca
- numero_leads_web
- calificacion_promedio_productos
- numero_devoluciones
- renovo
- participacion_mercado
- participacion_mercado_promedio
- r_devoluciones
- r_leads
- r_ingresoxventa
- r_crecimiento
- r_roi

TABLE "Costos":
- denominacion
- numero_registro
- fecha_costo
- costo_renovacion_IMPI
- costo_dec_uso_IMPI
- honorarios_legales_renov
- honorarios_legales_dec

IMPORTANT RULES:
- ONLY generate PostgreSQL SELECT queries.
- NEVER INSERT, DELETE, UPDATE, DROP.
- ALWAYS use double quotes:
"Marcas"
"Ventas"
"Costos"
- Return ONLY SQL.
- LIMIT results to 20 unless aggregation.

Question:
{question}
"""

    response = llm_client.models.generate_content(
        model=AGENT_MODEL,
        contents=prompt
    )

    sql_query = response.text.strip()

    sql_query = (
        sql_query
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )

    print("\nGenerated SQL:")
    print(sql_query)

    result = execute_sql_query(sql_query)

    return f"""
SQL Used:
{sql_query}

Results:
{result}
"""


# ======================================================
# EMBEDDINGS
# ======================================================

def GeminiEmbeddingFunction(
    texts,
    embedding_task
):
    response = llm_client.models.embed_content(
        model="gemini-embedding-2",
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=embedding_task,
            output_dimensionality=1024
        ),
    )

    return [
        e.values
        for e in response.embeddings
    ]


# ======================================================
# PINECONE SEARCH
# ======================================================

def pinecone_search(
    query: str
) -> str:

    query_embedding = (
        GeminiEmbeddingFunction(
            [query],
            "RETRIEVAL_QUERY"
        )[0]
    )

    results = index.query(
        vector=query_embedding,
        top_k=3,
        include_metadata=True
    )

    docs = []

    for match in results["matches"]:
        docs.append(
            match["metadata"]["page_content"]
        )

    return "\n\n".join(docs)


# ======================================================
# FILE EXTRACTION
# ======================================================

def extract_pdf(raw_data):
    full_text = ""

    pdf_stream = io.BytesIO(raw_data)

    reader = PdfReader(pdf_stream)

    for page in reader.pages:
        text = page.extract_text()

        if text:
            full_text += text + "\n"

    return full_text


def extract_image(raw_data):
    image = Image.open(
        io.BytesIO(raw_data)
    )

    text = pytesseract.image_to_string(
        image
    )

    return text


def extract_excel(raw_data):
    excel_buffer = io.BytesIO(raw_data)

    xls = pd.ExcelFile(
        excel_buffer
    )

    full_text = ""

    for sheet in xls.sheet_names:
        df = pd.read_excel(
            xls,
            sheet_name=sheet
        )

        full_text += (
            f"\n--- {sheet} ---\n"
        )

        full_text += df.to_string(
            index=False
        )

    return full_text


def extract_csv(raw_data):
    csv_buffer = io.BytesIO(raw_data)

    df = pd.read_csv(csv_buffer)

    return df.to_string(
        index=False
    )


# ======================================================
# DOCUMENT INGESTION
# ======================================================

async def ingest_uploaded_file(
    tool_context
) -> str:

    found_part = None
    display_name = None

    for part in (
        tool_context.user_content.parts
    ):

        if (
            hasattr(part, "file_data")
            and part.file_data
        ):
            found_part = part

            if part.file_data.file_uri:
                display_name = (
                    part.file_data.file_uri
                    .split("/")[-1]
                )

            break

        elif (
            hasattr(part, "inline_data")
            and part.inline_data
        ):
            found_part = part
            break

    if not found_part:
        return (
            "No file uploaded."
        )

    final_name = (
        display_name
        or f"upload_"
        f"{datetime.now().strftime('%H%M%S')}"
    )

    await tool_context.save_artifact(
        final_name,
        found_part
    )

    artifact = (
        await tool_context.load_artifact(
            final_name
        )
    )

    raw_data = (
        artifact.inline_data.data
    )

    extension = (
        final_name
        .split(".")[-1]
        .lower()
    )

    try:

        if extension == "pdf":
            full_text = extract_pdf(
                raw_data
            )

        elif extension in [
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "webp"
        ]:
            full_text = extract_image(
                raw_data
            )

        elif extension in [
            "xlsx",
            "xls"
        ]:
            full_text = extract_excel(
                raw_data
            )

        elif extension == "csv":
            full_text = extract_csv(
                raw_data
            )

        else:
            return (
                f"Unsupported file:"
                f" {extension}"
            )

    except Exception as e:
        return (
            f"Extraction error:"
            f" {str(e)}"
        )

    # ==========================================
    # CHUNKING
    # ==========================================

    chunk_size = 1000
    overlap = 200

    chunks = [
        full_text[i:i+chunk_size]
        for i in range(
            0,
            len(full_text),
            chunk_size-overlap
        )
    ]

    for i in range(
        0,
        len(chunks),
        32
    ):

        batch = chunks[i:i+32]

        embeddings = (
            GeminiEmbeddingFunction(
                batch,
                "RETRIEVAL_DOCUMENT"
            )
        )

        vectors = []

        for j, (
            text,
            embed
        ) in enumerate(
            zip(batch, embeddings)
        ):

            vectors.append({
                "id":
                    f"{final_name}-{i+j}",

                "values":
                    embed,

                "metadata": {
                    "page_content":
                        text,

                    "source":
                        final_name
                }
            })

        index.upsert(
            vectors=vectors
        )

    return (
        f"Document '{final_name}' "
        f"indexed successfully."
    )


# ======================================================
# ROUTER
# ======================================================

async def routing_callback(
    callback_context,
    **kwargs
):

    user_content = (
        callback_context.user_content
    )

    has_file = any(
        part.inline_data
        or part.file_data
        for part in user_content.parts
    )

    if has_file:
        callback_context.next_agent = (
            "Librarian"
        )
    else:
        callback_context.next_agent = (
            "Researcher"
        )


# ======================================================
# AGENTS
# ======================================================

librarian_agent = Agent(
    name="Librarian",
    instruction="""
    Index uploaded documents
    into Pinecone.
    """,
    tools=[
        ingest_uploaded_file
    ]
)

researcher_agent = Agent(
    name="Researcher",
    model=AGENT_MODEL,
    instruction="""
You answer questions using:

1. PostgreSQL business database
2. Uploaded document knowledge

For business metrics:
use postgres_search

For uploaded documents:
use pinecone_search

You may combine both.
""",
    tools=[
        postgres_search,
        pinecone_search
    ]
)

root_agent = Agent(
    name="Orchestrator",
    model=AGENT_MODEL,
    instruction="""
If a file is uploaded:
go to Librarian.

Otherwise:
go to Researcher.
""",
    sub_agents=[
        librarian_agent,
        researcher_agent
    ],
    before_agent_callback=
        routing_callback
)