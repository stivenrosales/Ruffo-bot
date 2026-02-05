"""Bot de Telegram principal."""

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import structlog

from src.config.settings import settings
from .handlers import setup_handlers

logger = structlog.get_logger()


def create_telegram_bot() -> tuple[Bot, Dispatcher]:
    """
    Crea el bot de Telegram y el dispatcher.

    Returns:
        Tuple con (Bot, Dispatcher)
    """
    # Crear bot con parse mode por defecto
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # Crear dispatcher
    dp = Dispatcher()

    # Configurar handlers
    setup_handlers(dp)

    logger.info("Telegram bot created", bot_name=settings.bot_name)

    return bot, dp


async def run_telegram_bot():
    """
    Ejecuta el bot de Telegram.

    Esta función bloquea hasta que el bot se detiene.
    """
    bot, dp = create_telegram_bot()

    logger.info("Starting Telegram bot polling...")

    try:
        # Eliminar webhook si existe (para usar polling)
        await bot.delete_webhook(drop_pending_updates=True)

        # Iniciar polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error("Error running bot", error=str(e))
        raise
    finally:
        await bot.session.close()


def run_bot_sync():
    """Ejecuta el bot de forma síncrona (para usar desde main.py)."""
    asyncio.run(run_telegram_bot())
