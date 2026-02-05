"""Tests para el estado del agente."""

import pytest
from src.agent.state import (
    create_initial_state,
    update_conversation_context,
    OrderStageTransitions,
)
from src.schemas.order import OrderInProgress
from src.schemas.product import ProductInCart


class TestCreateInitialState:
    """Tests para create_initial_state."""

    def test_creates_state_with_telegram_id(self):
        """Verifica que se cree el estado con el telegram_id."""
        state = create_initial_state(telegram_id="123456")

        assert state["customer"].telegram_id == "123456"
        assert state["channel"] == "telegram"
        assert state["is_new_conversation"] is True

    def test_creates_empty_messages(self):
        """Verifica que los mensajes estén vacíos inicialmente."""
        state = create_initial_state(telegram_id="123456")

        assert state["messages"] == []

    def test_creates_none_order(self):
        """Verifica que el pedido sea None inicialmente."""
        state = create_initial_state(telegram_id="123456")

        assert state["order"] is None
        assert state["order_stage"] is None


class TestOrderStageTransitions:
    """Tests para transiciones de etapas del pedido."""

    def test_can_transition_from_none_to_collecting(self):
        """Verifica transición de None a collecting_items."""
        assert OrderStageTransitions.can_transition(None, "collecting_items") is True

    def test_cannot_transition_from_none_to_completed(self):
        """Verifica que no se pueda saltar a completed."""
        assert OrderStageTransitions.can_transition(None, "completed") is False

    def test_can_transition_from_confirming_to_delivery(self):
        """Verifica transición de confirming_items a selecting_delivery."""
        assert OrderStageTransitions.can_transition(
            "confirming_items", "selecting_delivery"
        ) is True

    def test_get_next_stages(self):
        """Verifica obtención de siguientes etapas."""
        next_stages = OrderStageTransitions.get_next_stages("selecting_delivery")

        assert "collecting_address" in next_stages
        assert "selecting_branch" in next_stages


class TestOrderInProgress:
    """Tests para OrderInProgress."""

    def test_add_item(self):
        """Verifica agregar item al pedido."""
        order = OrderInProgress()
        item = ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=1,
            unit_price=100.0,
        )

        order.add_item(item)

        assert len(order.items) == 1
        assert order.items[0].product_name == "Croquetas"

    def test_add_existing_item_increases_quantity(self):
        """Verifica que agregar item existente aumente cantidad."""
        order = OrderInProgress()
        item1 = ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=1,
            unit_price=100.0,
        )
        item2 = ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=2,
            unit_price=100.0,
        )

        order.add_item(item1)
        order.add_item(item2)

        assert len(order.items) == 1
        assert order.items[0].quantity == 3

    def test_subtotal_calculation(self):
        """Verifica cálculo de subtotal."""
        order = OrderInProgress()
        order.add_item(ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=2,
            unit_price=100.0,
        ))
        order.add_item(ProductInCart(
            product_id="2",
            product_name="Snacks",
            quantity=1,
            unit_price=50.0,
        ))

        assert order.subtotal == 250.0

    def test_remove_item(self):
        """Verifica eliminación de item."""
        order = OrderInProgress()
        order.add_item(ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=1,
            unit_price=100.0,
        ))

        result = order.remove_item("1")

        assert result is True
        assert len(order.items) == 0

    def test_clear_order(self):
        """Verifica limpieza del pedido."""
        order = OrderInProgress()
        order.add_item(ProductInCart(
            product_id="1",
            product_name="Croquetas",
            quantity=1,
            unit_price=100.0,
        ))

        order.clear()

        assert len(order.items) == 0
        assert order.delivery_type is None
