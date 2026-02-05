"""Esquemas de intenciones del usuario."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class UserIntent(str, Enum):
    """Intenciones detectables del usuario."""

    GREETING = "greeting"
    BUY_ORDER = "buy_order"
    PRODUCT_INQUIRY = "product_inquiry"
    BRANCH_INFO = "branch_info"
    PROBLEM_ESCALATION = "problem_escalation"
    WHOLESALER = "wholesaler"
    ORDER_STATUS = "order_status"
    PAYMENT_PROOF = "payment_proof"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


class IntentClassification(BaseModel):
    """Resultado de clasificación de intención."""

    intent: UserIntent = Field(..., description="Intención detectada")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confianza")
    raw_response: Optional[str] = Field(default=None, description="Respuesta raw del LLM")


class DetectedEntities(BaseModel):
    """Entidades extraídas del mensaje."""

    product_names: list[str] = Field(default_factory=list)
    quantities: list[int] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    pet_names: list[str] = Field(default_factory=list)
    branch_names: list[str] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Contexto de la conversación para el clasificador."""

    recent_messages: list[str] = Field(default_factory=list, max_length=5)
    current_order_stage: Optional[str] = None
    has_items_in_cart: bool = False
    waiting_for: Optional[str] = None  # address, payment, confirmation, etc.

    # MEMORIA: Información de la mascota del usuario
    pet_type: Optional[str] = None  # "perro", "gato", etc.
    pet_name: Optional[str] = None  # Nombre de la mascota si lo menciona
    product_type_needed: Optional[str] = None  # "comida", "snack", "juguete", etc.

    def add_message(self, message: str) -> None:
        """Agrega un mensaje al contexto."""
        self.recent_messages.append(message)
        if len(self.recent_messages) > 5:
            self.recent_messages.pop(0)

    def extract_pet_info(self, message: str) -> None:
        """Extrae información de la mascota del mensaje."""
        message_lower = message.lower()

        # Detectar tipo de mascota
        cat_words = ["gato", "gata", "gatito", "gatita", "minino", "michi", "felino"]
        dog_words = ["perro", "perra", "perrito", "perrita", "cachorro", "can", "canino", "lomito"]

        for word in cat_words:
            if word in message_lower:
                self.pet_type = "gato"
                break

        for word in dog_words:
            if word in message_lower:
                self.pet_type = "perro"
                break

        # Detectar tipo de producto que busca
        product_types = {
            "comida": ["comida", "croqueta", "alimento", "come"],
            "snack": ["snack", "premio", "golosina", "treat"],
            "juguete": ["juguete", "pelota", "jugar"],
            "higiene": ["shampoo", "baño", "limpieza"],
            "arena": ["arena", "arenero"],
            "accesorio": ["collar", "correa", "cama", "plato"],
        }

        for product_type, keywords in product_types.items():
            for keyword in keywords:
                if keyword in message_lower:
                    self.product_type_needed = product_type
                    break

    def to_string(self) -> str:
        """Convierte el contexto a string para el prompt."""
        parts = []
        if self.recent_messages:
            parts.append(f"Mensajes recientes: {' | '.join(self.recent_messages[-3:])}")
        if self.pet_type:
            parts.append(f"Mascota del cliente: {self.pet_type}")
        if self.pet_name:
            parts.append(f"Nombre de la mascota: {self.pet_name}")
        if self.product_type_needed:
            parts.append(f"Busca: {self.product_type_needed}")
        if self.current_order_stage:
            parts.append(f"Etapa del pedido: {self.current_order_stage}")
        if self.has_items_in_cart:
            parts.append("El cliente tiene productos en el carrito")
        if self.waiting_for:
            parts.append(f"Esperando: {self.waiting_for}")
        return "; ".join(parts) if parts else "Sin contexto previo"

    def has_enough_info_to_search(self) -> bool:
        """Verifica si tenemos suficiente info para buscar productos."""
        return self.pet_type is not None and self.product_type_needed is not None

    def get_search_query(self) -> str:
        """Genera query de búsqueda basado en el contexto."""
        parts = []
        if self.product_type_needed:
            parts.append(self.product_type_needed)
        if self.pet_type:
            parts.append(self.pet_type)
        return " ".join(parts)
