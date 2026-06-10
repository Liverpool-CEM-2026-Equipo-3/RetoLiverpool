import asyncio
import sys
import os
import nest_asyncio
nest_asyncio.apply()
from dotenv import load_dotenv
from agent import root_agent

load_dotenv(os.path.join(os.path.dirname(__file__), 'rag_agent', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag_agent'))

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
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(call_agent_async(message))