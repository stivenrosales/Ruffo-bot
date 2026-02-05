"""Tools para sucursales."""

from typing import Optional
from langchain_core.tools import tool
import structlog

logger = structlog.get_logger()

# Datos de sucursales (hardcoded por ahora, luego se puede mover a Sheets)
BRANCHES = [
    {
        "id": "ojo-agua",
        "name": "Animalicha Ojo de Agua",
        "address": "Av. Ojo de Agua 123, Tecámac, Estado de México",
        "phone": "55-1234-5678",
        "hours": "Lunes a Sábado 9:00 - 20:00, Domingo 10:00 - 18:00",
        "services": ["pickup", "grooming", "veterinario"],
        "pickup_available": True,
        "maps_url": "https://maps.google.com/?q=Animalicha+Ojo+de+Agua",
    },
    {
        "id": "tecamac",
        "name": "Animalicha Tecámac Centro",
        "address": "Calle Principal 456, Tecámac Centro, Estado de México",
        "phone": "55-8765-4321",
        "hours": "Lunes a Sábado 9:00 - 19:00, Domingo 10:00 - 17:00",
        "services": ["pickup", "grooming"],
        "pickup_available": True,
        "maps_url": "https://maps.google.com/?q=Animalicha+Tecamac",
    },
    {
        "id": "ecatepec",
        "name": "Animalicha Ecatepec",
        "address": "Blvd. de las Américas 789, Ecatepec, Estado de México",
        "phone": "55-2468-1357",
        "hours": "Lunes a Sábado 10:00 - 20:00, Domingo 11:00 - 18:00",
        "services": ["pickup"],
        "pickup_available": True,
        "maps_url": "https://maps.google.com/?q=Animalicha+Ecatepec",
    },
]


@tool
def get_all_branches() -> list[dict]:
    """
    Obtiene la lista de todas las sucursales de Animalicha.
    Incluye dirección, horarios, teléfono y servicios disponibles.

    Returns:
        Lista de sucursales con toda su información
    """
    logger.info("Getting all branches", count=len(BRANCHES))
    return BRANCHES


@tool
def get_branch_by_id(branch_id: str) -> Optional[dict]:
    """
    Obtiene información de una sucursal específica.

    Args:
        branch_id: ID de la sucursal (ojo-agua, tecamac, ecatepec)

    Returns:
        Información de la sucursal o None si no existe
    """
    for branch in BRANCHES:
        if branch["id"] == branch_id:
            return branch
    return None


@tool
def find_nearest_branch(location: str) -> dict:
    """
    Encuentra la sucursal más cercana basada en la ubicación del cliente.

    Args:
        location: Ciudad o zona del cliente

    Returns:
        Sucursal recomendada
    """
    location_lower = location.lower()

    # Lógica simple de matching por ubicación
    if "ojo" in location_lower or "agua" in location_lower:
        return BRANCHES[0]  # Ojo de Agua
    elif "tecamac" in location_lower or "centro" in location_lower:
        return BRANCHES[1]  # Tecámac Centro
    elif "ecatepec" in location_lower:
        return BRANCHES[2]  # Ecatepec

    # Default: primera sucursal
    return BRANCHES[0]


def format_branch_info(branch: dict) -> str:
    """Formatea la información de una sucursal para mostrar al usuario."""
    return f"""
🏪 **{branch['name']}**
📍 {branch['address']}
📞 {branch['phone']}
🕐 {branch['hours']}
🔧 Servicios: {', '.join(branch['services'])}
📍 {branch['maps_url']}
"""


def format_all_branches() -> str:
    """Formatea todas las sucursales para mostrar al usuario."""
    lines = ["🏪 **Sucursales de Animalicha:**\n"]
    for branch in BRANCHES:
        lines.append(f"**{branch['name']}**")
        lines.append(f"  📍 {branch['address']}")
        lines.append(f"  📞 {branch['phone']}")
        lines.append(f"  🕐 {branch['hours']}")
        lines.append("")
    return "\n".join(lines)
