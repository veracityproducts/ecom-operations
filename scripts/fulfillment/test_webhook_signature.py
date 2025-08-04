#!/usr/bin/env python3
"""Test webhook signature verification for Shopify webhooks."""
import hmac
import hashlib
import base64
import json
import httpx
from datetime import datetime

# Test webhook secret - this should match what's configured in Shopify
WEBHOOK_SECRET = "test_webhook_secret_123"

# Sample order payload
sample_order = {
    "id": 999999,
    "order_number": "1999",
    "name": "#1999",
    "email": "test@example.com",
    "total_price": "50.00",
    "currency": "USD",
    "fulfillment_status": None,
    "financial_status": "paid",
    "created_at": datetime.utcnow().isoformat() + "Z",
    "updated_at": datetime.utcnow().isoformat() + "Z",
    "shipping_address": {
        "first_name": "Test",
        "last_name": "Customer",
        "address1": "123 Test St",
        "city": "Los Angeles",
        "province": "California",
        "province_code": "CA",
        "country": "United States",
        "country_code": "US",
        "zip": "90210",
        "phone": "555-1234"
    },
    "line_items": [
        {
            "id": 111,
            "name": "Test Product",
            "quantity": 1,
            "price": "50.00",
            "sku": "TEST-SKU-001",
            "grams": 500
        }
    ]
}

def generate_webhook_signature(payload_json: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Base64 encode the signature
    return base64.b64encode(signature).decode('utf-8')


def test_signature_verification():
    """Test webhook signature verification locally."""
    print("Testing webhook signature verification...")
    print(f"Using webhook secret: {WEBHOOK_SECRET[:10]}...")
    
    # Convert order to JSON
    payload_json = json.dumps(sample_order, separators=(',', ':'))
    print(f"\nPayload size: {len(payload_json)} bytes")
    
    # Generate signature
    signature = generate_webhook_signature(payload_json, WEBHOOK_SECRET)
    print(f"Generated signature: {signature[:20]}...")
    
    # Test verification (simulating what the webhook handler does)
    print("\nVerifying signature...")
    
    # Recalculate signature
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
    
    # Compare
    is_valid = hmac.compare_digest(signature, expected_signature_base64)
    print(f"Signature valid: {is_valid}")
    
    return signature, payload_json


async def test_webhook_endpoint():
    """Test the actual webhook endpoint with signature."""
    print("\n" + "="*50)
    print("Testing webhook endpoint...")
    
    # Generate signature
    signature, payload_json = test_signature_verification()
    
    # Test with local server
    async with httpx.AsyncClient() as client:
        try:
            # First test the test endpoint (no signature required)
            print("\n1. Testing test endpoint (no signature)...")
            response = await client.post(
                "http://localhost:8750/test/order-webhook",
                json=sample_order
            )
            print(f"Response status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            # Then test production endpoint with signature
            print("\n2. Testing production endpoint (with signature)...")
            response = await client.post(
                "http://localhost:8750/webhooks/shopify/order-create",
                content=payload_json,
                headers={
                    "X-Shopify-Hmac-Sha256": signature,
                    "Content-Type": "application/json"
                }
            )
            print(f"Response status: {response.status_code}")
            print(f"Response: {response.json()}")
            
        except httpx.ConnectError:
            print("❌ Could not connect to server. Make sure it's running on port 8750")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import asyncio
    
    # Run signature test
    test_signature_verification()
    
    # Run endpoint test
    print("\nMake sure the fulfillment server is running (uv run fulfillment/main.py)")
    input("Press Enter to test the webhook endpoint...")
    
    asyncio.run(test_webhook_endpoint())