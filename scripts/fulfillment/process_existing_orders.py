#!/usr/bin/env python3
"""
Process existing unfulfilled orders from JSON file.
"""
import asyncio
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FULFILLMENT_API_URL = os.getenv("FULFILLMENT_API_URL", "http://localhost:8750")


async def process_order(order_data):
    """Send order to fulfillment API."""
    async with httpx.AsyncClient() as client:
        try:
            # Simulate webhook payload
            webhook_payload = {
                "id": order_data["id"],
                "email": order_data["email"],
                "created_at": order_data["created_at"],
                "currency": order_data["currency"],
                "total_price": order_data["total_price"],
                "subtotal_price": order_data["subtotal_price"],
                "total_tax": order_data["total_tax"],
                "financial_status": order_data["financial_status"],
                "fulfillment_status": order_data["fulfillment_status"],
                "name": order_data["name"],
                "order_number": order_data["order_number"],
                "line_items": order_data["line_items"],
                "shipping_address": order_data["shipping_address"],
                "customer": order_data["customer"],
                "shipping_lines": order_data["shipping_lines"]
            }
            
            response = await client.post(
                f"{FULFILLMENT_API_URL}/webhook/order/created",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Processed order {order_data['name']} - {response.json()}")
            else:
                print(f"❌ Failed to process order {order_data['name']}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error processing order {order_data['name']}: {e}")


async def main():
    """Process unfulfilled orders from file."""
    # Load orders from file (relative to project root)
    project_root = Path(__file__).parent.parent.parent
    orders_file = project_root / "unfulfilled_orders_20250801_022951.json"
    
    if not orders_file.exists():
        print(f"❌ Orders file not found: {orders_file}")
        return
    
    with open(orders_file) as f:
        orders = json.load(f)
    
    print(f"📦 Found {len(orders)} orders to process")
    
    # Filter only truly unfulfilled orders
    unfulfilled = []
    for order in orders:
        if order.get("fulfillment_status") in [None, "null", ""]:
            # Check if all line items need fulfillment
            needs_fulfillment = False
            for item in order.get("line_items", []):
                if item.get("fulfillable_quantity", 0) > 0:
                    needs_fulfillment = True
                    break
            
            if needs_fulfillment:
                unfulfilled.append(order)
                print(f"  - Order {order['name']} ({order['order_number']}): ${order['total_price']} - {len(order['line_items'])} items")
    
    print(f"\n🎯 {len(unfulfilled)} orders need fulfillment")
    
    if unfulfilled:
        print("\n🚀 Starting fulfillment server check...")
        
        # Check if server is running
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{FULFILLMENT_API_URL}/health")
                if response.status_code == 200:
                    print("✅ Fulfillment server is healthy")
                else:
                    print("❌ Fulfillment server is not responding correctly")
                    print("💡 Start the server with: ./run_fulfillment.sh")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to fulfillment server: {e}")
            print("💡 Start the server with: ./run_fulfillment.sh")
            return
        
        # Process orders
        print("\n📤 Sending orders to fulfillment system...")
        for order in unfulfilled:
            await process_order(order)
            await asyncio.sleep(1)  # Rate limiting
    
    print("\n✨ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())