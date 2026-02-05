"""API FastAPI para el chat de Ruffo."""

import uuid
import structlog
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.graph import create_ruffo_agent

logger = structlog.get_logger()

# Crear app FastAPI
app = FastAPI(
    title="Ruffo Chat API",
    description="API para chatear con Ruffo, el perro rockero de Animalicha",
    version="1.0.0"
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear agente una sola vez
logger.info("Initializing Ruffo agent for web...")
agent = create_ruffo_agent()
logger.info("Ruffo agent ready!")


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

    - message: El mensaje del usuario
    - thread_id: ID de conversación (opcional, se genera si no existe)
    """
    try:
        # Generar thread_id si no existe
        thread_id = request.thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": f"web-{thread_id}"}}

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
    return {"status": "ok", "agent": "ruffo"}


# Rutas para archivos estáticos
static_path = Path(__file__).parent / "static"

@app.get("/")
async def root():
    """Servir el frontend."""
    return FileResponse(static_path / "index.html")


# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


def run_web_server(host: str = "0.0.0.0", port: int = 8000):
    """Ejecutar el servidor web."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_web_server()
