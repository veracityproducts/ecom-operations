#!/usr/bin/env python3
"""Get today's unfulfilled orders for analysis."""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.shopify.client import ShopifyClient
from fulfillment.utils.config import Settings


async def main():
    """Get today's unfulfilled orders."""
    settings = Settings()
    client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    # Get orders from last 24 hours
    created_at_min = (datetime.now() - timedelta(days=1)).isoformat()
    
    async with client:
        response = await client.get_orders(
            status="any",
            created_at_min=created_at_min,
            fulfillment_status="unfulfilled",
            limit=250
        )
        
        orders = response["orders"]
        
    print(f"Found {len(orders)} unfulfilled orders from the last 24 hours")
    
    # Show sample of products
    print("\nProduct Summary:")
    product_counts = {}
    for order in orders:
        for item in order.get("line_items", []):
            sku = item.get("sku", "NO_SKU")
            name = item.get("name", "Unknown")
            key = f"{sku} - {name}"
            product_counts[key] = product_counts.get(key, 0) + 1
    
    # Sort by count
    sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTop Products in Unfulfilled Orders:")
    for product, count in sorted_products[:10]:
        print(f"  {count}x {product}")
    
    # Save to file
    output_file = f"unfulfilled_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(orders, f, indent=2)
    
    print(f"\n💾 Saved {len(orders)} orders to {output_file}")
    
    # Show a few standard product orders
    print("\nSample Orders with Standard Products:")
    standard_skus = ["CB-BOOK-SET", "SOUND-CARDS", "HW-WORKBOOK"]
    shown = 0
    for order in orders:
        for item in order.get("line_items", []):
            if any(sku in item.get("sku", "") for sku in standard_skus) and shown < 5:
                print(f"\nOrder: {order['name']} (ID: {order['id']})")
                print(f"  Product: {item['name']}")
                print(f"  SKU: {item.get('sku', 'N/A')}")
                print(f"  Ship to: {order['shipping_address']['city']}, {order['shipping_address']['province_code']}")
                shown += 1
                break


if __name__ == "__main__":
    asyncio.run(main())