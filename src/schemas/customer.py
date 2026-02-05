"""Esquemas de cliente."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CustomerCreate(BaseModel):
    """Esquema para crear un cliente."""

    name: str = Field(..., min_length=2, max_length=100, description="Nombre del cliente")
    phone: Optional[str] = Field(default=None, description="Teléfono del cliente")
    telegram_id: Optional[str] = Field(default=None, description="ID de Telegram")
    address: Optional[str] = Field(default=None, description="Dirección principal")


class Customer(CustomerCreate):
    """Esquema completo de cliente."""

    id: str = Field(..., description="ID único del cliente")
    is_wholesaler: bool = Field(default=False, description="Es cliente mayorista")
    created_at: datetime = Field(default_factory=datetime.now, description="Fecha de registro")
    total_orders: int = Field(default=0, description="Total de pedidos realizados")
    pet_name: Optional[str] = Field(default=None, description="Nombre de la mascota")
    pet_type: Optional[str] = Field(default=None, description="Tipo de mascota (perro, gato, etc.)")

    class Config:
        from_attributes = True


class CustomerSession(BaseModel):
    """Información del cliente durante la sesión de chat."""

    telegram_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    pet_name: Optional[str] = None
    pet_type: Optional[str] = None
    is_wholesaler: bool = False
    is_new: bool = True
