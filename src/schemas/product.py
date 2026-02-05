"""Esquemas de producto."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ProductCategory(str, Enum):
    """Categorías de productos."""

    ALIMENTO_PERRO = "alimento_perro"
    ALIMENTO_GATO = "alimento_gato"
    SNACKS_PERRO = "snacks_perro"
    SNACKS_GATO = "snacks_gato"
    JUGUETES = "juguetes"
    HIGIENE = "higiene"
    SALUD = "salud"
    ACCESORIOS = "accesorios"
    OTROS = "otros"


class Product(BaseModel):
    """Esquema de producto del catálogo."""

    id: str = Field(..., description="ID único del producto")
    name: str = Field(..., min_length=2, max_length=200, description="Nombre del producto")
    category: str = Field(..., description="Categoría del producto")
    brand: Optional[str] = Field(default=None, description="Marca")
    price: float = Field(..., gt=0, description="Precio en MXN")
    stock: int = Field(default=0, ge=0, description="Unidades disponibles")
    description: Optional[str] = Field(default=None, description="Descripción del producto")
    image_url: Optional[str] = Field(default=None, description="URL de imagen")
    sku: Optional[str] = Field(default=None, description="Código SKU")
    is_active: bool = Field(default=True, description="Producto activo para venta")

    class Config:
        from_attributes = True


class ProductInCart(BaseModel):
    """Producto dentro del carrito de compras."""

    product_id: str = Field(..., description="ID del producto")
    product_name: str = Field(..., description="Nombre del producto")
    quantity: int = Field(..., gt=0, description="Cantidad")
    unit_price: float = Field(..., gt=0, description="Precio unitario")

    @property
    def subtotal(self) -> float:
        """Calcula el subtotal del item."""
        return self.quantity * self.unit_price

    def to_dict(self) -> dict:
        """Convierte a diccionario incluyendo subtotal."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
        }


class ProductSearchResult(BaseModel):
    """Resultado de búsqueda de productos."""

    products: list[Product] = Field(default_factory=list)
    total_found: int = Field(default=0)
    query: str = Field(default="")
