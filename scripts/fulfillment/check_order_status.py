#!/usr/bin/env python3
"""Check order fulfillment status."""
import asyncio
import sys
from pathlib import Path

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.shopify.client import ShopifyClient
from fulfillment.utils.config import Settings


async def check_order_status(order_name: str):
    """Check order fulfillment status."""
    settings = Settings()
    client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    async with client:
        # Search for order by name
        response = await client.get_orders(
            name=order_name,
            limit=1
        )
        
        orders = response["orders"]
        if not orders:
            print(f"❌ Order {order_name} not found")
            return
            
        order = orders[0]
        print(f"📦 Order: {order['name']}")
        print(f"  ID: {order['id']}")
        print(f"  Status: {order.get('fulfillment_status', 'None')}")
        print(f"  Financial: {order['financial_status']}")
        
        # Get fulfillment orders
        fulfillment_orders = await client.get_fulfillment_orders(order['id'])
        print(f"\n📋 Fulfillment Orders: {len(fulfillment_orders)}")
        for fo in fulfillment_orders:
            print(f"  - ID: {fo['id']}")
            print(f"    Status: {fo['status']}")
            print(f"    Location: {fo.get('assigned_location', {}).get('name', 'N/A')}")
            print(f"    Line Items: {len(fo.get('line_items', []))}")
            
            # Check line items
            for item in fo.get('line_items', []):
                print(f"      • {item.get('sku', 'N/A')} x{item.get('quantity', 0)} (remaining: {item.get('remaining_quantity', item.get('quantity', 0))})")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        order_name = sys.argv[1]
    else:
        order_name = "#111708"
    
    await check_order_status(order_name)


if __name__ == "__main__":
    asyncio.run(main())