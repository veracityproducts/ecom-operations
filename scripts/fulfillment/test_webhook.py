#!/usr/bin/env python3
"""
Test Shopify webhook locally by sending a sample order.

This simulates what Shopify would send when an order is created.
"""
import httpx
import asyncio
import json
from datetime import datetime
import hmac
import hashlib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

# Sample Shopify order data (based on actual Shopify webhook format)
SAMPLE_ORDER = {
    "id": 5678901234,
    "admin_graphql_api_id": "gid://shopify/Order/5678901234",
    "email": "test@example.com",
    "closed_at": None,
    "created_at": datetime.utcnow().isoformat() + "Z",
    "updated_at": datetime.utcnow().isoformat() + "Z",
    "number": 1001,
    "note": None,
    "token": "abcdef123456",
    "gateway": "manual",
    "test": True,
    "total_price": "89.99",
    "subtotal_price": "79.99",
    "total_weight": 1000,
    "total_tax": "10.00",
    "taxes_included": True,
    "currency": "USD",
    "financial_status": "paid",
    "confirmed": True,
    "total_discounts": "0.00",
    "total_line_items_price": "79.99",
    "cart_token": None,
    "buyer_accepts_marketing": False,
    "name": "#1001",
    "referring_site": None,
    "landing_site": None,
    "cancelled_at": None,
    "cancel_reason": None,
    "total_price_usd": "89.99",
    "checkout_token": None,
    "reference": None,
    "user_id": None,
    "location_id": None,
    "source_identifier": None,
    "source_url": None,
    "processed_at": datetime.utcnow().isoformat() + "Z",
    "device_id": None,
    "phone": None,
    "customer_locale": "en",
    "app_id": 123456,
    "browser_ip": "127.0.0.1",
    "landing_site_ref": None,
    "order_number": 2001,
    "discount_codes": [],
    "note_attributes": [],
    "payment_gateway_names": ["manual"],
    "processing_method": "manual",
    "checkout_id": None,
    "source_name": "shopify_draft_order",
    "fulfillment_status": None,
    "tax_lines": [],
    "tags": "",
    "contact_email": "test@example.com",
    "order_status_url": "https://checkout.shopify.com/orders/abcdef123456",
    "line_items": [
        {
            "id": 12345678901,
            "variant_id": 44444444444,
            "title": "Code Breakers Book Set",
            "quantity": 1,
            "sku": "CB-SET-001",
            "variant_title": "Complete Set",
            "vendor": "Grooved Learning",
            "fulfillment_service": "manual",
            "product_id": 8888888888,
            "requires_shipping": True,
            "taxable": True,
            "gift_card": False,
            "name": "Code Breakers Book Set - Complete Set",
            "variant_inventory_management": "shopify",
            "properties": [],
            "product_exists": True,
            "fulfillable_quantity": 1,
            "grams": 1000,
            "price": "79.99",
            "total_discount": "0.00",
            "fulfillment_status": None,
            "discount_allocations": [],
            "tax_lines": []
        }
    ],
    "shipping_lines": [
        {
            "id": 4444444444,
            "title": "Standard Shipping",
            "price": "10.00",
            "code": "STANDARD",
            "source": "shopify",
            "phone": None,
            "requested_fulfillment_service_id": None,
            "delivery_category": None,
            "carrier_identifier": None,
            "discounted_price": "10.00",
            "discount_allocations": [],
            "tax_lines": []
        }
    ],
    "billing_address": {
        "first_name": "Test",
        "address1": "123 Billing St",
        "phone": "555-1234",
        "city": "Los Angeles",
        "zip": "90210",
        "province": "California",
        "country": "United States",
        "last_name": "Customer",
        "address2": None,
        "company": None,
        "latitude": 34.0522,
        "longitude": -118.2437,
        "name": "Test Customer",
        "country_code": "US",
        "province_code": "CA"
    },
    "shipping_address": {
        "first_name": "Test",
        "address1": "456 Shipping Ave",
        "phone": "555-5678",
        "city": "San Francisco",
        "zip": "94102",
        "province": "California",
        "country": "United States",
        "last_name": "Customer",
        "address2": "Apt 2B",
        "company": None,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "Test Customer",
        "country_code": "US",
        "province_code": "CA"
    },
    "customer": {
        "id": 6666666666,
        "email": "test@example.com",
        "accepts_marketing": False,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "first_name": "Test",
        "last_name": "Customer",
        "orders_count": 1,
        "state": "enabled",
        "total_spent": "89.99",
        "last_order_id": 5678901234,
        "note": None,
        "verified_email": True,
        "multipass_identifier": None,
        "tax_exempt": False,
        "phone": None,
        "tags": "",
        "last_order_name": "#1001",
        "currency": "USD",
        "accepts_marketing_updated_at": "2024-01-01T00:00:00Z",
        "marketing_opt_in_level": None,
        "admin_graphql_api_id": "gid://shopify/Customer/6666666666"
    }
}


