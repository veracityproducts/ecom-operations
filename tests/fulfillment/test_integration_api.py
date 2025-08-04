#!/usr/bin/env python3
"""Integration tests for the FastAPI fulfillment service."""
import pytest
from pathlib import Path
import sys
import json
from unittest.mock import AsyncMock, patch

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from fulfillment.main import app


@pytest.fixture
def client():
    """Create test client with proper lifespan management."""
    with TestClient(app) as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "checks" in data
    assert "timestamp" in data
    assert "environment" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Grooved Learning Fulfillment"
    assert data["version"] == "1.0.0"


def test_order_status_not_found(client):
    """Test order status for non-existent order."""
    response = client.get("/orders/999999/status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "pending"
    assert data["order_id"] == "999999"


def test_get_order_not_found(client):
    """Test get order for non-existent order."""
    response = client.get("/orders/999999")
    assert response.status_code == 404


@patch("fulfillment.main.process_order_fulfillment")
def test_webhook_handler_invalid_json(mock_process, client):
    """Test webhook handler with invalid JSON - should fail gracefully."""
    response = client.post(
        "/webhooks/shopify/order-create",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    # Expected to return 500 due to general exception handling
    # In production, this would trigger alerting
    assert response.status_code == 500
    mock_process.assert_not_called()


@patch("fulfillment.main.process_order_fulfillment")
def test_webhook_handler_valid_order(mock_process, client):
    """Test webhook handler with valid order data."""
    # Mock the process function to avoid actual fulfillment
    mock_process.return_value = None
    
    # Sample Shopify order webhook payload
    order_data = {
        "id": 12345,
        "order_number": "GL-1001",
        "name": "#GL-1001",
        "email": "customer@example.com",
        "total_price": "29.99",
        "currency": "USD",
        "financial_status": "paid",
        "fulfillment_status": None,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "shipping_address": {
            "name": "John Doe",
            "address1": "123 Main St",
            "city": "Anytown",
            "province_code": "CA",
            "zip": "90210",
            "country_code": "US",
            "phone": "555-1234"
        },
        "line_items": [
            {
                "name": "Code Breakers Book Set",
                "quantity": 1,
                "price": "29.99",
                "sku": "CB-BOOK-SET",
                "grams": 1000
            }
        ]
    }
    
    with patch("fulfillment.shopify.webhook_handler.ShopifyWebhookHandler.verify_webhook_signature", return_value=True):
        response = client.post(
            "/webhooks/shopify/order-create",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["order_id"] == 12345
    assert data["order_number"] == "GL-1001"


def test_app_lifespan():
    """Test that app lifecycle management works correctly."""
    # This test ensures the app can start and stop without errors
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200