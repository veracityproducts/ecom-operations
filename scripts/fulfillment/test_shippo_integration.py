#!/usr/bin/env python3
"""Test Shippo integration directly."""
import asyncio
import sys
from pathlib import Path

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fulfillment.shippo.client import ShippoClient, ShippoAddress
from fulfillment.utils.config import settings


async def test_shippo_connection():
    """Test basic Shippo API connection."""
    print("🚀 Testing Shippo Integration")
    print(f"Using {'TEST' if settings.use_test_mode else 'PRODUCTION'} mode")
    print(f"Shop domain: {settings.shopify_shop_domain}")
    
    # Initialize client  
    async with ShippoClient(settings.shippo_token) as client:
        print("\n📦 Testing with a simple order...")
        
        # Create a test order
        from datetime import datetime
        from fulfillment.shippo.client import ShippoOrder
        
        test_order = ShippoOrder(
            order_number="TEST-001",
            placed_at=datetime.now(),
            to_address=ShippoAddress(
                name="Test Customer",
                street1="123 Main St",
                city="Los Angeles", 
                state="CA",
                zip="90210",
                country="US"
            ),
            from_address=ShippoAddress(
                name=settings.warehouse_ca_name,
                street1=settings.warehouse_ca_address1,
                city=settings.warehouse_ca_city,
                state=settings.warehouse_ca_state,
                zip=settings.warehouse_ca_zip,
                country="US"
            ),
            line_items=[{
                "title": "Test Product",
                "quantity": 1,
                "weight": "1.0"
            }]
        )
        
        try:
            # Test creating an order
            result = await client.create_order(test_order)
            print(f"✅ Order created: {result['object_id']}")
            print(f"   Status: {result['order_status']}")
            
            print("\n✨ Shippo integration test successful!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(test_shippo_connection())