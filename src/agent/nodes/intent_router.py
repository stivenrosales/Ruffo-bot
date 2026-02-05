"""Nodo de clasificación de intención."""

from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import structlog

from src.agent.state import RuffoState, update_conversation_context
from src.config.settings import settings
from src.config.prompts import INTENT_CLASSIFICATION_PROMPT
from src.schemas.intents import UserIntent

logger = structlog.get_logger()

# Mapeo de respuestas a intenciones
INTENT_MAPPING = {
    "greeting": UserIntent.GREETING,
    "buy_order": UserIntent.BUY_ORDER,
    "product_inquiry": UserIntent.PRODUCT_INQUIRY,
    "branch_info": UserIntent.BRANCH_INFO,
    "problem_escalation": UserIntent.PROBLEM_ESCALATION,
    "wholesaler": UserIntent.WHOLESALER,
    "order_status": UserIntent.ORDER_STATUS,
    "payment_proof": UserIntent.PAYMENT_PROOF,
    "farewell": UserIntent.FAREWELL,
    "unknown": UserIntent.UNKNOWN,
}

# Palabras clave para clasificación rápida (sin LLM)
KEYWORD_INTENTS = {
    UserIntent.GREETING: ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "hi"],
    UserIntent.FAREWELL: ["adiós", "bye", "gracias", "hasta luego", "chao", "nos vemos"],
    UserIntent.BUY_ORDER: ["comprar", "ordenar", "pedir", "quiero", "necesito", "agregar", "carrito"],
    UserIntent.PRODUCT_INQUIRY: ["precio", "cuánto cuesta", "tienen", "hay", "busco", "información"],
    UserIntent.BRANCH_INFO: ["sucursal", "tienda", "horario", "dirección", "ubicación", "dónde"],
    UserIntent.PROBLEM_ESCALATION: ["problema", "queja", "reclamo", "mal", "error", "ayuda urgente"],
    UserIntent.WHOLESALER: ["mayoreo", "mayorista", "distribuidor", "volumen", "precio especial"],
}


def classify_by_keywords(message: str) -> Optional[UserIntent]:
    """Clasificación rápida por palabras clave."""
    message_lower = message.lower()

    for intent, keywords in KEYWORD_INTENTS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return intent

    return None


def intent_router_node(state: RuffoState) -> dict:
    """
    Nodo que clasifica la intención del usuario.

    Usa primero clasificación por keywords (rápida) y si no
    encuentra match, usa el LLM.
    """
    messages = state.get("messages", [])

    if not messages:
        logger.warning("No messages to classify")
        return {"intent": UserIntent.UNKNOWN, "current_node": "intent_router"}

    # Obtener último mensaje del usuario
    last_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    if not last_message:
        logger.warning("No human message found")
        return {"intent": UserIntent.UNKNOWN, "current_node": "intent_router"}

    logger.info("Classifying intent", message=last_message[:50])

    # Actualizar contexto
    state = update_conversation_context(state, last_message)

    # Extraer información de mascota del mensaje (MEMORIA)
    context = state.get("conversation_context")
    if context:
        context.extract_pet_info(last_message)
        state["conversation_context"] = context
        logger.info("Pet info extracted", pet_type=context.pet_type, product_needed=context.product_type_needed)

    # Primero intentar clasificación por keywords
    intent = classify_by_keywords(last_message)

    if intent:
        logger.info("Intent classified by keywords", intent=intent.value)
        return {
            "intent": intent,
            "previous_intent": state.get("intent"),
            "current_node": "intent_router",
            "conversation_context": state.get("conversation_context"),
        }

    # Si está en medio de un pedido, asumir que continúa
    if state.get("order_stage"):
        logger.info("Continuing order flow", stage=state.get("order_stage"))
        return {
            "intent": UserIntent.BUY_ORDER,
            "current_node": "intent_router",
        }

    # Si no hay match por keywords, usar LLM
    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_completion_tokens=300,
        )

        context = state.get("conversation_context")
        context_str = context.to_string() if context else "Sin contexto previo"

        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            context=context_str,
            message=last_message,
        )

        response = llm.invoke(prompt)
        intent_str = response.content.strip().lower()

        # Mapear respuesta a intención
        intent = INTENT_MAPPING.get(intent_str, UserIntent.UNKNOWN)

        logger.info("Intent classified by LLM", intent=intent.value, raw=intent_str)

        return {
            "intent": intent,
            "previous_intent": state.get("intent"),
            "current_node": "intent_router",
            "conversation_context": state.get("conversation_context"),
        }

    except Exception as e:
        logger.error("Error classifying intent", error=str(e))
        return {
            "intent": UserIntent.UNKNOWN,
            "current_node": "intent_router",
        }
