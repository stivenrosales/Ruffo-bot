"""Esquemas de pedido."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

from .product import ProductInCart


class DeliveryType(str, Enum):
    """Tipos de entrega."""

    PICKUP = "pickup"
    DELIVERY = "delivery"


class OrderStatus(str, Enum):
    """Estados del pedido."""

    COLLECTING = "collecting"  # Agregando productos
    CONFIRMING_ITEMS = "confirming_items"  # Confirmando carrito
    SELECTING_DELIVERY = "selecting_delivery"  # Eligiendo entrega
    COLLECTING_ADDRESS = "collecting_address"  # Pidiendo dirección
    SELECTING_PAYMENT = "selecting_payment"  # Eligiendo pago
    WAITING_PAYMENT_PROOF = "waiting_payment_proof"  # Esperando comprobante
    CONFIRMING = "confirming"  # Confirmación final
    COMPLETED = "completed"  # Pedido completado
    CANCELLED = "cancelled"  # Pedido cancelado


class PaymentMethod(str, Enum):
    """Métodos de pago."""

    CASH = "efectivo"
    TRANSFER = "transferencia"
    CARD = "tarjeta"


class OrderItem(BaseModel):
    """Item de un pedido."""

    product_id: str
    product_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    subtotal: float = Field(..., gt=0)


class OrderCreate(BaseModel):
    """Esquema para crear un pedido."""

    customer_id: str
    customer_name: str
    items: list[OrderItem] = Field(..., min_length=1)
    delivery_type: DeliveryType
    delivery_address: Optional[str] = None
    branch_id: Optional[str] = None
    payment_method: PaymentMethod
    notes: Optional[str] = None

    @field_validator("delivery_address")
    @classmethod
    def validate_delivery_address(cls, v, info):
        """Valida que haya dirección si es delivery."""
        if info.data.get("delivery_type") == DeliveryType.DELIVERY and not v:
            raise ValueError("Dirección requerida para envío a domicilio")
        return v


class Order(OrderCreate):
    """Esquema completo de pedido."""

    id: str = Field(..., description="ID del pedido")
    status: OrderStatus = Field(default=OrderStatus.COLLECTING)
    subtotal: float = Field(default=0.0)
    shipping_cost: float = Field(default=0.0)
    total: float = Field(default=0.0)
    payment_proof_received: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    channel: str = Field(default="telegram")

    class Config:
        from_attributes = True


class OrderInProgress(BaseModel):
    """Pedido en construcción durante la conversación."""

    items: list[ProductInCart] = Field(default_factory=list)
    delivery_type: Optional[DeliveryType] = None
    delivery_address: Optional[str] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    payment_proof_url: Optional[str] = None
    notes: Optional[str] = None

    @property
    def subtotal(self) -> float:
        """Calcula el subtotal del pedido."""
        return sum(item.subtotal for item in self.items)

    @property
    def shipping_cost(self) -> float:
        """Calcula el costo de envío."""
        if self.delivery_type == DeliveryType.DELIVERY:
            # Envío gratis arriba de $500
            return 0.0 if self.subtotal >= 500 else 50.0
        return 0.0

    @property
    def total(self) -> float:
        """Calcula el total del pedido."""
        return self.subtotal + self.shipping_cost

    @property
    def item_count(self) -> int:
        """Cuenta total de items."""
        return sum(item.quantity for item in self.items)

    def add_item(self, item: ProductInCart) -> None:
        """Agrega un item al pedido."""
        # Verificar si ya existe el producto
        for existing in self.items:
            if existing.product_id == item.product_id:
                existing.quantity += item.quantity
                return
        self.items.append(item)

    def remove_item(self, product_id: str) -> bool:
        """Elimina un item del pedido."""
        for i, item in enumerate(self.items):
            if item.product_id == product_id:
                self.items.pop(i)
                return True
        return False

    def clear(self) -> None:
        """Limpia el pedido."""
        self.items = []
        self.delivery_type = None
        self.delivery_address = None
        self.branch_id = None
        self.payment_method = None

    def to_summary(self) -> str:
        """Genera un resumen del pedido."""
        lines = ["📦 **Tu pedido:**"]
        for item in self.items:
            lines.append(f"  • {item.quantity}x {item.product_name} - ${item.subtotal:.2f}")
        lines.append(f"\n💰 Subtotal: ${self.subtotal:.2f}")
        if self.shipping_cost > 0:
            lines.append(f"🚚 Envío: ${self.shipping_cost:.2f}")
        lines.append(f"**Total: ${self.total:.2f}**")
        return "\n".join(lines)
