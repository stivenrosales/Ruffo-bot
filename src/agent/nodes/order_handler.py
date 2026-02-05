"""Nodo manejador de pedidos con LLM conversacional."""

import random
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import structlog

from src.agent.state import RuffoState
from src.config.settings import settings
from src.schemas.order import OrderInProgress, DeliveryType, PaymentMethod
from src.schemas.product import ProductInCart
from src.tools.sheets.products import search_products
from src.tools.sheets.branches import get_all_branches, format_all_branches
from src.tools.upselling import get_upsell_suggestions, generate_upsell_message

logger = structlog.get_logger()

# Prompt para respuestas del order handler
ORDER_HANDLER_PROMPT = """Eres Ruffo, un Pastor Inglés gigante virtual rockero de Animalicha, la tienda de mascotas.

## Tu Personalidad
- ROCKERO: usas expresiones como "a todo dar", "qué onda", "genial", "rock on"
- JUGUETÓN y CARIÑOSO: te preocupas por las mascotas
- Tratas al cliente como "humano-amigo"
- Usas emojis moderadamente: 🐕 🐱 🎸 🐾 🤘 🛒

## REGLAS
- Respuestas CORTAS: máximo 3-4 líneas
- Sé entusiasta pero no exagerado
- Si no entiendes algo, pide clarificación de forma amigable

## Contexto del Pedido
{order_context}

## Etapa Actual
{stage}

## Mensaje del Usuario
{user_message}

## Tu Tarea
{task}

Responde como Ruffo (CORTO y AMIGABLE):"""


def _generate_order_response(stage: str, order_context: str, user_message: str, task: str) -> str:
    """Genera una respuesta conversacional usando el LLM."""
    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_completion_tokens=500,
        )

        prompt = ORDER_HANDLER_PROMPT.format(
            order_context=order_context,
            stage=stage,
            user_message=user_message,
            task=task,
        )

        response = llm.invoke(prompt)
        return response.content.strip()

    except Exception as e:
        logger.error("Error generating order response", error=str(e))
        return None


def order_handler_node(state: RuffoState) -> dict:
    """
    Nodo principal para manejar el flujo de pedidos.
    Usa LLM para generar respuestas naturales con personalidad de Ruffo.
    """
    messages = state.get("messages", [])
    order = state.get("order") or OrderInProgress()
    order_stage = state.get("order_stage")
    context = state.get("conversation_context")

    # Obtener último mensaje del usuario
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    logger.info(
        "Order handler executing",
        stage=order_stage,
        items_count=len(order.items),
        message=last_message[:50] if last_message else "none",
        pet_type=context.pet_type if context else None,
    )

    # Determinar qué hacer según la etapa actual
    if order_stage is None or order_stage == "collecting_items":
        return handle_collecting_items(state, order, last_message, context)

    elif order_stage == "confirming_items":
        return handle_confirming_items(state, order, last_message)

    elif order_stage == "selecting_delivery":
        return handle_selecting_delivery(state, order, last_message)

    elif order_stage == "collecting_address":
        return handle_collecting_address(state, order, last_message)

    elif order_stage == "selecting_branch":
        return handle_selecting_branch(state, order, last_message)

    elif order_stage == "selecting_payment":
        return handle_selecting_payment(state, order, last_message)

    elif order_stage == "waiting_payment_proof":
        return handle_waiting_payment_proof(state, order, last_message)

    elif order_stage == "confirming_order":
        return handle_confirming_order(state, order, last_message)

    else:
        # Estado desconocido, reiniciar
        response = _generate_order_response(
            stage="error",
            order_context="Algo salió mal en el flujo del pedido",
            user_message=last_message,
            task="Dile amablemente que algo se reinició y pregunta qué quiere pedir"
        )
        if not response:
            response = "🐕 ¡Guau! Algo se enredó. ¿Qué te gustaría pedir, humano-amigo?"

        return {
            "order": OrderInProgress(),
            "order_stage": "collecting_items",
            "messages": [AIMessage(content=response)],
            "last_ruffo_message": response,
        }


