#!/usr/bin/env python3
"""
Pull historical orders from Shopify for testing and migration.

This script fetches orders from Shopify and can:
- Import unfulfilled orders for processing
- Analyze historical data for cost savings
- Test the fulfillment system with real data
"""
import os
import httpx
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

SHOPIFY_SHOP_DOMAIN = os.getenv("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")


async def fetch_orders(status="any", created_at_min=None, limit=250):
    """
    Fetch orders from Shopify.
    
    Args:
        status: Order status filter (any, open, closed, cancelled)
        created_at_min: Minimum creation date (ISO 8601)
        limit: Maximum number of orders to fetch
    """
    url = f"https://{SHOPIFY_SHOP_DOMAIN}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/orders.json"
    
    params = {
        "status": status,
        "limit": min(limit, 250),  # Shopify max is 250 per page
        "fields": "id,order_number,created_at,total_price,financial_status,fulfillment_status,shipping_address,line_items,customer"
    }
    
    if created_at_min:
        params["created_at_min"] = created_at_min
    
    orders = []
    
    async with httpx.AsyncClient() as client:
        while url and len(orders) < limit:
            response = await client.get(
                url,
                headers={"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN},
                params=params if url.endswith("/orders.json") else None
            )
            
            if response.status_code != 200:
                print(f"❌ Error fetching orders: {response.status_code}")
                print(response.text)
                break
                
            data = response.json()
            orders.extend(data.get("orders", []))
            
            # Check for pagination
            link_header = response.headers.get("Link", "")
            if 'rel="next"' in link_header:
                # Extract next URL from Link header
                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        url = link.split(";")[0].strip("<>")
                        break
                else:
                    url = None
            else:
                url = None
                
    return orders


async def analyze_orders(orders):
    """Analyze orders for fulfillment insights."""
    total_orders = len(orders)
    unfulfilled = [o for o in orders if not o.get("fulfillment_status")]
    fulfilled = [o for o in orders if o.get("fulfillment_status") == "fulfilled"]
    
    # Calculate potential savings
    # Assuming average shipping cost of $8 vs Shippo's $5.50
    potential_savings = len(fulfilled) * 2.50
    
    print(f"\n📊 Order Analysis")
    print(f"{'='*50}")
    print(f"Total orders: {total_orders}")
    print(f"Fulfilled: {len(fulfilled)}")
    print(f"Unfulfilled: {len(unfulfilled)}")
    print(f"Potential savings on fulfilled orders: ${potential_savings:,.2f}")
    
    # Show recent unfulfilled orders
    if unfulfilled:
        print(f"\n📦 Recent Unfulfilled Orders:")
        for order in unfulfilled[:10]:
            created = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
            days_old = (datetime.now(created.tzinfo) - created).days
            print(f"   - Order #{order['order_number']} - ${order['total_price']} - {days_old} days old")
    
    return unfulfilled


async def save_orders(orders, directory="data/shopify_orders"):
    """Save orders to JSON files."""
    output_dir = project_root / directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for order in orders:
        order_file = output_dir / f"shopify_order_{order['id']}.json"
        with open(order_file, "w") as f:
            json.dump(order, f, indent=2)
    
    print(f"\n💾 Saved {len(orders)} orders to {output_dir}")


async def send_to_fulfillment(orders, base_url="http://localhost:8750"):
    """Send orders to the fulfillment system for processing."""
    print(f"\n🚀 Sending {len(orders)} orders to fulfillment system...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check if server is running
        try:
            health = await client.get(f"{base_url}/health")
            if health.status_code != 200:
                print("❌ Fulfillment server not healthy")
                return
        except:
            print("❌ Could not connect to fulfillment server")
            print(f"   Make sure it's running on {base_url}")
            return
        
        # Send orders
        success = 0
        for order in orders:
            try:
                response = await client.post(
                    f"{base_url}/webhooks/shopify/order-create",
                    json=order
                )
                if response.status_code == 200:
                    success += 1
                    print(f"   ✅ Order #{order['order_number']} sent")
                else:
                    print(f"   ❌ Order #{order['order_number']} failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Order #{order['order_number']} error: {e}")
                
        print(f"\n✅ Successfully sent {success}/{len(orders)} orders")


async def main():
    """Main flow for pulling Shopify orders."""
    print("🛍️  Shopify Order Import Tool")
    print("="*50)
    
    if not SHOPIFY_SHOP_DOMAIN or not SHOPIFY_ACCESS_TOKEN:
        print("❌ Missing Shopify configuration in .env")
        return
    
    # Menu
    print("\nWhat would you like to do?")
    print("1. Analyze all recent orders")
    print("2. Import unfulfilled orders")
    print("3. Import orders from last N days")
    print("4. Import specific date range")
    
    choice = input("\nEnter choice (1-4): ")
    
    if choice == "1":
        # Analyze recent orders
        days = int(input("How many days back? (default 30): ") or "30")
        created_at_min = (datetime.now() - timedelta(days=days)).isoformat()
        
        print(f"\n📥 Fetching orders from last {days} days...")
        orders = await fetch_orders(created_at_min=created_at_min)
        await analyze_orders(orders)
        
        save = input("\nSave orders to disk? (y/n): ").lower() == 'y'
        if save:
            await save_orders(orders)
            
    elif choice == "2":
        # Import unfulfilled orders
        print("\n📥 Fetching unfulfilled orders...")
        orders = await fetch_orders(status="open")
        unfulfilled = await analyze_orders(orders)
        
        if unfulfilled:
            process = input(f"\nProcess {len(unfulfilled)} unfulfilled orders? (y/n): ").lower() == 'y'
            if process:
                await send_to_fulfillment(unfulfilled)
                
    elif choice == "3":
        # Import last N days
        days = int(input("How many days back? (default 7): ") or "7")
        created_at_min = (datetime.now() - timedelta(days=days)).isoformat()
        
        print(f"\n📥 Fetching orders from last {days} days...")
        orders = await fetch_orders(created_at_min=created_at_min)
        print(f"Found {len(orders)} orders")
        
        process = input(f"\nProcess these orders? (y/n): ").lower() == 'y'
        if process:
            await send_to_fulfillment(orders)
            
    elif choice == "4":
        # Custom date range
        start = input("Start date (YYYY-MM-DD): ")
        end = input("End date (YYYY-MM-DD, optional): ")
        
        created_at_min = f"{start}T00:00:00Z"
        print(f"\n📥 Fetching orders from {start}...")
        orders = await fetch_orders(created_at_min=created_at_min)
        
        # Filter by end date if provided
        if end:
            end_date = datetime.fromisoformat(f"{end}T23:59:59+00:00")
            orders = [o for o in orders if datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) <= end_date]
            
        print(f"Found {len(orders)} orders")
        
        process = input(f"\nProcess these orders? (y/n): ").lower() == 'y'
        if process:
            await send_to_fulfillment(orders)


if __name__ == "__main__":
    asyncio.run(main())