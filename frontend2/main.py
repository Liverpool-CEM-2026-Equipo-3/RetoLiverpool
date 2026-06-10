import asyncio
import sys
import os
import dash
from dash import Dash, html, dcc
import diskcache
from dash.background_callback.managers.diskcache_manager import DiskcacheLongCallbackManager

# ─── AGENTE ADK INTEGRADO DIRECTAMENTE ───────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agente', 'rag_agent'))
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import root_agent

APP_NAME = "liverpool_dash_chatbot"
USER_ID = "dash_user"
SESSION_ID = "dash_session"

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)
asyncio.run(
    session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
)

async def call_agent_async(message: str) -> str:
    content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )
    final_response = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
    return final_response or "No recibí respuesta del agente."

def call_agent(message: str) -> str:
    return asyncio.run(call_agent_async(message))

# ─── BACKGROUND CALLBACK MANAGER ─────────────────────────────────────────────
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# ─── APP DASH ─────────────────────────────────────────────────────────────────
external_scripts = [
    {"src": "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"}
]

app = Dash(
    __name__,
    external_scripts=external_scripts,
    use_pages=True,
    title="Liverpool Insights",
    suppress_callback_exceptions=True,
    background_callback_manager=long_callback_manager,
)

header = html.Header(
    className="top-0 z-20 sticky bg-white/90 shadow-sm backdrop-blur",
    children=[
        html.Div(
            className="flex justify-between items-center mx-auto px-6 py-4 max-w-7xl",
            children=[
                html.A(
                    className="font-extrabold text-[#d3196b] text-xl tracking-tight",
                    href="/",
                    children=["Liverpool Insights"],
                ),
                html.Nav(
                    className="hidden md:flex gap-6 font-medium text-[#4a2a4f] text-sm",
                    children=[
                        dcc.Link(className="hover:text-[#d3196b]", href="/", children=["Inicio"]),
                        dcc.Link(className="hover:text-[#d3196b]", href="/predictivo", children=["Predictivo"]),
                        dcc.Link(className="hover:text-[#d3196b]", href="/dashboards", children=["Dashboards"]),
                        dcc.Link(className="hover:text-[#d3196b]", href="/marca", children=["Marca"]),
                    ],
                ),
            ],
        )
    ],
)

footer = html.Footer(
    className="bg-white/90 py-6 border-[#f7c0dd] border-t",
    children=[
        html.Div(
            className="mx-auto px-6 max-w-7xl text-[#6c4a6f] text-sm text-center",
            children=["Proyecto de analítica de datos para Liverpool · Diseñado solamente para Liverpool"],
        )
    ],
)

app.layout = html.Div(
    children=[
        header,
        dash.page_container,
        footer,
    ]
)

if __name__ == "__main__":
    app.run(host="0.0.0.0")