def handle_collecting_items(state: RuffoState, order: OrderInProgress, message: str, context) -> dict:
    """Maneja la etapa de agregar productos al carrito."""

    # Obtener tipo de mascota del contexto
    pet_type = context.pet_type if context else None

    # Buscar productos CON filtro de mascota
    products = search_products.invoke({
        "query": message,
        "max_results": 5,
        "pet_type": pet_type
    })

    if not products:
        # No encontró productos - usar LLM para respuesta amigable
        response = _generate_order_response(
            stage="collecting_items",
            order_context=f"No encontré productos para '{message}'. Mascota del cliente: {pet_type or 'no especificada'}",
            user_message=message,
            task="Dile que no encontraste el producto pero pide que lo describa diferente. Da ejemplos como 'croquetas para perro' o 'snacks de pollo'. Sé amigable."
        )
        if not response:
            response = f"🐕 ¡Guau! No encontré '{message}' en mi catálogo, humano-amigo.\n¿Me lo describes diferente? Por ejemplo: 'croquetas para perro' o 'snacks de pollo' 🔍"

        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_items",
            "last_ruffo_message": response,
        }

    if len(products) == 1:
        # Encontró exactamente uno, agregarlo
        product = products[0]
        item = ProductInCart(
            product_id=product["id"],
            product_name=product["name"],
            quantity=1,
            unit_price=product["price"],
        )
        order.add_item(item)

        # Verificar si ofrecer upselling
        if not state.get("upsell_offered") and len(order.items) >= 1:
            try:
                suggestions = get_upsell_suggestions.invoke({
                    "current_items": [{"category": product.get("category", "")}],
                    "max_suggestions": 1,
                })

                if suggestions:
                    upsell_msg = generate_upsell_message(product["name"], suggestions[0])
                    response = _generate_order_response(
                        stage="collecting_items",
                        order_context=f"Agregué {product['name']} al carrito. Carrito: {order.to_summary()}",
                        user_message=message,
                        task=f"Confirma que agregaste el producto. Sugiere: {upsell_msg}. Pregunta si quiere algo más."
                    )
                    if not response:
                        response = (
                            f"🛒 ¡Agregado! {product['name']} - ${product['price']:.2f}\n\n"
                            f"{order.to_summary()}\n\n"
                            f"{upsell_msg}\n\n"
                            "¿Algo más o procedemos? 🤘"
                        )
                    return {
                        "order": order,
                        "messages": [AIMessage(content=response)],
                        "order_stage": "collecting_items",
                        "upsell_offered": True,
                        "upsell_suggestions": suggestions,
                        "last_ruffo_message": response,
                    }
            except Exception as e:
                logger.error("Error getting upsell suggestions", error=str(e))

        response = _generate_order_response(
            stage="collecting_items",
            order_context=f"Agregué {product['name']} (${product['price']:.2f}) al carrito. Carrito actual: {order.to_summary()}",
            user_message=message,
            task="Confirma entusiastamente que agregaste el producto. Muestra el resumen del carrito. Pregunta si quiere algo más o si procedemos."
        )
        if not response:
            response = (
                f"🛒 ¡A todo dar! Agregué {product['name']} - ${product['price']:.2f}\n\n"
                f"{order.to_summary()}\n\n"
                "¿Algo más o procedemos con tu pedido? 🤘"
            )

        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_items",
            "last_ruffo_message": response,
        }

    else:
        # Múltiples productos encontrados
        options = "\n".join([
            f"{i+1}. {p['name']} - ${p['price']:.2f}"
            for i, p in enumerate(products[:5])
        ])

        response = _generate_order_response(
            stage="collecting_items",
            order_context=f"Encontré {len(products)} productos. Opciones:\n{options}",
            user_message=message,
            task="Dile que encontraste varios productos y muestra las opciones. Pide que elija por número o nombre."
        )
        if not response:
            response = (
                f"🔍 ¡Genial! Encontré varias opciones:\n\n"
                f"{options}\n\n"
                "¿Cuál te late? Dime el número o el nombre 🐾"
            )

        return {
            "found_products": products,
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_items",
            "last_ruffo_message": response,
        }


