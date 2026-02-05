"""Handlers de mensajes para el bot de Telegram con Agente ReAct."""

from aiogram import Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from langchain_core.messages import HumanMessage, AIMessage
import structlog

from src.agent.graph import create_ruffo_agent
from .keyboards import get_main_menu_keyboard

logger = structlog.get_logger()

# Instancia global del agente Ruffo
ruffo_agent = None


def get_agent():
    """Obtiene o crea la instancia del agente."""
    global ruffo_agent
    if ruffo_agent is None:
        ruffo_agent = create_ruffo_agent()
    return ruffo_agent


def setup_handlers(dp: Dispatcher):
    """Configura todos los handlers del bot."""

    @dp.message(CommandStart())
    async def handle_start(message: Message):
        """Handler para /start - Inicia conversación con Ruffo."""
        user_id = str(message.from_user.id)
        user_name = message.from_user.first_name or "humano-amigo"

        logger.info("Start command received", user_id=user_id, user_name=user_name)

        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": f"telegram-{user_id}"}}

            # Invocar el agente con mensaje de inicio
            result = agent.invoke(
                {"messages": [HumanMessage(content="Hola")]},
                config=config
            )

            # Obtener última respuesta del agente
            response = ""
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break

            if not response:
                response = "¡Guau, guau! 🐾 Soy Ruffo de Animalicha 🤘 ¿En qué puedo ayudarte?"

            await message.answer(response)

        except Exception as e:
            logger.error("Error in start handler", error=str(e))
            await message.answer(
                "¡Guau, guau! 🐾 Soy Ruffo de Animalicha 🤘\n"
                "¿En qué puedo ayudarte hoy, humano-amigo?"
            )

    @dp.message(Command("help"))
    async def handle_help(message: Message):
        """Handler para /help."""
        help_text = (
            "🐕 **¡Hola! Soy Ruffo de Animalicha** 🎸\n\n"
            "Puedo ayudarte con:\n"
            "• 🛒 Hacer pedidos de productos\n"
            "• 🔍 Buscar productos y precios\n"
            "• 🏪 Información de sucursales\n\n"
            "**Comandos:**\n"
            "/start - Iniciar conversación\n"
            "/sucursales - Ver sucursales\n"
            "/help - Ver esta ayuda\n\n"
            "¡O simplemente escríbeme lo que necesitas! 🐾"
        )
        await message.answer(help_text)

    @dp.message(Command("sucursales"))
    async def handle_branches(message: Message):
        """Handler para /sucursales."""
        from src.tools.sheets.branches import format_all_branches

        branches_info = format_all_branches()
        await message.answer(branches_info)

    @dp.message(F.photo)
    async def handle_photo(message: Message):
        """Handler para fotos (comprobantes de pago)."""
        user_id = str(message.from_user.id)

        logger.info("Photo received", user_id=user_id)

        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": f"telegram-{user_id}"}}

            # Enviar como mensaje de comprobante
            result = agent.invoke(
                {"messages": [HumanMessage(content="Te envío mi comprobante de pago")]},
                config=config
            )

            response = ""
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break

            if not response:
                response = "📸 ¡Recibido! Voy a procesarlo y te confirmaré pronto, humano-amigo 🤘"

            await message.answer(response)

        except Exception as e:
            logger.error("Error processing photo", error=str(e))
            await message.answer(
                "📸 ¡Recibido! Voy a procesarlo y te confirmaré pronto, humano-amigo.\n\n"
                "¡Gracias! 🐾🤘"
            )

    @dp.message()
    async def handle_message(message: Message):
        """
        Handler principal para mensajes de texto.

        Aquí el LLM controla TODO:
        - Decide si saludar
        - Decide si buscar productos
        - Decide si pedir más info
        - NO hay lógica hardcodeada
        """
        user_id = str(message.from_user.id)
        user_message = message.text or ""

        logger.info(
            "Message received",
            user_id=user_id,
            message=user_message[:50],
        )

        try:
            agent = get_agent()

            # El thread_id mantiene la memoria de la conversación
            config = {"configurable": {"thread_id": f"telegram-{user_id}"}}

            # Invocar el agente - EL LLM DECIDE TODO
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_message)]},
                config=config
            )

            # Obtener la respuesta del agente
            response = ""
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break

            if not response:
                response = "🐕 ¡Guau! ¿Puedes repetirme eso, humano-amigo?"

            logger.info("Response generated", user_id=user_id, response_length=len(response))

            # Enviar respuesta (sin botones - conversación pura)
            await message.answer(response)

        except Exception as e:
            logger.error("Error processing message", error=str(e), user_id=user_id)
            await message.answer(
                "🐕 ¡Guau! Tuve un pequeño problema técnico.\n"
                "¿Puedes intentar de nuevo?"
            )

    @dp.callback_query()
    async def handle_callback(callback: CallbackQuery):
        """Handler para callbacks de botones inline (si se usan)."""
        user_id = str(callback.from_user.id)
        data = callback.data

        logger.info("Callback received", user_id=user_id, data=data)

        # Convertir callback a mensaje natural
        callback_messages = {
            "delivery_pickup": "quiero recoger en tienda",
            "delivery_home": "quiero envío a domicilio",
            "payment_cash": "pago en efectivo",
            "payment_transfer": "pago por transferencia",
            "payment_card": "pago con tarjeta",
            "action_products": "quiero ver productos",
            "action_order": "quiero hacer un pedido",
            "action_branches": "donde están sus tiendas",
        }

        user_message = callback_messages.get(data, data)

        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": f"telegram-{user_id}"}}

            result = agent.invoke(
                {"messages": [HumanMessage(content=user_message)]},
                config=config
            )

            response = ""
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break

            await callback.answer()
            await callback.message.answer(response or "🐕 ¿Qué más necesitas?")

        except Exception as e:
            logger.error("Error in callback handler", error=str(e))
            await callback.answer("Error procesando solicitud")

    logger.info("Telegram handlers configured (ReAct Agent)")
