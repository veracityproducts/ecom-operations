#!/usr/bin/env python3
"""Test Shopify fulfillment API directly."""
import asyncio
import httpx
import json
from datetime import datetime, timedelta

# Direct API test
async def test_fulfillment_api():
    """Test different fulfillment approaches."""
    
    # API credentials
    import os
    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "your-shop.myshopify.com")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "your-access-token-here")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    base_url = f"https://{shop_domain}/admin/api/{api_version}"
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Get a recent unfulfilled order
        print("🔍 Finding recent unfulfilled order...")
        created_at_min = (datetime.now() - timedelta(days=2)).isoformat()
        
        response = await client.get(
            f"{base_url}/orders.json",
            params={
                "status": "any",
                "created_at_min": created_at_min,
                "limit": 10,
                "fulfillment_status": "unfulfilled"
            }
        )
        
        orders = response.json()["orders"]
        if not orders:
            print("❌ No unfulfilled orders found")
            return
            
        order = orders[0]
        order_id = order["id"]
        print(f"✅ Found order: {order['name']} (ID: {order_id})")
        
        # Try to get fulfillment orders (newer API approach)
        print(f"\n📦 Getting fulfillment orders...")
        try:
            response = await client.get(
                f"{base_url}/orders/{order_id}/fulfillment_orders.json"
            )
            
            if response.status_code == 200:
                fulfillment_orders = response.json()["fulfillment_orders"]
                print(f"✅ Found {len(fulfillment_orders)} fulfillment order(s)")
                
                if fulfillment_orders:
                    fo = fulfillment_orders[0]
                    print(f"  - ID: {fo['id']}")
                    print(f"  - Status: {fo['status']}")
                    print(f"  - Location: {fo.get('assigned_location', {}).get('name', 'N/A')}")
            else:
                print(f"❌ Fulfillment orders API returned: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting fulfillment orders: {e}")
        
        # Try the newer fulfillment orders approach
        if fulfillment_orders:
            fo_id = fulfillment_orders[0]["id"]
            print(f"\n🚚 Creating fulfillment via fulfillment orders API...")
            
            # First, we need to create a fulfillment
            fulfillment_data = {
                "fulfillment": {
                    "notify_customer": False,
                    "tracking_info": {
                        "number": "TEST123456",
                        "company": "Other"
                    },
                    "line_items_by_fulfillment_order": [
                        {
                            "fulfillment_order_id": fo_id,
                            "fulfillment_order_line_items": []  # Empty = all items
                        }
                    ]
                }
            }
            
            try:
                response = await client.post(
                    f"{base_url}/fulfillments.json",
                    json=fulfillment_data
                )
                
                if response.status_code == 201:
                    fulfillment = response.json()["fulfillment"]
                    print(f"✅ Created fulfillment: {fulfillment['id']}")
                    print(f"  - Status: {fulfillment['status']}")
                    print(f"  - Tracking: {fulfillment.get('tracking_number', 'N/A')}")
                else:
                    print(f"❌ Fulfillment creation failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error creating fulfillment: {e}")
        
        # Also try the traditional method with location_id
        print(f"\n🚚 Creating fulfillment (traditional with location)...")
        
        # Get locations
        response = await client.get(f"{base_url}/locations.json")
        locations = response.json()["locations"]
        if locations:
            location_id = locations[0]["id"]
            print(f"  Using location ID: {location_id}")
            
            fulfillment_data = {
                "fulfillment": {
                    "location_id": location_id,
                    "tracking_number": "TEST789",
                    "tracking_company": "Other",
                    "notify_customer": False,
                    "line_items": []  # Empty = fulfill all
                }
            }
            
            try:
                response = await client.post(
                    f"{base_url}/orders/{order_id}/fulfillments.json",
                    json=fulfillment_data
                )
                
                if response.status_code == 201:
                    fulfillment = response.json()["fulfillment"]
                    print(f"✅ Created fulfillment: {fulfillment['id']}")
                else:
                    print(f"❌ Failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_fulfillment_api())