def handle_confirming_items(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Confirma los items del carrito."""
    message_lower = message.lower()

    if any(word in message_lower for word in ["sí", "si", "ok", "listo", "confirmo", "correcto", "eso"]):
        response = _generate_order_response(
            stage="confirming_items",
            order_context=f"Cliente confirmó el carrito: {order.to_summary()}",
            user_message=message,
            task="Celebra que confirmó. Pregunta cómo quiere recibir: Pickup (recoger en tienda) o Domicilio (se lo llevan)."
        )
        if not response:
            response = (
                "🤘 ¡A todo dar! Tu carrito está listo.\n\n"
                "¿Cómo prefieres recibirlo?\n"
                "🏪 **Pickup** - Recoges en tienda\n"
                "🚚 **Domicilio** - Te lo llevamos"
            )
        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_delivery",
            "last_ruffo_message": response,
        }

    elif any(word in message_lower for word in ["no", "cambiar", "modificar", "quitar"]):
        response = _generate_order_response(
            stage="confirming_items",
            order_context=f"Cliente quiere modificar el carrito: {order.to_summary()}",
            user_message=message,
            task="Dile que está bien modificar. Explica que puede escribir 'quitar [producto]' o agregar algo nuevo."
        )
        if not response:
            response = (
                "🐕 ¡Claro! ¿Qué quieres cambiar?\n"
                "- Escribe 'quitar [producto]' para eliminarlo\n"
                "- O dime qué producto agregar"
            )
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_items",
            "last_ruffo_message": response,
        }
    else:
        # Asumir que quiere agregar algo más
        context = state.get("conversation_context")
        return handle_collecting_items(state, order, message, context)


def handle_selecting_delivery(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Selecciona tipo de entrega."""
    message_lower = message.lower()

    if any(word in message_lower for word in ["pickup", "recoger", "tienda", "sucursal"]):
        order.delivery_type = DeliveryType.PICKUP
        branches = get_all_branches.invoke({})
        branches_text = format_all_branches()

        response = _generate_order_response(
            stage="selecting_delivery",
            order_context=f"Cliente eligió pickup. Sucursales disponibles:\n{branches_text}",
            user_message=message,
            task="Confirma pickup en tienda. Muestra las sucursales y pregunta en cuál le queda mejor."
        )
        if not response:
            response = (
                f"🏪 ¡Genial! Pickup en tienda.\n\n"
                f"{branches_text}\n"
                "¿En cuál sucursal te queda mejor?"
            )
        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_branch",
            "last_ruffo_message": response,
        }

    elif any(word in message_lower for word in ["domicilio", "casa", "envío", "enviar", "llevar"]):
        order.delivery_type = DeliveryType.DELIVERY

        shipping_note = ""
        if order.subtotal < 500:
            shipping_note = f" (¡Tip! Con ${500 - order.subtotal:.2f} más el envío es gratis)"

        response = _generate_order_response(
            stage="selecting_delivery",
            order_context=f"Cliente eligió domicilio. Subtotal: ${order.subtotal:.2f}.{shipping_note}",
            user_message=message,
            task="Confirma envío a domicilio. Pide la dirección completa (calle, número, colonia, ciudad)."
        )
        if not response:
            response = (
                f"🚚 ¡Perfecto! Te lo llevamos a domicilio.{shipping_note}\n\n"
                "¿Cuál es tu dirección completa? (calle, número, colonia, ciudad)"
            )
        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_address",
            "waiting_for": "address",
            "last_ruffo_message": response,
        }

    else:
        response = _generate_order_response(
            stage="selecting_delivery",
            order_context="No entendí el tipo de entrega que quiere el cliente",
            user_message=message,
            task="Dile amablemente que no entendiste. Pregunta si prefiere Pickup (recoger en tienda) o Domicilio (se lo llevan)."
        )
        if not response:
            response = (
                "🐕 ¡Guau! No capté bien, humano-amigo. ¿Prefieres:\n"
                "🏪 **Pickup** - Recoges en tienda\n"
                "🚚 **Domicilio** - Te lo llevamos"
            )
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_delivery",
            "last_ruffo_message": response,
        }


