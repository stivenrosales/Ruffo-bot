"""Vercel Serverless Function - Ruffo Chat API."""

import os
import sys

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import structlog
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# Inicializar logger
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()

# Crear app FastAPI
app = FastAPI(
    title="Ruffo Chat API",
    description="API para chatear con Ruffo, el perro rockero de Animalicha",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agente lazy loading (se crea en primera request)
_agent = None


def get_agent():
    """Obtener o crear el agente de Ruffo."""
    global _agent
    if _agent is None:
        logger.info("Initializing Ruffo agent for Vercel...")
        from src.agent.graph import create_ruffo_agent
        _agent = create_ruffo_agent()
        logger.info("Ruffo agent ready!")
    return _agent


class ChatRequest(BaseModel):
    """Request para enviar un mensaje."""
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response del chat."""
    response: str
    thread_id: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para chatear con Ruffo.
    """
    try:
        agent = get_agent()

        # Generar thread_id si no existe
        thread_id = request.thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": f"vercel-{thread_id}"}}

        logger.info(
            "Chat request received",
            thread_id=thread_id,
            message=request.message[:50]
        )

        # Invocar el agente
        result = agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config
        )

        # Extraer respuesta del agente
        response = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, 'tool_calls', None):
                response = msg.content
                break

        if not response:
            response = "🐕 ¡Guau! Tuve un problemita. ¿Puedes repetirme eso?"

        logger.info(
            "Chat response generated",
            thread_id=thread_id,
            response_length=len(response)
        )

        return ChatResponse(response=response, thread_id=thread_id)

    except Exception as e:
        logger.error("Error in chat endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "agent": "ruffo", "platform": "vercel"}


# Handler para Vercel
handler = app
