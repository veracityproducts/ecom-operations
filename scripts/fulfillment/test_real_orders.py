#!/usr/bin/env python3
"""
Test the fulfillment system with a couple of real orders from the conversation.
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FULFILLMENT_API_URL = os.getenv("FULFILLMENT_API_URL", "http://localhost:8750")

# Real order data from unfulfilled_orders_20250801_022951.json
TEST_ORDERS = [
    {
        "id": 6396689547572,
        "name": "#111710",
        "order_number": "111710",
        "email": "v4bD3XSD5I4LJ45CPLJ4AYE43ZZ3Q@scs.tiktokw.us",
        "created_at": "2025-08-01T01:25:48-04:00",
        "updated_at": "2025-08-01T01:25:48-04:00",
        "currency": "USD",
        "total_price": "30.22",
        "subtotal_price": "27.98",
        "total_tax": "2.24",
        "financial_status": "paid",
        "fulfillment_status": None,
        "source_name": "tiktok",
        "line_items": [
            {
                "id": 16005477859636,
                "name": "Women's Linen Bible Verse Mapping Journal - 7\" x 10\" - Deep Purple",
                "quantity": 1,
                "price": "39.99",
                "sku": "VerseMappingJournalPurple",
                "fulfillable_quantity": 1,
                "grams": 998
            }
        ],
        "shipping_address": {
            "first_name": "Ashley",
            "last_name": "Batiste",
            "address1": "5921 HEATHERWOOD CT",
            "city": "Mobile",
            "province": "Alabama",
            "zip": "36618",
            "country": "United States",
            "country_code": "US",
            "province_code": "AL"
        },
        "customer": {
            "first_name": "Ashley",
            "last_name": "Batiste",
            "email": "v4bD3XSD5I4LJ45CPLJ4AYE43ZZ3Q@scs.tiktokw.us"
        },
        "shipping_lines": [
            {
                "title": "Shipped by Seller: Standard Shipping",
                "price": "0.00"
            }
        ]
    },
    {
        "id": 6396634300724,
        "name": "#111707",
        "order_number": "111707",
        "email": "canal_customer+6856390118087@shopcanal.com",
        "created_at": "2025-08-01T00:25:40-04:00",
        "updated_at": "2025-08-01T00:25:40-04:00",
        "currency": "USD",
        "total_price": "35.00",
        "subtotal_price": "35.00", 
        "total_tax": "0.00",
        "financial_status": "paid",
        "fulfillment_status": None,
        "source_name": "Canal",
        "line_items": [
            {
                "id": 16005366743348,
                "name": "Reusable Grooved Handwriting Workbooks for Kids With Disappearing Ink - Letters and First Words + Numbers and Shapes",
                "quantity": 1,
                "price": "35.00",
                "sku": "00-0NGH-AA4O",
                "fulfillable_quantity": 1,
                "grams": 816
            }
        ],
        "shipping_address": {
            "first_name": "True",
            "last_name": "Story",
            "address1": "462 Winslow Ave",
            "city": "Buffalo",
            "province": "New York",
            "zip": "14211",
            "country": "United States",
            "country_code": "US",
            "province_code": "NY"
        },
        "customer": {
            "first_name": "True",
            "last_name": "Story",
            "email": "canal_customer+6856390118087@shopcanal.com"
        },
        "shipping_lines": [
            {
                "title": "Flat Rate Shipping",
                "price": "0.00"
            }
        ]
    }
]


async def test_order_ingestion():
    """Test sending orders to the fulfillment webhook."""
    async with httpx.AsyncClient() as client:
        # First check server health
        try:
            response = await client.get(f"{FULFILLMENT_API_URL}/health")
            if response.status_code == 200:
                print("✅ Fulfillment server is healthy")
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Cannot connect to fulfillment server: {e}")
            print("💡 Make sure the server is running on port 8750")
            return
        
        print(f"\n📤 Testing {len(TEST_ORDERS)} real orders...")
        
        for order in TEST_ORDERS:
            print(f"\n🛍️  Processing order {order['name']} (${order['total_price']})")
            
            try:
                response = await client.post(
                    f"{FULFILLMENT_API_URL}/test/order-webhook",
                    json=order,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Success: {result.get('message', 'Order processed')}")
                    if 'order_id' in result:
                        print(f"   📁 Stored as: {result['order_id']}")
                else:
                    print(f"   ❌ Failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Small delay between orders
            await asyncio.sleep(0.5)
        
        print("\n✨ Order ingestion test complete!")
        print("\n💡 Next steps:")
        print("   - Check data/orders/ for stored order files")
        print("   - Use GET /orders to see all orders")
        print("   - Use POST /orders/{order_id}/fulfill to create labels")


if __name__ == "__main__":
    asyncio.run(test_order_ingestion())