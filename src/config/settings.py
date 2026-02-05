"""Configuración centralizada usando Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Configuración del bot Ruffo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI
    openai_api_key: str = Field(..., description="API Key de OpenAI")

    # Telegram (opcional en Vercel, requerido para Telegram bot)
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Token del bot de Telegram",
    )

    # Google Sheets
    google_credentials_path: str = Field(
        default="credentials.json",
        description="Ruta al archivo de credenciales de Google",
    )
    google_credentials_json: Optional[str] = Field(
        default=None,
        description="JSON de credenciales de Google (para Vercel, alternativa a archivo)",
    )
    google_sheets_id: str = Field(
        default="13LKCH_HHVANAl_KO99-Lrah5AoLLCTDjEJt2YMqco7M",
        description="ID del spreadsheet de Google Sheets",
    )
    google_sheets_name: str = Field(
        default="animalicha_limpia",
        description="Nombre de la hoja a usar",
    )

    # Slack (opcional)
    slack_bot_token: Optional[str] = Field(
        default=None,
        description="Token del bot de Slack",
    )
    slack_orders_channel: str = Field(
        default="#pedidos",
        description="Canal de Slack para pedidos",
    )
    slack_support_channel: str = Field(
        default="#soporte",
        description="Canal de Slack para soporte",
    )

    # Bot Config
    bot_name: str = Field(default="Ruffo", description="Nombre del bot")
    bot_debug: bool = Field(default=True, description="Modo debug")
    log_level: str = Field(default="INFO", description="Nivel de logging")

    # LLM Config
    llm_model: str = Field(
        default="gpt-5-mini-2025-08-07",
        description="Modelo de OpenAI GPT-5 Mini (sin razonamiento)",
    )
    llm_temperature: float = Field(
        default=1.0,
        description="Temperatura del LLM (gpt-5-mini solo soporta 1.0)",
    )
    llm_max_completion_tokens: int = Field(
        default=1024,
        description="Máximo de tokens en respuesta (incluye razonamiento para GPT-5 mini)",
    )


# Instancia global de configuración
settings = Settings()
