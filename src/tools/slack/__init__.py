"""Tools de Slack."""

from .notifications import notify_new_order, escalate_to_support

__all__ = [
    "notify_new_order",
    "escalate_to_support",
]
