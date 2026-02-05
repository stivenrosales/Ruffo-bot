"""Nodo de escalación a humanos."""

from langchain_core.messages import HumanMessage, AIMessage
import structlog

from src.agent.state import RuffoState
from src.schemas.intents import UserIntent

logger = structlog.get_logger()

# Mensajes de escalación según el tipo
ESCALATION_MESSAGES = {
    "problem": (
        "😔 Lamento mucho que tengas este problema, humano-amigo.\n\n"
        "Voy a pasar tu caso a mi equipo humano para que te ayuden mejor. "
        "Ellos son expertos y te contactarán pronto.\n\n"
        "📞 También puedes llamar directamente al: **55-1234-5678**\n\n"
        "¡Prometo que lo resolveremos! 🐾"
    ),
    "wholesaler": (
        "🏪 ¡Ah, eres mayorista! Qué genial, humano-amigo.\n\n"
        "Para atención de mayoreo, mi compañera **Frida** es la experta. "
        "Ella te dará los mejores precios y atención personalizada.\n\n"
        "📧 Contacta a Frida: mayoreo@animalicha.com\n"
        "📞 O llama al: **55-8765-4321** ext. 200\n\n"
        "¡Gracias por tu interés en Animalicha! 🤘"
    ),
    "complex": (
        "🤔 Esta situación necesita atención especial, humano-amigo.\n\n"
        "Voy a conectarte con mi equipo humano que puede ayudarte mejor "
        "con esto. Te contactarán muy pronto.\n\n"
        "📞 Si es urgente: **55-1234-5678**\n\n"
        "¡No te preocupes, lo resolveremos! 🐾"
    ),
}


def escalation_node(state: RuffoState) -> dict:
    """
    Nodo para escalar conversaciones a humanos.

    Se activa cuando:
    - El usuario tiene un problema/queja
    - El usuario es mayorista
    - La situación es compleja para el bot
    """
    intent = state.get("intent")
    messages = state.get("messages", [])

    # Obtener último mensaje del usuario para contexto
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    # Determinar tipo de escalación
    if intent == UserIntent.WHOLESALER or "mayorist" in last_message.lower():
        escalation_type = "wholesaler"
        reason = "Cliente mayorista"
    elif intent == UserIntent.PROBLEM_ESCALATION or any(
        word in last_message.lower()
        for word in ["problema", "queja", "reclamo", "mal", "error"]
    ):
        escalation_type = "problem"
        reason = f"Problema reportado: {last_message[:100]}"
    else:
        escalation_type = "complex"
        reason = "Situación compleja"

    logger.info(
        "Escalating conversation",
        escalation_type=escalation_type,
        reason=reason,
    )

    response = ESCALATION_MESSAGES.get(escalation_type, ESCALATION_MESSAGES["complex"])

    return {
        "messages": [AIMessage(content=response)],
        "needs_escalation": True,
        "escalation_reason": reason,
        "current_node": "escalation",
        "last_ruffo_message": response,
    }