def handle_collecting_address(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Recoge la dirección de entrega."""
    if len(message) < 10:
        response = _generate_order_response(
            stage="collecting_address",
            order_context="La dirección proporcionada es muy corta",
            user_message=message,
            task="Dile amablemente que la dirección parece muy corta. Necesitas: calle, número, colonia y ciudad."
        )
        if not response:
            response = (
                "🐕 ¡Guau! Esa dirección parece muy cortita.\n"
                "Necesito: calle, número, colonia y ciudad para no perderme 📍"
            )
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "collecting_address",
            "last_ruffo_message": response,
        }

    order.delivery_address = message

    response = _generate_order_response(
        stage="collecting_address",
        order_context=f"Dirección registrada: {message}. Carrito: {order.to_summary()}",
        user_message=message,
        task="Confirma la dirección. Muestra resumen del pedido. Pregunta cómo quiere pagar: Efectivo, Transferencia o Tarjeta."
    )
    if not response:
        response = (
            f"📍 ¡Anotado!\n{message}\n\n"
            f"{order.to_summary()}\n\n"
            "¿Cómo quieres pagar?\n"
            "💵 **Efectivo** - Pagas al recibir\n"
            "💳 **Transferencia** - Te paso los datos\n"
            "💳 **Tarjeta** - Pagas al recibir"
        )
    return {
        "order": order,
        "messages": [AIMessage(content=response)],
        "order_stage": "selecting_payment",
        "waiting_for": None,
        "last_ruffo_message": response,
    }


def handle_selecting_branch(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Selecciona sucursal para pickup."""
    message_lower = message.lower()

    branches = get_all_branches.invoke({})

    # Buscar sucursal mencionada
    selected_branch = None
    for branch in branches:
        if branch["id"] in message_lower or branch["name"].lower() in message_lower:
            selected_branch = branch
            break

    # Buscar por palabras clave de dirección
    if not selected_branch:
        for branch in branches:
            address_words = branch["address"].lower().split()
            for word in address_words:
                if len(word) > 3 and word in message_lower:
                    selected_branch = branch
                    break

    if selected_branch:
        order.branch_id = selected_branch["id"]
        order.branch_name = selected_branch["name"]

        response = _generate_order_response(
            stage="selecting_branch",
            order_context=f"Sucursal seleccionada: {selected_branch['name']} - {selected_branch['address']}. Horario: {selected_branch['hours']}. Carrito: {order.to_summary()}",
            user_message=message,
            task="Confirma la sucursal con su dirección y horario. Muestra resumen del pedido. Pregunta cómo quiere pagar."
        )
        if not response:
            response = (
                f"🏪 ¡Perfecto! Recoges en **{selected_branch['name']}**\n"
                f"📍 {selected_branch['address']}\n"
                f"🕐 {selected_branch['hours']}\n\n"
                f"{order.to_summary()}\n\n"
                "¿Cómo quieres pagar?\n"
                "💵 **Efectivo** | 💳 **Transferencia** | 💳 **Tarjeta**"
            )
        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_payment",
            "last_ruffo_message": response,
        }
    else:
        branches_text = format_all_branches()
        response = _generate_order_response(
            stage="selecting_branch",
            order_context=f"No encontré la sucursal mencionada. Sucursales disponibles:\n{branches_text}",
            user_message=message,
            task="Dile amablemente que no ubicaste esa sucursal. Muestra las opciones disponibles."
        )
        if not response:
            response = (
                f"🐕 ¡Guau! No ubiqué esa sucursal. Aquí están las opciones:\n\n"
                f"{branches_text}\n"
                "¿Cuál te queda mejor?"
            )
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_branch",
            "last_ruffo_message": response,
        }


