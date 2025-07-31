#!/usr/bin/env python3
"""Set up Shopify webhooks for the fulfillment system."""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fulfillment_system.integrations.shopify import get_shopify_service
from fulfillment_system.utils.config import settings


async def setup_webhooks():
    """Set up all required Shopify webhooks."""
    
    # Check if Shopify is configured
    if not settings.shopify.access_token or settings.shopify.access_token == "your_shopify_access_token_here":
        print("❌ Error: Shopify not configured!")
        print("\nPlease set these environment variables in your .env file:")
        print("  SHOPIFY_SHOP_DOMAIN=your-shop-name")
        print("  SHOPIFY_ACCESS_TOKEN=your_access_token")
        print("  SHOPIFY_WEBHOOK_SECRET=your_webhook_secret")
        print("\nTo create a custom app in Shopify:")
        print("1. Go to Settings → Apps and sales channels")
        print("2. Click 'Develop apps for your store'")
        print("3. Create an app with these scopes:")
        print("   - read_orders")
        print("   - write_orders")
        print("   - read_products")
        print("   - read_inventory")
        print("   - read_customers")
        print("   - write_fulfillments")
        print("4. Install the app and get the access token")
        return
    
    # Get webhook base URL
    webhook_base_url = input("\nEnter your webhook base URL (e.g., https://your-domain.com): ").strip()
    
    if not webhook_base_url.startswith("https://"):
        print("❌ Error: Webhook URL must use HTTPS!")
        return
    
    print(f"\n🚀 Setting up Shopify webhooks...")
    print(f"   Shop: {settings.shopify.shop_domain}")
    print(f"   Webhook Base: {webhook_base_url}")
    
    # Set up webhooks
    shopify_service = get_shopify_service()
    
    try:
        webhook_ids = await shopify_service.setup_webhooks(webhook_base_url)
        
        print("\n✅ Successfully set up webhooks:")
        for topic, webhook_id in webhook_ids.items():
            print(f"   {topic}: {webhook_id}")
        
        print(f"\n📝 Webhook endpoints configured:")
        print(f"   - {webhook_base_url}/webhooks/shopify/orders-create")
        print(f"   - {webhook_base_url}/webhooks/shopify/orders-updated")
        print(f"   - {webhook_base_url}/webhooks/shopify/orders-cancelled")
        print(f"   - {webhook_base_url}/webhooks/shopify/orders-fulfilled")
        print(f"   - {webhook_base_url}/webhooks/shopify/orders-paid")
        
        print("\n💡 Next steps:")
        print("1. Make sure your webhook endpoints are accessible from the internet")
        print("2. Start your FastAPI server to receive webhooks")
        print("3. Create a test order in Shopify to verify the integration")
        
    except Exception as e:
        print(f"\n❌ Error setting up webhooks: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your access token has the correct permissions")
        print("2. Check that your shop domain is correct")
        print("3. Ensure your app is installed on the store")


async def list_webhooks():
    """List all configured webhooks."""
    shopify_service = get_shopify_service()
    
    async with shopify_service.api_client as client:
        webhooks = await client.list_webhooks()
        
        if webhooks:
            print("\n📋 Configured webhooks:")
            for webhook in webhooks:
                print(f"\n   Topic: {webhook['topic']}")
                print(f"   URL: {webhook['address']}")
                print(f"   ID: {webhook['id']}")
                print(f"   Created: {webhook['created_at']}")
        else:
            print("\n📋 No webhooks configured")


async def main():
    """Main entry point."""
    print("🛍️  Grooved Learning Fulfillment System")
    print("    Shopify Webhook Setup")
    print("=" * 50)
    
    action = input("\nWhat would you like to do?\n1. Set up webhooks\n2. List existing webhooks\n\nChoice (1 or 2): ").strip()
    
    if action == "1":
        await setup_webhooks()
    elif action == "2":
        await list_webhooks()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    asyncio.run(main())