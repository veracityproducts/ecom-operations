#!/usr/bin/env python3
"""Non-interactive version of order sync for testing."""
import asyncio
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.shopify.client import ShopifyClient
from fulfillment.utils.config import Settings


async def fetch_orders(status="any", created_at_min=None, limit=250):
    """Fetch orders from Shopify."""
    settings = Settings()
    client = ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version
    )
    
    orders = []
    params = {
        "status": status,
        "limit": limit,
        "fields": "id,name,created_at,updated_at,total_price,financial_status,fulfillment_status,shipping_address,line_items"
    }
    
    if created_at_min:
        params["created_at_min"] = created_at_min
    
    print(f"Fetching orders with params: {params}")
    
    async with client:
        has_next = True
        while has_next:
            try:
                response = await client.get_orders(**params)
                
                if "orders" in response:
                    batch = response["orders"]
                    orders.extend(batch)
                    print(f"Fetched {len(batch)} orders (total: {len(orders)})")
                    
                    # Check for pagination
                    if "link" in response.get("headers", {}):
                        # Parse Link header for next page
                        link_header = response["headers"]["link"]
                        if 'rel="next"' in link_header:
                            # Extract page_info from link
                            import re
                            match = re.search(r'page_info=([^&>]+)', link_header)
                            if match:
                                params = {"page_info": match.group(1), "limit": limit}
                            else:
                                has_next = False
                        else:
                            has_next = False
                    else:
                        has_next = False
                else:
                    print(f"Unexpected response: {response}")
                    has_next = False
                    
            except Exception as e:
                print(f"Error fetching orders: {e}")
                has_next = False
    
    return orders


async def analyze_orders(days_back=30):
    """Analyze recent orders."""
    created_at_min = (datetime.now() - timedelta(days=days_back)).isoformat()
    orders = await fetch_orders(created_at_min=created_at_min)
    
    print(f"\n📊 Order Analysis (Last {days_back} Days)")
    print("=" * 50)
    print(f"Total orders: {len(orders)}")
    
    # Fulfillment status breakdown
    fulfilled = sum(1 for o in orders if o.get('fulfillment_status') == 'fulfilled')
    partial = sum(1 for o in orders if o.get('fulfillment_status') == 'partial')
    unfulfilled = sum(1 for o in orders if o.get('fulfillment_status') is None)
    
    print(f"\nFulfillment Status:")
    print(f"  Fulfilled: {fulfilled}")
    print(f"  Partial: {partial}")
    print(f"  Unfulfilled: {unfulfilled}")
    
    # Financial status breakdown
    paid = sum(1 for o in orders if o.get('financial_status') == 'paid')
    pending = sum(1 for o in orders if o.get('financial_status') == 'pending')
    
    print(f"\nFinancial Status:")
    print(f"  Paid: {paid}")
    print(f"  Pending: {pending}")
    
    # Show sample orders
    if orders:
        print(f"\nSample Orders:")
        for order in orders[:5]:
            print(f"  {order['name']} - Created: {order['created_at'][:10]} - Status: {order.get('fulfillment_status', 'unfulfilled')}")
    
    return orders


async def fetch_unfulfilled_orders():
    """Get all unfulfilled orders."""
    # Only fetch orders from last 30 days to avoid timeout
    created_at_min = (datetime.now() - timedelta(days=30)).isoformat()
    orders = await fetch_orders(status="any", created_at_min=created_at_min)
    unfulfilled = [o for o in orders if o.get('fulfillment_status') is None]
    
    print(f"\n📦 Unfulfilled Orders")
    print("=" * 50)
    print(f"Found {len(unfulfilled)} unfulfilled orders")
    
    for order in unfulfilled[:10]:  # Show first 10
        print(f"\nOrder: {order['name']}")
        print(f"  Created: {order['created_at'][:10]}")
        print(f"  Total: ${order['total_price']}")
        print(f"  Items: {len(order.get('line_items', []))}")
    
    return unfulfilled


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Shopify Order Sync Tool")
    parser.add_argument("--mode", choices=["analyze", "unfulfilled", "sync"], default="analyze",
                        help="Operation mode")
    parser.add_argument("--days", type=int, default=30,
                        help="Number of days to look back (for analyze mode)")
    parser.add_argument("--save", action="store_true",
                        help="Save orders to JSON file")
    
    args = parser.parse_args()
    
    if args.mode == "analyze":
        orders = await analyze_orders(args.days)
    elif args.mode == "unfulfilled":
        orders = await fetch_unfulfilled_orders()
    elif args.mode == "sync":
        # For now, just fetch recent orders
        created_at_min = (datetime.now() - timedelta(days=args.days)).isoformat()
        orders = await fetch_orders(created_at_min=created_at_min)
        print(f"Fetched {len(orders)} orders from last {args.days} days")
    
    if args.save and orders:
        output_file = f"orders_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(orders, f, indent=2)
        print(f"\n💾 Saved {len(orders)} orders to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())