def handle_selecting_payment(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Selecciona método de pago."""
    message_lower = message.lower()

    if any(word in message_lower for word in ["efectivo", "cash"]):
        order.payment_method = PaymentMethod.CASH
        return finalize_order(order, "efectivo")

    elif any(word in message_lower for word in ["transferencia", "transfer", "spei"]):
        order.payment_method = PaymentMethod.TRANSFER
        response = _generate_order_response(
            stage="selecting_payment",
            order_context=f"Cliente eligió transferencia. Total: ${order.total:.2f}",
            user_message=message,
            task="Confirma transferencia. Da los datos bancarios: BBVA, Cuenta 0123456789, CLABE 012345678901234567, Animalicha SA de CV. Pide que mande foto del comprobante."
        )
        if not response:
            response = (
                "💳 ¡Perfecto! Aquí están los datos para transferencia:\n\n"
                "🏦 Banco: BBVA\n"
                "📝 Cuenta: 0123456789\n"
                "🔢 CLABE: 012345678901234567\n"
                "👤 Nombre: Animalicha SA de CV\n\n"
                f"💰 Total: **${order.total:.2f}**\n\n"
                "Cuando hagas la transferencia, mándame foto del comprobante 📸"
            )
        return {
            "order": order,
            "messages": [AIMessage(content=response)],
            "order_stage": "waiting_payment_proof",
            "waiting_for": "photo",
            "last_ruffo_message": response,
        }

    elif any(word in message_lower for word in ["tarjeta", "card", "débito", "crédito"]):
        order.payment_method = PaymentMethod.CARD
        return finalize_order(order, "tarjeta")

    else:
        response = _generate_order_response(
            stage="selecting_payment",
            order_context="No entendí el método de pago",
            user_message=message,
            task="Dile amablemente que no entendiste. Pregunta si prefiere Efectivo, Transferencia o Tarjeta."
        )
        if not response:
            response = (
                "🐕 ¡Guau! No capté bien. ¿Cómo prefieres pagar?\n"
                "💵 **Efectivo**\n"
                "💳 **Transferencia**\n"
                "💳 **Tarjeta**"
            )
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "selecting_payment",
            "last_ruffo_message": response,
        }


def handle_waiting_payment_proof(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Espera el comprobante de pago."""
    response = _generate_order_response(
        stage="waiting_payment_proof",
        order_context=f"Cliente envió algo (posiblemente comprobante). Total esperado: ${order.total:.2f}",
        user_message=message,
        task="Confirma que recibiste el comprobante. Dile que lo procesarás y confirmarás pronto. Sé entusiasta."
    )
    if not response:
        response = (
            "📸 ¡Recibido, humano-amigo! Voy a procesarlo y te confirmaré pronto.\n\n"
            "Tu pedido queda registrado. ¡Te avisamos cuando verifiquemos! 🐾\n\n"
            "¡Rock on! 🤘"
        )

    return finalize_order(order, "transferencia (comprobante recibido)")


def handle_confirming_order(state: RuffoState, order: OrderInProgress, message: str) -> dict:
    """Confirmación final del pedido."""
    message_lower = message.lower()

    if any(word in message_lower for word in ["sí", "si", "confirmo", "ok", "listo"]):
        return finalize_order(order, order.payment_method.value if order.payment_method else "efectivo")
    else:
        response = _generate_order_response(
            stage="confirming_order",
            order_context=f"Esperando confirmación final. Carrito: {order.to_summary()}",
            user_message=message,
            task="Pregunta si confirma el pedido. Si dice que quiere cambiar algo, dile qué puede hacer."
        )
        if not response:
            response = "🐕 ¿Confirmamos el pedido? Responde 'sí' para confirmar o dime qué quieres cambiar."
        return {
            "messages": [AIMessage(content=response)],
            "order_stage": "confirming_order",
            "last_ruffo_message": response,
        }


def finalize_order(order: OrderInProgress, payment_method: str) -> dict:
    """Finaliza y confirma el pedido."""
    import uuid
    order_number = f"RUF-{uuid.uuid4().hex[:6].upper()}"

    delivery_info = ""
    if order.delivery_type == DeliveryType.PICKUP:
        delivery_info = f"🏪 Recoger en: {order.branch_name}"
    else:
        delivery_info = f"🚚 Envío a: {order.delivery_address}"

    response = _generate_order_response(
        stage="completed",
        order_context=f"Pedido #{order_number} confirmado. {delivery_info}. Pago: {payment_method}. {order.to_summary()}",
        user_message="",
        task="Celebra el pedido confirmado. Muestra el número de pedido, tipo de entrega y forma de pago. Agradece y despídete rockero."
    )
    if not response:
        response = (
            f"🎉 **¡PEDIDO CONFIRMADO!** 🎉\n\n"
            f"📦 Pedido: **{order_number}**\n"
            f"{delivery_info}\n"
            f"💳 Pago: {payment_method}\n\n"
            f"{order.to_summary()}\n\n"
            "¡Gracias, humano-amigo! Tu peludo va a estar feliz 🐕\n"
            "¡Rock on! 🤘🐾"
        )

    return {
        "order": order,
        "messages": [AIMessage(content=response)],
        "order_stage": "completed",
        "conversation_ended": True,
        "last_ruffo_message": response,
    }
