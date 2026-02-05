"""Teclados inline para el bot de Telegram."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Teclado del menú principal."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Hacer pedido",
                    callback_data="action_order",
                ),
                InlineKeyboardButton(
                    text="🔍 Ver productos",
                    callback_data="action_products",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏪 Sucursales",
                    callback_data="action_branches",
                ),
            ],
        ]
    )


def get_delivery_keyboard() -> InlineKeyboardMarkup:
    """Teclado para selección de tipo de entrega."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏪 Pickup en tienda",
                    callback_data="delivery_pickup",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Envío a domicilio",
                    callback_data="delivery_home",
                ),
            ],
        ]
    )


def get_payment_keyboard() -> InlineKeyboardMarkup:
    """Teclado para selección de método de pago."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵 Efectivo",
                    callback_data="payment_cash",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Transferencia",
                    callback_data="payment_transfer",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Tarjeta",
                    callback_data="payment_card",
                ),
            ],
        ]
    )


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Teclado de confirmación."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Confirmar",
                    callback_data="confirm_yes",
                ),
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data="confirm_no",
                ),
            ],
        ]
    )


def get_branches_keyboard(branches: list[dict]) -> InlineKeyboardMarkup:
    """Teclado para selección de sucursales."""
    buttons = []
    for branch in branches:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏪 {branch['name']}",
                callback_data=f"branch_{branch['id']}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    """Teclado para selección de productos."""
    buttons = []
    for i, product in enumerate(products[:5]):  # Máximo 5 productos
        buttons.append([
            InlineKeyboardButton(
                text=f"{product['name']} - ${product['price']:.2f}",
                callback_data=f"product_{product['id']}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quantity_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """Teclado para selección de cantidad."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data=f"qty_{product_id}_1"),
                InlineKeyboardButton(text="2", callback_data=f"qty_{product_id}_2"),
                InlineKeyboardButton(text="3", callback_data=f"qty_{product_id}_3"),
            ],
            [
                InlineKeyboardButton(text="5", callback_data=f"qty_{product_id}_5"),
                InlineKeyboardButton(text="10", callback_data=f"qty_{product_id}_10"),
            ],
        ]
    )
