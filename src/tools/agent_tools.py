"""
Tools centralizadas para el agente Ruffo.

Este módulo exporta todas las herramientas que el agente puede usar.
El LLM decide cuándo y cómo usar cada tool.
"""

from typing import Optional, Annotated
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import structlog

# Importar tools existentes
from src.tools.sheets.products import search_products, get_product_by_id, get_products_by_category
from src.tools.sheets.branches import get_all_branches, get_branch_by_id, find_nearest_branch

logger = structlog.get_logger()


# ============================================
# TOOLS PARA EL AGENTE RUFFO
# ============================================

# Las tools de productos y sucursales ya están definidas en sus módulos
# Aquí las reexportamos y agregamos tools adicionales para el carrito


@tool
def get_cart_status(cart_items: list = None) -> str:
    """
    Muestra el estado actual del carrito de compras.
    Úsala cuando el cliente pregunte qué tiene en su carrito.

    Returns:
        Resumen del carrito con productos y total
    """
    if not cart_items:
        return "El carrito está vacío. ¿Qué te gustaría agregar?"

    total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
    items_text = "\n".join([
        f"- {item['name']} x{item.get('quantity', 1)} = ${item.get('price', 0) * item.get('quantity', 1):.2f}"
        for item in cart_items
    ])

    return f"Carrito actual:\n{items_text}\n\nTotal: ${total:.2f}"


# Lista de todas las tools disponibles para el agente
RUFFO_TOOLS = [
    # Búsqueda de productos
    search_products,
    get_product_by_id,
    get_products_by_category,

    # Información de sucursales
    get_all_branches,
    get_branch_by_id,
    find_nearest_branch,

    # Carrito (básico)
    get_cart_status,
]


def get_tools_description() -> str:
    """Retorna descripción de todas las tools para debugging."""
    descriptions = []
    for tool in RUFFO_TOOLS:
        descriptions.append(f"- {tool.name}: {tool.description[:100]}...")
    return "\n".join(descriptions)
