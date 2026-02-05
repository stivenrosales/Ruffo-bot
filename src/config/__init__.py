"""Configuración del bot Ruffo."""

from .settings import settings
from .prompts import RUFFO_SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT, UPSELL_PROMPT

__all__ = [
    "settings",
    "RUFFO_SYSTEM_PROMPT",
    "INTENT_CLASSIFICATION_PROMPT",
    "UPSELL_PROMPT",
]
