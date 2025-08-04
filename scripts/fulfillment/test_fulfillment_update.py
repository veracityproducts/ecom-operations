#!/usr/bin/env python3
"""Test Shopify fulfillment update for a single order."""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.shopify.client import ShopifyClient
from fulfillment.shippo.client import ShippoService, ShippoOrder, ShippoAddress, ShippoParcel
from fulfillment.utils.config import Settings


async def get_recent_unfulfilled_order():
    """Get one recent unfulfilled order."""
    settings = Settings()
    client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    # Get orders from last 2 days only
    created_at_min = (datetime.now() - timedelta(days=2)).isoformat()
    
    async with client:
        response = await client.get_orders(
            status="any",
            created_at_min=created_at_min,
            limit=50,
            fields="id,name,created_at,total_price,financial_status,fulfillment_status,shipping_address,line_items"
        )
        
        orders = response["orders"]
        # Find first unfulfilled order
        for order in orders:
            if order.get('fulfillment_status') is None:
                return order
    
    return None


async def create_test_shipment(order):
    """Create a test shipment with Shippo."""
    settings = Settings()
    
    # Initialize Shippo service
    service = ShippoService(
        api_token=settings.shippo_token,
        test_mode=settings.use_test_mode
    )
    
    # Create Shippo order
    shippo_order = ShippoOrder(
        order_number=order["name"],
        to_address=ShippoAddress(
            name=order["shipping_address"]["name"],
            street1=order["shipping_address"]["address1"],
            street2=order["shipping_address"].get("address2", ""),
            city=order["shipping_address"]["city"],
            state=order["shipping_address"]["province_code"],
            zip=order["shipping_address"]["zip"],
            country=order["shipping_address"]["country_code"],
            phone=order["shipping_address"].get("phone", "")
        ),
        from_address=ShippoAddress(
            name=settings.warehouse_ca_address["name"],
            street1=settings.warehouse_ca_address["street1"],
            street2=settings.warehouse_ca_address.get("street2", ""),
            city=settings.warehouse_ca_address["city"],
            state=settings.warehouse_ca_address["state"],
            zip=settings.warehouse_ca_address["zip"],
            country=settings.warehouse_ca_address["country"],
            phone=settings.warehouse_ca_address.get("phone", "")
        ),
        line_items=[
            {
                "title": item["name"],
                "quantity": item["quantity"],
                "sku": item.get("sku", ""),
                "total_price": item["price"],
                "weight": item.get("grams", 1000) / 1000.0,  # Convert grams to kg
                "weight_unit": "kg"
            }
            for item in order.get("line_items", [])
        ],
        placed_at=datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
    )
    
    # Create parcel
    parcel = ShippoParcel(
        length=10,
        width=8,
        height=4,
        weight=2
    )
    
    # Create shipment with label (skip order/packing slip for now)
    try:
        # Just create the label
        result = await service.get_rates_and_create_label(
            from_address=shippo_order.from_address,
            to_address=shippo_order.to_address,
            parcel=parcel,
            preferred_carrier=None  # Let it choose cheapest
        )
        
        print(f"✅ Created shipment with label")
        print(f"🏷️  Label URL: {result.label_url}")
        print(f"📮 Tracking Number: {result.tracking_number}")
        
        # Get rate details if available
        if hasattr(result, 'rate_details'):
            print(f"💰 Cost: ${float(result.rate_details['amount']):.2f}")
            print(f"🚚 Carrier: {result.rate_details['provider']}")
            carrier = result.rate_details['provider']
        else:
            print(f"💰 Cost: N/A (test mode)")
            print(f"🚚 Carrier: N/A (test mode)")
            carrier = "Other"
        
        return {
            "label": {
                "url": result.label_url,
                "tracking_number": result.tracking_number,
                "carrier": carrier
            },
            "packing_slip": {
                "url": "Generated separately"  # We'll handle this differently
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating shipment: {e}")
        return None


async def update_shopify_fulfillment(order_id, tracking_number, tracking_company, tracking_url=None):
    """Update Shopify order with fulfillment information."""
    settings = Settings()
    client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    # Prepare fulfillment data
    fulfillment_data = {
        "line_items": [],  # Empty means fulfill all items
        "tracking_number": tracking_number,
        "tracking_company": tracking_company,
        "notify_customer": False,  # Don't notify during testing
        "location_id": None  # Will use default location
    }
    
    if tracking_url:
        fulfillment_data["tracking_urls"] = [tracking_url]
    
    async with client:
        try:
            fulfillment = await client.update_order_fulfillment(order_id, fulfillment_data)
            print(f"✅ Updated Shopify fulfillment: {fulfillment['id']}")
            return fulfillment
        except Exception as e:
            print(f"❌ Error updating fulfillment: {e}")
            return None


async def main():
    """Main test function."""
    print("🔍 Finding recent unfulfilled order...")
    
    order = await get_recent_unfulfilled_order()
    if not order:
        print("❌ No unfulfilled orders found in last 2 days")
        return
    
    print(f"\n📦 Found unfulfilled order:")
    print(f"  Order: {order['name']}")
    print(f"  Created: {order['created_at'][:10]}")
    print(f"  Total: ${order['total_price']}")
    print(f"  Items: {len(order.get('line_items', []))}")
    
    # Show line items
    for item in order.get('line_items', []):
        print(f"    - {item['name']} x{item['quantity']} @ ${item['price']}")
    
    # Create shipment
    print(f"\n🚚 Creating test shipment...")
    label = await create_test_shipment(order)
    
    if not label:
        print("❌ Failed to create shipment")
        return
    
    # Extract tracking info
    tracking_number = label["label"]["tracking_number"]
    tracking_url = ""  # Shippo doesn't provide tracking URL in test mode
    carrier = label["label"]["carrier"]
    
    # Map Shippo carrier to Shopify format
    carrier_mapping = {
        "usps": "USPS",
        "ups": "UPS",
        "fedex": "FedEx",
        "dhl_express": "DHL Express",
    }
    tracking_company = carrier_mapping.get(carrier.lower(), "Other")
    
    print(f"\n📮 Tracking Info:")
    print(f"  Number: {tracking_number}")
    print(f"  Carrier: {tracking_company}")
    print(f"  URL: {tracking_url}")
    
    # Update Shopify
    print(f"\n🔄 Updating Shopify order...")
    fulfillment = await update_shopify_fulfillment(
        order["id"],
        tracking_number,
        tracking_company,
        tracking_url
    )
    
    if fulfillment:
        print(f"\n✅ SUCCESS! Order {order['name']} has been fulfilled")
        print(f"  Fulfillment ID: {fulfillment['id']}")
        print(f"  Status: {fulfillment.get('status', 'N/A')}")
    else:
        print(f"\n❌ Failed to update Shopify order")


if __name__ == "__main__":
    asyncio.run(main())