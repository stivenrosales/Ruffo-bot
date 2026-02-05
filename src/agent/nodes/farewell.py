"""Nodo de despedida de Ruffo."""

import random
from langchain_core.messages import AIMessage
import structlog

from src.agent.state import RuffoState

logger = structlog.get_logger()

# Despedidas de Ruffo
FAREWELLS = [
    "¡Rock on, humano-amigo! 🤘🐾\nCuida mucho a tu peludo y vuelve pronto a Animalicha.\n¡Guau, guau! 🐕",
    "¡Fue un gusto atenderte! 🎸\nRecuerda que aquí estoy para lo que necesites.\n¡Nos vemos pronto! 🐾",
    "¡Gracias por visitarme! 🐕\nEspero que tu mascota disfrute mucho.\n¡Rock on y cuídate! 🤘",
    "¡Hasta la próxima, humano-amigo! 🎸🐾\nAquí estaré ladrando cuando me necesites.\n¡Guau! 🐕",
]

FAREWELLS_WITH_ORDER = [
    "¡Gracias por tu compra! 🎉🐾\nTu peludo va a estar muy feliz.\n¡Rock on y nos vemos pronto! 🤘🐕",
    "¡Pedido listo! 📦✨\nFue un placer atenderte, humano-amigo.\n¡Cuida mucho a tu mascota! 🐾🎸",
    "¡Genial! Tu pedido está en camino (o esperándote) 🚚🏪\n¡Gracias por elegir Animalicha!\n¡Guau, guau! 🐕🤘",
]


def farewell_node(state: RuffoState) -> dict:
    """
    Nodo de despedida.

    Genera una despedida personalizada según si hubo pedido o no.
    """
    order_completed = state.get("order_stage") == "completed"
    customer = state.get("customer")

    logger.info("Executing farewell node", order_completed=order_completed)

    # Seleccionar despedida apropiada
    if order_completed:
        farewell = random.choice(FAREWELLS_WITH_ORDER)
    else:
        farewell = random.choice(FAREWELLS)

    # Personalizar si tenemos el nombre
    if customer and customer.name:
        farewell = farewell.replace("humano-amigo", customer.name)

    # Crear mensaje de Ruffo
    ruffo_message = AIMessage(content=farewell)

    logger.info("Farewell generated")

    return {
        "messages": [ruffo_message],
        "current_node": "farewell",
        "conversation_ended": True,
        "last_ruffo_message": farewell,
    }
