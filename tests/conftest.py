"""Configuración de pytest para tests de Ruffo."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_settings():
    """Mock de configuración."""
    with patch("src.config.settings.settings") as mock:
        mock.anthropic_api_key = "test-key"
        mock.telegram_bot_token = "test-token"
        mock.google_sheets_id = "test-sheet-id"
        mock.google_sheets_name = "test-sheet"
        mock.llm_model = "claude-sonnet-4-20250514"
        mock.llm_temperature = 0.7
        mock.llm_max_tokens = 1024
        mock.bot_debug = True
        yield mock


@pytest.fixture
def mock_sheets_client():
    """Mock del cliente de Google Sheets."""
    with patch("src.tools.sheets.client.get_client") as mock:
        client = MagicMock()
        client.get_all_as_dicts.return_value = [
            {
                "ID": "1",
                "Nombre": "Croquetas Premium Perro",
                "Categoria": "alimento_perro",
                "Marca": "Royal Canin",
                "Precio": "450.00",
                "Stock": "50",
                "Descripcion": "Alimento premium para perros adultos",
            },
            {
                "ID": "2",
                "Nombre": "Snacks de Pollo",
                "Categoria": "snacks_perro",
                "Marca": "Pedigree",
                "Precio": "85.00",
                "Stock": "100",
                "Descripcion": "Snacks de pollo para perros",
            },
        ]
        mock.return_value = client
        yield client


@pytest.fixture
def sample_state():
    """Estado de ejemplo para tests."""
    from src.agent.state import create_initial_state
    return create_initial_state(telegram_id="123456789")


@pytest.fixture
def sample_order():
    """Pedido de ejemplo para tests."""
    from src.schemas.order import OrderInProgress
    from src.schemas.product import ProductInCart

    order = OrderInProgress()
    order.add_item(ProductInCart(
        product_id="1",
        product_name="Croquetas Premium",
        quantity=2,
        unit_price=450.0,
    ))
    return order
