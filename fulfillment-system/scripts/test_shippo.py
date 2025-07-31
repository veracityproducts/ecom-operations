#!/usr/bin/env python3
"""Test script for Shippo API integration."""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fulfillment_system.integrations.shippo import (
    ShippoService,
    ShippoOrder,
    ShippoAddress,
    ShippoParcel
)
from fulfillment_system.utils.config import settings


async def test_shippo_integration():
    """Test basic Shippo functionality."""
    
    # Get API token from settings
    api_token = settings.shipping.shippo_test_api_token or settings.shipping.shippo_api_token
    
    if not api_token or api_token == "shippo_test_your_test_token_here":
        print("❌ Error: Please set SHIPPING_SHIPPO_TEST_API_TOKEN in your .env file")
        print("   You can get a test token from: https://goshippo.com/register")
        return
    
    print("🚀 Testing Shippo Integration...")
    print(f"   Using API token: {api_token[:10]}...")
    
    # Initialize service
    shippo_service = ShippoService(
        api_token=api_token,
        rate_limit_tier=settings.shipping.shippo_rate_limit_tier
    )
    
    # Create test order
    customer_order = ShippoOrder(
        order_number=f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        to_address=ShippoAddress(
            name="Test Customer",
            street1="123 Main St",
            city="Los Angeles",
            state="CA",
            zip="90210",
            phone="555-123-4567",
            email="test@example.com"
        ),
        from_address=ShippoAddress(
            name=settings.warehouse.ca_name,
            street1=settings.warehouse.ca_address1,
            city=settings.warehouse.ca_city,
            state=settings.warehouse.ca_state,
            zip=settings.warehouse.ca_postal_code,
            phone=settings.warehouse.ca_phone or "555-000-0000",
            email="shipping@groovedlearning.com"
        ),
        line_items=[
            {
                "title": "Code Breakers Books Set (TEST)",
                "quantity": 1,
                "sku": "CB-BOOKS-K6-TEST",
                "weight": "2.5",
                "weight_unit": "lb"
            }
        ],
        placed_at=datetime.now()
    )
    
    # Package details
    package = ShippoParcel(
        length=12.0,
        width=9.0,
        height=3.0,
        weight=2.5
    )
    
    try:
        print("\n📦 Creating test order and generating label...")
        
        # Generate combined label and packing slip
        result = await shippo_service.create_combined_label_and_packing_slip(
            order=customer_order,
            parcel=package,
            preferred_carrier=settings.shipping.shippo_preferred_carrier
        )
        
        print("\n✅ Success! Test order processed:")
        print(f"   Order ID: {result['order_id']}")
        print(f"   Tracking: {result['label']['tracking_number']}")
        print(f"   Carrier: {result['label']['carrier']}")
        print(f"   Rate: ${result['label']['rate_amount']}")
        print(f"   Total Cost: ${result['total_cost']:.2f}")
        print(f"\n📄 Documents:")
        print(f"   Label URL: {result['label']['url']}")
        print(f"   Packing Slip URL: {result['packing_slip']['url']}")
        print(f"   (URLs expire at: {result['packing_slip']['expires_at']})")
        
        print("\n✨ Shippo integration is working correctly!")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing Shippo integration: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_shippo_integration())
    
    if result:
        print("\n💡 Next steps:")
        print("   1. Download the label and packing slip PDFs from the URLs above")
        print("   2. Verify the documents look correct")
        print("   3. Note: This was a TEST label - do not use for actual shipping!")
        print("   4. Update your .env with production API token when ready")