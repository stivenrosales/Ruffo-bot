"""Tests para tools de productos."""

import pytest
from unittest.mock import patch, MagicMock


class TestSearchProducts:
    """Tests para search_products."""

    @pytest.fixture
    def mock_client(self):
        """Mock del cliente de Sheets."""
        with patch("src.tools.sheets.products.get_client") as mock:
            client = MagicMock()
            client.get_all_as_dicts.return_value = [
                {
                    "ID": "1",
                    "Nombre": "Croquetas Premium Perro",
                    "Categoria": "alimento_perro",
                    "Marca": "Royal Canin",
                    "Precio": "450.00",
                    "Stock": "50",
                    "Descripcion": "Alimento premium",
                },
                {
                    "ID": "2",
                    "Nombre": "Snacks de Pollo",
                    "Categoria": "snacks_perro",
                    "Marca": "Pedigree",
                    "Precio": "85.00",
                    "Stock": "100",
                    "Descripcion": "Snacks deliciosos",
                },
                {
                    "ID": "3",
                    "Nombre": "Croquetas Gato Adulto",
                    "Categoria": "alimento_gato",
                    "Marca": "Whiskas",
                    "Precio": "350.00",
                    "Stock": "30",
                    "Descripcion": "Para gatos adultos",
                },
            ]
            mock.return_value = client
            yield client

    def test_search_finds_products(self, mock_client):
        """Verifica que encuentre productos por nombre."""
        from src.tools.sheets.products import search_products

        results = search_products.invoke({"query": "croquetas", "max_results": 5})

        assert len(results) == 2  # Croquetas perro y gato
        assert all("croquetas" in r["name"].lower() for r in results)

    def test_search_by_brand(self, mock_client):
        """Verifica búsqueda por marca."""
        from src.tools.sheets.products import search_products

        results = search_products.invoke({"query": "Royal Canin", "max_results": 5})

        assert len(results) == 1
        assert results[0]["brand"] == "Royal Canin"

    def test_search_respects_max_results(self, mock_client):
        """Verifica que respete el límite de resultados."""
        from src.tools.sheets.products import search_products

        results = search_products.invoke({"query": "croquetas", "max_results": 1})

        assert len(results) == 1

    def test_search_returns_empty_for_no_match(self, mock_client):
        """Verifica que devuelva lista vacía si no hay match."""
        from src.tools.sheets.products import search_products

        results = search_products.invoke({"query": "dinosaurio", "max_results": 5})

        assert results == []

    def test_search_parses_price_correctly(self, mock_client):
        """Verifica que parsee el precio correctamente."""
        from src.tools.sheets.products import search_products

        results = search_products.invoke({"query": "snacks", "max_results": 1})

        assert results[0]["price"] == 85.0
        assert isinstance(results[0]["price"], float)


class TestGetProductById:
    """Tests para get_product_by_id."""

    @pytest.fixture
    def mock_client(self):
        """Mock del cliente de Sheets."""
        with patch("src.tools.sheets.products.get_client") as mock:
            client = MagicMock()
            client.get_all_as_dicts.return_value = [
                {
                    "ID": "1",
                    "Nombre": "Croquetas Premium",
                    "Categoria": "alimento_perro",
                    "Marca": "Royal Canin",
                    "Precio": "450.00",
                    "Stock": "50",
                },
            ]
            mock.return_value = client
            yield client

    def test_get_existing_product(self, mock_client):
        """Verifica obtención de producto existente."""
        from src.tools.sheets.products import get_product_by_id

        result = get_product_by_id.invoke({"product_id": "1"})

        assert result is not None
        assert result["id"] == "1"
        assert result["name"] == "Croquetas Premium"

    def test_get_nonexistent_product(self, mock_client):
        """Verifica que devuelva None para producto inexistente."""
        from src.tools.sheets.products import get_product_by_id

        result = get_product_by_id.invoke({"product_id": "999"})

        assert result is None
