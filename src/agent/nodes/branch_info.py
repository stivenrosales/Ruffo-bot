"""Nodo de información de sucursales."""

from langchain_core.messages import AIMessage
import structlog

from src.agent.state import RuffoState
from src.tools.sheets.branches import get_all_branches, format_all_branches, find_nearest_branch

logger = structlog.get_logger()


def branch_info_node(state: RuffoState) -> dict:
    """
    Nodo para responder consultas sobre sucursales.

    Muestra información de todas las sucursales o busca la más cercana.
    """
    messages = state.get("messages", [])

    # Obtener último mensaje del usuario
    last_message = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and not isinstance(msg, AIMessage):
            last_message = msg.content
            break

    logger.info("Branch info requested", message=last_message[:50] if last_message else "none")

    # Verificar si pregunta por una ubicación específica
    location_keywords = ["cerca", "cercana", "más cerca", "en", "por"]
    is_location_query = any(kw in last_message.lower() for kw in location_keywords)

    if is_location_query and last_message:
        # Intentar encontrar sucursal cercana
        try:
            branch = find_nearest_branch.invoke({"location": last_message})
            response = (
                f"🏪 La sucursal más cercana es:\n\n"
                f"**{branch['name']}**\n"
                f"📍 {branch['address']}\n"
                f"📞 {branch['phone']}\n"
                f"🕐 {branch['hours']}\n"
                f"🔧 Servicios: {', '.join(branch['services'])}\n\n"
                f"📍 [Ver en Maps]({branch['maps_url']})\n\n"
                "¿Necesitas algo más, humano-amigo? 🐾"
            )
        except Exception as e:
            logger.error("Error finding nearest branch", error=str(e))
            response = format_all_branches() + "\n¿Alguna te queda bien? 🐾"
    else:
        # Mostrar todas las sucursales
        response = format_all_branches()
        response += "\n¿En cuál te gustaría recoger o cuál te queda más cerca? 🐾"

    return {
        "messages": [AIMessage(content=response)],
        "current_node": "branch_info",
        "last_ruffo_message": response,
    }
