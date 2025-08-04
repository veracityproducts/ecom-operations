#!/usr/bin/env python3
"""Complete end-to-end fulfillment test."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.shopify.client import ShopifyClient
from fulfillment.shippo.client import ShippoService, ShippoAddress, ShippoParcel
from fulfillment.utils.config import Settings


async def main():
    """Test complete fulfillment flow."""
    settings = Settings()
    
    # Use specific order we know is unfulfilled
    order_name = "#111708"
    
    print(f"🎯 Testing fulfillment for order {order_name}")
    
    # Initialize Shopify client
    shopify_client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    async with shopify_client:
        # Get the order
        response = await shopify_client.get_orders(name=order_name, limit=1)
        orders = response["orders"]
        if not orders:
            print(f"❌ Order {order_name} not found")
            return
            
        order = orders[0]
        print(f"\n📦 Order Details:")
        print(f"  ID: {order['id']}")
        print(f"  Status: {order.get('fulfillment_status', 'unfulfilled')}")
        print(f"  Total: ${order['total_price']}")
        
        # Get fulfillment orders
        fulfillment_orders = await shopify_client.get_fulfillment_orders(order['id'])
        if not fulfillment_orders:
            print("❌ No fulfillment orders found")
            return
            
        fo = fulfillment_orders[0]
        print(f"\n📋 Fulfillment Order:")
        print(f"  ID: {fo['id']}")
        print(f"  Status: {fo['status']}")
        
        if fo['status'] != 'open':
            print(f"❌ Fulfillment order is not open (status: {fo['status']})")
            return
        
        # Create Shippo shipment
        print(f"\n🚚 Creating Shippo shipment...")
        shippo_service = ShippoService(
            api_token=settings.shippo_token,
            test_mode=settings.use_test_mode
        )
        
        # Create addresses
        from_address = ShippoAddress(
            name=settings.warehouse_ca_address["name"],
            street1=settings.warehouse_ca_address["street1"],
            city=settings.warehouse_ca_address["city"],
            state=settings.warehouse_ca_address["state"],
            zip=settings.warehouse_ca_address["zip"],
            country=settings.warehouse_ca_address["country"]
        )
        
        to_address = ShippoAddress(
            name=order["shipping_address"]["name"],
            street1=order["shipping_address"]["address1"],
            street2=order["shipping_address"].get("address2", ""),
            city=order["shipping_address"]["city"],
            state=order["shipping_address"]["province_code"],
            zip=order["shipping_address"]["zip"],
            country=order["shipping_address"]["country_code"]
        )
        
        parcel = ShippoParcel(
            length=10,
            width=8,
            height=4,
            weight=2
        )
        
        try:
            # Create label
            label_result = await shippo_service.get_rates_and_create_label(
                from_address=from_address,
                to_address=to_address,
                parcel=parcel,
                preferred_carrier=None
            )
            
            print(f"✅ Created Shippo label")
            print(f"  URL: {label_result.label_url or 'N/A (test mode)'}")
            print(f"  Tracking: {label_result.tracking_number or 'TEST123'}")
            
            # Use test tracking number if in test mode
            tracking_number = label_result.tracking_number or f"TEST{order['id']}"
            
            # Update Shopify fulfillment
            print(f"\n📮 Updating Shopify fulfillment...")
            fulfillment = await shopify_client.create_fulfillment(
                tracking_number=tracking_number,
                tracking_company="USPS",  # Default for test
                fulfillment_order_id=fo['id'],
                notify_customer=False
            )
            
            print(f"✅ SUCCESS! Created fulfillment")
            print(f"  ID: {fulfillment['id']}")
            print(f"  Status: {fulfillment['status']}")
            print(f"  Tracking: {fulfillment.get('tracking_number', 'N/A')}")
            
            # Save result
            result = {
                "order_id": order['id'],
                "order_name": order['name'],
                "fulfillment_id": fulfillment['id'],
                "tracking_number": tracking_number,
                "shippo_label_url": label_result.label_url or "N/A (test mode)",
                "created_at": datetime.now().isoformat()
            }
            
            with open('fulfillment_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\n💾 Saved result to fulfillment_result.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())