def calculate_webhook_signature(data: bytes, secret: str) -> str:
    """Calculate Shopify webhook signature."""
    return base64.b64encode(
        hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
    ).decode()


async def send_test_webhook():
    """Send test webhook to local server."""
    webhook_url = "http://localhost:8750/webhooks/shopify/order-create"
    
    # Prepare webhook data
    order_data = SAMPLE_ORDER.copy()
    order_data["id"] = int(datetime.now().timestamp() * 1000)  # Unique ID
    order_data["order_number"] = 1000 + int(datetime.now().timestamp() % 1000)
    order_data["name"] = f"#{order_data['order_number']}"
    
    # Convert to JSON
    payload = json.dumps(order_data)
    
    # Calculate signature if webhook secret is available
    webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Topic": "orders/create",
        "X-Shopify-Shop-Domain": os.getenv("SHOPIFY_SHOP_DOMAIN", "test-shop") + ".myshopify.com",
        "X-Shopify-API-Version": "2024-01",
        "X-Shopify-Webhook-Id": "test-webhook-123"
    }
    
    if webhook_secret:
        signature = calculate_webhook_signature(payload.encode(), webhook_secret)
        headers["X-Shopify-Hmac-Sha256"] = signature
    
    print("📦 Sending test order webhook...")
    print(f"   Order ID: {order_data['id']}")
    print(f"   Order Number: {order_data['order_number']}")
    print(f"   Customer: {order_data['customer']['email']}")
    print(f"   Total: ${order_data['total_price']}")
    print()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                webhook_url,
                content=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Webhook accepted!")
                print(f"   Response: {json.dumps(result, indent=2)}")
                print()
                print("📁 Check the data/orders/ directory for:")
                print(f"   - order_{order_data['id']}.json")
                print(f"   - label_{order_data['id']}.json (after processing)")
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except httpx.ConnectError:
            print("❌ Could not connect to server")
            print("   Make sure the fulfillment server is running:")
            print("   ./run_fulfillment.sh")
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main test flow."""
    print("🧪 Shopify Webhook Test")
    print("=" * 40)
    print()
    
    # Check if server is running
    print("Checking if fulfillment server is running...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8750/health", timeout=2.0)
            if response.status_code == 200:
                health = response.json()
                print("✅ Server is running")
                print(f"   Status: {health['status']}")
                print()
            else:
                print("⚠️  Server returned unexpected status")
        except:
            print("❌ Server is not running!")
            print("   Start it with: ./run_fulfillment.sh")
            return
    
    # Send test webhook
    await send_test_webhook()
    
    # Wait for processing
    print("\n⏳ Waiting for order processing...")
    await asyncio.sleep(5)
    
    # Check if label was created
    print("\n📊 Checking results...")
    order_id = SAMPLE_ORDER["id"]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://localhost:8750/orders/{order_id}")
            if response.status_code == 200:
                order = response.json()
                if "fulfillment" in order:
                    print("✅ Order fulfilled!")
                    print(f"   Tracking: {order['fulfillment'].get('tracking_number')}")
                    print(f"   Label URL: {order['fulfillment'].get('label_url')}")
                else:
                    print("⏳ Order received but not yet fulfilled")
                    print("   Check logs for any errors")
            else:
                print("❓ Could not retrieve order status")
        except Exception as e:
            print(f"❌ Error checking order: {e}")


if __name__ == "__main__":
    asyncio.run(main())