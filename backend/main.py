import joblib
import os
import asyncio
import numpy as np
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, text

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agente', 'rag_agent'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'agente', 'rag_agent', '.env'))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from agent import root_agent

class MarketShareModel(BaseModel):
    antiguedad_marca: int
    participacion_mercado_promedio: float
    calificacion_promedio_productos: float
    numero_leads_web: int
    numero_devoluciones: int
    participacion_mercado: float
    ingresos: float
    ventas_totales: float
    sector: str = "OTRO"

class MarketShareBatchModel(BaseModel):
    total_sales: float
    revenue: float
    antiguedad_de_la_marca: float
    numero_de_leads_en_web: float
    calificacion_promedio_de_productos: float
    numero_de_devoluciones: float
    participacion_de_mercado: float
    avg_market_share: float
    crecimiento_total_sales: float
    pct_costo: float
    costo_ops_total: float
    margen_neto_marca: float
    revenue_por_lead: float
    ratio_devolucion_revenue: float
    roi_marca: float
    ratio_dev_revenue: float

class ChatModel(BaseModel):
    mensaje: str

engine = create_engine(
    "postgresql+psycopg2://anakaren:Cupcake005@127.0.0.1:5432/LiverpoolT3"
)

APP_NAME = "liverpool_backend_chatbot"
USER_ID = "backend_user"
SESSION_ID = "backend_session"

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = joblib.load("random_fores_equipo3nuevo.joblib")
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    print("Modelo cargado y sesión del agente creada.")
    yield
    print("Servidor apagado.")

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def asignar_porcentaje_cogs(texto):
    texto = str(texto).upper()
    if "PUBLICIDAD" in texto or "GESTION" in texto or "ADMINISTRACION" in texto or "TRABAJOS DE OFICINA" in texto:
        return 0.15
    elif "PRENDAS DE VESTIR" in texto or "VESTUARIO" in texto or "CALZADO" in texto or "SOMBRERERIA" in texto:
        return 0.42
    elif "JOYERIA" in texto or "RELOJERIA" in texto or "METALES PRECIOSOS" in texto:
        return 0.55
    elif "ALIMENTOS" in texto or "LIMPIEZA" in texto or "FERRETERIA" in texto or "VELAS" in texto:
        return 0.60
    else:
        return 0.48

@app.post("/predict-market-share")
async def post_predict_market_share(data: MarketShareModel):
    pct_costo = asignar_porcentaje_cogs(data.sector)
    costo_por_pieza = 65 if data.calificacion_promedio_productos < 3.0 else 30
    costo_ops_total = (data.ingresos * pct_costo) + (data.ventas_totales * costo_por_pieza)
    margen_neto_marca = (data.ingresos - costo_ops_total) / data.ingresos if data.ingresos > 0 else 0.0
    roi_marca = (data.ingresos - costo_ops_total) / (costo_ops_total + 1)
    revenue_por_lead = data.ingresos / (data.numero_leads_web + 1)
    ratio_dev_revenue = data.numero_devoluciones / (data.ingresos + 1)

    registro_marca = {
        'total_sales': data.ventas_totales,
        'revenue': data.ingresos,
        'antiguedad_de_la_marca': data.antiguedad_marca,
        'numero_de_leads_en_web': data.numero_leads_web,
        'calificacion_promedio_de_productos': data.calificacion_promedio_productos,
        'numero_de_devoluciones': data.numero_devoluciones,
        'participacion_de_mercado_(%)': data.participacion_mercado,
        'avg_market_share': data.participacion_mercado_promedio,
        'crecimiento_total_sales': data.ventas_totales,
        'pct_costo': pct_costo,
        'costo_ops_total': costo_ops_total,
        'margen_neto_marca': margen_neto_marca,
        'revenue_por_lead': revenue_por_lead,
        'ratio_devolucion_revenue': ratio_dev_revenue,
        'roi_marca': roi_marca,
        'ratio_dev_revenue': ratio_dev_revenue
    }
    prediccion = app.state.model.predict(np.array(list(registro_marca.values())).reshape(1, -1))
    return {"renovacion": int(prediccion[0])}

