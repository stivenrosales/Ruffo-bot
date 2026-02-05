"""Lógica de upselling para Ruffo."""

from typing import Optional
from langchain_core.tools import tool
import structlog
import random

from .sheets.products import search_products

logger = structlog.get_logger()

# Reglas de upselling por categoría
UPSELL_RULES = {
    "alimento": ["snacks", "vitaminas", "plato", "bebedero"],
    "snacks": ["juguetes", "alimento", "premios"],
    "juguetes": ["snacks", "accesorios", "cama"],
    "higiene": ["shampoo", "cepillo", "toallas", "accesorios"],
    "salud": ["vitaminas", "alimento", "suplementos"],
    "accesorios": ["juguetes", "cama", "plato"],
    "cama": ["cobija", "juguetes", "accesorios"],
}

# Frases de upselling de Ruffo
UPSELL_PHRASES = [
    "¡Oye! Y ya que llevas {current}, ¿qué tal agregarle un {suggestion}? A los peludos les encanta 🐾",
    "Humano-amigo, te recomiendo mucho este {suggestion} para complementar. ¡Yo se lo daría a Ruffito! 🎸",
    "¿Sabías que el {suggestion} es el complemento perfecto? Muchos clientes lo llevan junto con {current}",
    "¡Rock on! 🤘 Para que tu peludo esté aún más feliz, checa este {suggestion}",
    "Este {suggestion} está increíble, ¡y hace match perfecto con lo que llevas!",
]


@tool
def get_upsell_suggestions(
    current_items: list[dict],
    max_suggestions: int = 2
) -> list[dict]:
    """
    Genera sugerencias de upselling basadas en el pedido actual.

    Ruffo siempre intenta sugerir productos complementarios de forma
    amigable y rockera.

    Args:
        current_items: Lista de productos actuales en el carrito
        max_suggestions: Máximo de sugerencias

    Returns:
        Lista de productos sugeridos con razón de la sugerencia
    """
    try:
        if not current_items:
            return []

        suggestions = []
        seen_categories = set()

        # Obtener categorías de productos actuales
        current_categories = set()
        for item in current_items:
            category = str(item.get("category", "")).lower()
            for key in UPSELL_RULES.keys():
                if key in category:
                    current_categories.add(key)
                    break

        # Buscar productos complementarios
        for category in current_categories:
            suggested_cats = UPSELL_RULES.get(category, [])
            for suggested_cat in suggested_cats:
                if suggested_cat in seen_categories:
                    continue

                # Buscar productos de esa categoría
                products = search_products.invoke({
                    "query": suggested_cat,
                    "max_results": 3,
                })

                if products:
                    # Tomar uno aleatorio
                    product = random.choice(products)
                    suggestions.append({
                        **product,
                        "upsell_reason": f"Complementa tu compra de {category}",
                        "original_category": category,
                    })
                    seen_categories.add(suggested_cat)

                if len(suggestions) >= max_suggestions:
                    break

            if len(suggestions) >= max_suggestions:
                break

        logger.info(
            "Generated upsell suggestions",
            current_items_count=len(current_items),
            suggestions_count=len(suggestions),
        )

        return suggestions

    except Exception as e:
        logger.error("Error generating upsell suggestions", error=str(e))
        return []


def generate_upsell_message(
    current_product: str,
    suggested_product: dict,
) -> str:
    """
    Genera un mensaje de upselling en el estilo de Ruffo.

    Args:
        current_product: Nombre del producto actual
        suggested_product: Producto sugerido

    Returns:
        Mensaje de upselling
    """
    phrase = random.choice(UPSELL_PHRASES)
    return phrase.format(
        current=current_product,
        suggestion=suggested_product.get("name", "este producto"),
    )


def should_offer_upsell(
    items_count: int,
    upsell_already_offered: bool,
    order_total: float,
) -> bool:
    """
    Determina si se debe ofrecer upselling.

    Args:
        items_count: Cantidad de items en el carrito
        upsell_already_offered: Si ya se ofreció upselling
        order_total: Total actual del pedido

    Returns:
        True si se debe ofrecer upselling
    """
    # No ofrecer si ya se ofreció
    if upsell_already_offered:
        return False

    # Ofrecer después de agregar el primer producto
    if items_count >= 1:
        return True

    # Ofrecer si el pedido es pequeño (menos de $300)
    if order_total < 300:
        return True

    return False
