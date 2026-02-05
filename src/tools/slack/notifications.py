"""Notificaciones a Slack."""

from typing import Optional
from langchain_core.tools import tool
import structlog

from src.config.settings import settings

logger = structlog.get_logger()


@tool
async def notify_new_order(
    order_id: str,
    customer_name: str,
    customer_phone: str,
    delivery_type: str,
    delivery_location: str,
    items: list[dict],
    total: float,
    payment_method: str,
    notes: str = "",
) -> dict:
    """
    Envía notificación a Slack cuando hay un nuevo pedido.

    Args:
        order_id: ID del pedido
        customer_name: Nombre del cliente
        customer_phone: Teléfono del cliente
        delivery_type: Tipo de entrega (pickup/delivery)
        delivery_location: Dirección o sucursal
        items: Lista de productos
        total: Total del pedido
        payment_method: Método de pago
        notes: Notas adicionales

    Returns:
        Dict con resultado de la notificación
    """
    if not settings.slack_bot_token:
        logger.warning("Slack not configured, skipping notification")
        return {"success": False, "reason": "Slack not configured"}

    try:
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient(token=settings.slack_bot_token)

        # Formatear items
        items_text = "\n".join([
            f"  • {item.get('quantity', 1)}x {item.get('product_name', 'Producto')} - ${item.get('subtotal', 0):.2f}"
            for item in items
        ])

        # Emoji según tipo de entrega
        delivery_emoji = "🏪" if delivery_type == "pickup" else "🚚"

        message = f"""
:package: *Nuevo Pedido - {order_id}*

*Cliente:* {customer_name}
*Teléfono:* {customer_phone}
{delivery_emoji} *Entrega:* {delivery_type.upper()}
*Ubicación:* {delivery_location}

*Productos:*
{items_text}

*Total:* ${total:.2f}
*Pago:* {payment_method}

{f"*Notas:* {notes}" if notes else ""}
        """

        response = await client.chat_postMessage(
            channel=settings.slack_orders_channel,
            text=message,
            mrkdwn=True,
        )

        logger.info("Slack notification sent", order_id=order_id)

        return {"success": response["ok"], "ts": response.get("ts")}

    except Exception as e:
        logger.error("Error sending Slack notification", error=str(e))
        return {"success": False, "error": str(e)}


@tool
async def escalate_to_support(
    customer_id: str,
    customer_name: str,
    issue_description: str,
    conversation_summary: str,
    channel: str = "telegram",
) -> dict:
    """
    Escala un problema al equipo de soporte via Slack.

    Args:
        customer_id: ID del cliente
        customer_name: Nombre del cliente
        issue_description: Descripción del problema
        conversation_summary: Resumen de la conversación
        channel: Canal de origen

    Returns:
        Dict con resultado de la escalación
    """
    if not settings.slack_bot_token:
        logger.warning("Slack not configured, skipping escalation")
        return {"success": False, "reason": "Slack not configured"}

    try:
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient(token=settings.slack_bot_token)

        message = f"""
:warning: *Escalación de Cliente*

*Cliente:* {customer_name} (ID: {customer_id})
*Canal:* {channel}
*Problema:* {issue_description}

*Resumen de conversación:*
```
{conversation_summary[:500]}
```

Por favor, contactar al cliente lo antes posible.
        """

        response = await client.chat_postMessage(
            channel=settings.slack_support_channel,
            text=message,
            mrkdwn=True,
        )

        logger.info("Escalation sent to Slack", customer_id=customer_id)

        return {"success": response["ok"], "ts": response.get("ts")}

    except Exception as e:
        logger.error("Error sending escalation to Slack", error=str(e))
        return {"success": False, "error": str(e)}