@app.post("/predict-batch")
async def post_predict_batch(data: MarketShareBatchModel):
    valores = [
        data.total_sales,
        data.revenue,
        data.antiguedad_de_la_marca,
        data.numero_de_leads_en_web,
        data.calificacion_promedio_de_productos,
        data.numero_de_devoluciones,
        data.participacion_de_mercado,
        data.avg_market_share,
        data.crecimiento_total_sales,
        data.pct_costo,
        data.costo_ops_total,
        data.margen_neto_marca,
        data.revenue_por_lead,
        data.ratio_devolucion_revenue,
        data.roi_marca,
        data.ratio_dev_revenue
    ]
    prediccion = app.state.model.predict(np.array(valores).reshape(1, -1))
    return {"renovacion": int(prediccion[0])}

@app.get("/marcas/buscar")
async def buscar_marcas(nombre: str = Query(..., min_length=2)):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT denominacion, tipo, clase, estatus_marca,
                           fecha_vencimiento, numero_registro
                    FROM "Marcas"
                    WHERE LOWER(denominacion) LIKE LOWER(:nombre)
                    ORDER BY denominacion, clase
                """),
                {"nombre": f"%{nombre}%"}
            )
            rows = [dict(row._mapping) for row in result]

        agrupadas = {}
        for row in rows:
            key = row["denominacion"]
            if key not in agrupadas:
                agrupadas[key] = {
                    "denominacion": row["denominacion"],
                    "tipo": row["tipo"],
                    "estatus_marca": row["estatus_marca"],
                    "fecha_vencimiento": str(row["fecha_vencimiento"]) if row["fecha_vencimiento"] else None,
                    "numero_registro": row["numero_registro"],
                    "clases": []
                }
            if row["clase"]:
                agrupadas[key]["clases"].append(row["clase"])

        return list(agrupadas.values())
    except Exception as e:
        return {"error": str(e)}

@app.post("/bolo/chat")
async def chat_bolo(data: ChatModel):
    try:
        content = genai_types.Content(role="user", parts=[genai_types.Part(text=data.mensaje)])
        final_response = ""

        async def run_agent():
            nonlocal final_response
            async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text

        await asyncio.wait_for(run_agent(), timeout=120)
        return {"respuesta": final_response or "No recibí respuesta del agente."}
    except asyncio.TimeoutError:
        return {"respuesta": "Lo siento, la consulta tardó demasiado. Intenta con una pregunta más específica."}
    except Exception as e:
        import traceback
        print("ERROR EN BOLO CHAT:", traceback.format_exc())
        return {"error": str(e), "detalle": traceback.format_exc()}

@app.get("/metricas/resumen")
async def get_metricas_resumen():
    try:
        with engine.connect() as conn:
            r1 = conn.execute(text('SELECT COUNT(*) FROM "Marcas" WHERE estatus_marca = \'Vigente\''))
            marcas_vigentes = r1.fetchone()[0]
            r2 = conn.execute(text('SELECT COUNT(DISTINCT clase) FROM "Marcas" WHERE clase IS NOT NULL'))
            clases = r2.fetchone()[0]
            hoy = date.today()
            en_90 = hoy + timedelta(days=90)
            r3 = conn.execute(text('SELECT COUNT(*) FROM "Marcas" WHERE estatus_marca = \'Vigente\' AND fecha_vencimiento >= :hoy AND fecha_vencimiento <= :en_90'), {"hoy": hoy, "en_90": en_90})
            por_vencer = r3.fetchone()[0]
        return {"marcas_vigentes": marcas_vigentes, "clases": clases, "por_vencer_90_dias": por_vencer, "precision_modelo": 96}
    except Exception as e:
        return {"error": str(e)}

app.mount("/", StaticFiles(directory="../html", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)