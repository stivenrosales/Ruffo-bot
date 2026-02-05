"""
Agente Ruffo con arquitectura ReAct.

Este es un agente REAL donde:
- El LLM controla TODAS las decisiones
- El LLM decide cuándo usar tools
- NO hay lógica hardcodeada de routing
"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
import structlog

from src.config.settings import settings
from src.config.prompts import RUFFO_SYSTEM_PROMPT
from src.tools.agent_tools import RUFFO_TOOLS

logger = structlog.get_logger()


def create_ruffo_agent(checkpointer=None):
    """
    Crea el agente Ruffo usando LangGraph's create_react_agent.

    Este es un agente REAL donde:
    - El LLM controla TODAS las decisiones
    - Las tools son llamadas por el LLM, no por lógica hardcodeada
    - No hay clasificación de intención - el LLM entiende naturalmente

    Args:
        checkpointer: Checkpointer para persistencia de estado.
                      Si es None, usa MemorySaver (en memoria).

    Returns:
        Grafo compilado listo para ejecutar
    """
    # Inicializar LLM
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        max_completion_tokens=settings.llm_max_completion_tokens,
    )

    # System prompt que define la personalidad de Ruffo
    system_message = SystemMessage(content=RUFFO_SYSTEM_PROMPT)

    # Crear checkpointer para memoria de conversación
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Crear el agente ReAct
    agent = create_react_agent(
        model=llm,
        tools=RUFFO_TOOLS,
        state_modifier=system_message,  # Inyecta la personalidad
        checkpointer=checkpointer,
    )

    logger.info(
        "Ruffo ReAct agent created",
        tools_count=len(RUFFO_TOOLS),
        model=settings.llm_model,
    )

    return agent


def get_llm():
    """
    Obtiene la instancia del LLM configurado.
    """
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        max_completion_tokens=settings.llm_max_completion_tokens,
    )


# Alias para compatibilidad con código existente
def build_ruffo_graph():
    """Alias para create_ruffo_agent (compatibilidad)."""
    return create_ruffo_agent()
