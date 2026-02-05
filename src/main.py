"""Punto de entrada principal del bot Ruffo."""

import asyncio
import structlog
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from src.config.settings import settings
from src.channels.telegram.bot import run_telegram_bot

# Configurar logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer() if settings.bot_debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def main():
    """Función principal para ejecutar el bot."""
    logger.info(
        "Starting Ruffo bot",
        bot_name=settings.bot_name,
        debug=settings.bot_debug,
        llm_model=settings.llm_model,
    )

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🐕 RUFFO - Bot de Animalicha 🎸                         ║
    ║                                                           ║
    ║   El perro más rockero de la tienda de mascotas           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    try:
        # Ejecutar el bot de Telegram
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        raise


if __name__ == "__main__":
    main()
