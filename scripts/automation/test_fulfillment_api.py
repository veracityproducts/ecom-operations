#!/usr/bin/env python3
"""Test the fulfillment API endpoints."""
import httpx
import asyncio
import json
from datetime import datetime


async def test_api():
    """Test fulfillment API endpoints."""
    print("🧪 Testing Fulfillment API\n")
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Health check passed")
                print(f"   Status: {data['status']}")
                print(f"   Checks: {json.dumps(data['checks'], indent=6)}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print("   Make sure the server is running: cd fulfillment && uv run uvicorn main:app --reload")
            return
            
        # Test webhook endpoint with sample order
        print("\n2. Testing order webhook...")
        sample_order = {
            "id": 123456,
            "order_number": "1001",
            "created_at": datetime.utcnow().isoformat(),
            "shipping_address": {
                "first_name": "Test",
                "last_name": "Customer",
                "address1": "123 Main Street",
                "city": "Los Angeles",
                "province_code": "CA",
                "zip": "90210",
                "country_code": "US",
                "phone": "555-1234"
            },
            "line_items": [
                {
                    "name": "Code Breakers Book Set",
                    "quantity": 1,
                    "price": "79.99"
                }
            ]
        }
        
        try:
            response = await client.post(
                f"{base_url}/webhooks/shopify/order-create",
                json=sample_order
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Webhook accepted")
                print(f"   Order ID: {data['order_id']}")
                print(f"   Message: {data['message']}")
            else:
                print(f"   ❌ Webhook failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Check order status
        print("\n3. Checking order status...")
        try:
            response = await client.get(f"{base_url}/orders/123456")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Order found")
                if "fulfillment" in data:
                    print(f"   📦 Tracking: {data['fulfillment'].get('tracking_number')}")
                    print(f"   🏷️  Label URL: {data['fulfillment'].get('label_url')}")
                else:
                    print("   ⏳ Fulfillment pending...")
            else:
                print(f"   ❌ Order not found: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("NOTE: Make sure the server is running first:")
    print("  cd fulfillment && uv run uvicorn main:app --reload\n")
    asyncio.run(test_api())