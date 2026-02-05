"""Estado del agente Ruffo."""

from typing import Annotated, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

from src.schemas.customer import CustomerSession
from src.schemas.order import OrderInProgress, DeliveryType, PaymentMethod
from src.schemas.intents import UserIntent, ConversationContext


class RuffoState(MessagesState):
    """
    Estado completo del agente Ruffo.

    Hereda de MessagesState para tener el historial de mensajes automáticamente.
    """

    # === Información del Usuario ===
    customer: Optional[CustomerSession] = None
    channel: Literal["telegram", "whatsapp", "facebook", "instagram"] = "telegram"

    # === Clasificación de Intención ===
    intent: Optional[UserIntent] = None
    previous_intent: Optional[UserIntent] = None

    # === Estado del Pedido ===
    order: Optional[OrderInProgress] = None
    order_stage: Optional[
        Literal[
            "collecting_items",
            "confirming_items",
            "selecting_delivery",
            "collecting_address",
            "selecting_branch",
            "selecting_payment",
            "waiting_payment_proof",
            "confirming_order",
            "completed",
        ]
    ] = None

    # === Productos y Búsquedas ===
    found_products: list[dict] = []
    last_search_query: Optional[str] = None

    # === Upselling ===
    upsell_suggestions: list[dict] = []
    upsell_offered: bool = False

    # === Escalado ===
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None

    # === Control de Flujo ===
    current_node: str = "start"
    waiting_for: Optional[str] = None  # "address", "payment", "confirmation", "photo"
    conversation_context: Optional[ConversationContext] = None

    # === Metadata ===
    is_new_conversation: bool = True
    conversation_ended: bool = False
    last_ruffo_message: Optional[str] = None


def create_initial_state(
    telegram_id: str,
    channel: str = "telegram",
) -> dict:
    """Crea el estado inicial para una nueva conversación."""
    return {
        "messages": [],
        "customer": CustomerSession(telegram_id=telegram_id),
        "channel": channel,
        "intent": None,
        "previous_intent": None,
        "order": None,
        "order_stage": None,
        "found_products": [],
        "last_search_query": None,
        "upsell_suggestions": [],
        "upsell_offered": False,
        "needs_escalation": False,
        "escalation_reason": None,
        "current_node": "start",
        "waiting_for": None,
        "conversation_context": ConversationContext(),
        "is_new_conversation": True,
        "conversation_ended": False,
        "last_ruffo_message": None,
    }


def update_conversation_context(state: RuffoState, user_message: str) -> RuffoState:
    """Actualiza el contexto de la conversación."""
    if state.get("conversation_context") is None:
        state["conversation_context"] = ConversationContext()

    context = state["conversation_context"]
    context.add_message(user_message)

    # MEMORIA: Extraer info de mascota del mensaje
    context.extract_pet_info(user_message)

    # Actualizar flags del contexto
    if state.get("order") and state["order"].items:
        context.has_items_in_cart = True
    context.current_order_stage = state.get("order_stage")
    context.waiting_for = state.get("waiting_for")

    state["conversation_context"] = context
    return state


class OrderStageTransitions:
    """Transiciones válidas entre etapas del pedido."""

    TRANSITIONS = {
        None: ["collecting_items"],
        "collecting_items": ["confirming_items", "collecting_items"],
        "confirming_items": ["selecting_delivery", "collecting_items"],
        "selecting_delivery": ["collecting_address", "selecting_branch"],
        "collecting_address": ["selecting_payment"],
        "selecting_branch": ["selecting_payment"],
        "selecting_payment": ["waiting_payment_proof", "confirming_order"],
        "waiting_payment_proof": ["confirming_order"],
        "confirming_order": ["completed", "collecting_items"],
        "completed": [None],
    }

    @classmethod
    def can_transition(cls, from_stage: Optional[str], to_stage: str) -> bool:
        """Verifica si una transición es válida."""
        valid_next = cls.TRANSITIONS.get(from_stage, [])
        return to_stage in valid_next

    @classmethod
    def get_next_stages(cls, current_stage: Optional[str]) -> list[str]:
        """Obtiene las etapas siguientes válidas."""
        return cls.TRANSITIONS.get(current_stage, [])
