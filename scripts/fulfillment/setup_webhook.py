#!/usr/bin/env python3
"""
Set up Shopify webhook for order creation.

This script registers a webhook with Shopify to notify our fulfillment system
when new orders are created.
"""
import os
import httpx
import asyncio
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

SHOPIFY_SHOP_DOMAIN = os.getenv("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhooks/shopify/order-create")


async def list_webhooks():
    """List existing webhooks."""
    url = f"https://{SHOPIFY_SHOP_DOMAIN}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/webhooks.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
        )
        
        if response.status_code == 200:
            webhooks = response.json()["webhooks"]
            return webhooks
        else:
            print(f"❌ Error listing webhooks: {response.status_code}")
            print(response.text)
            return []


async def create_webhook():
    """Create order creation webhook."""
    url = f"https://{SHOPIFY_SHOP_DOMAIN}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/webhooks.json"
    
    webhook_data = {
        "webhook": {
            "topic": "orders/create",
            "address": WEBHOOK_URL,
            "format": "json"
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN},
            json=webhook_data
        )
        
        if response.status_code == 201:
            webhook = response.json()["webhook"]
            return webhook
        else:
            print(f"❌ Error creating webhook: {response.status_code}")
            print(response.text)
            return None


async def delete_webhook(webhook_id):
    """Delete a webhook."""
    url = f"https://{SHOPIFY_SHOP_DOMAIN}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/webhooks/{webhook_id}.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers={"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
        )
        
        return response.status_code == 200


async def main():
    """Main setup flow."""
    print("🛍️  Shopify Webhook Setup")
    print(f"Shop: {SHOPIFY_SHOP_DOMAIN}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()
    
    # Check configuration
    if not SHOPIFY_SHOP_DOMAIN or not SHOPIFY_ACCESS_TOKEN:
        print("❌ Missing Shopify configuration in .env")
        print("   Required: SHOPIFY_SHOP_DOMAIN, SHOPIFY_ACCESS_TOKEN")
        return
        
    if WEBHOOK_URL == "https://your-domain.com/webhooks/shopify/order-create":
        print("⚠️  Using default webhook URL - for testing only!")
        print("   For production, set WEBHOOK_URL in .env")
        print()
        
        # For local testing with ngrok
        print("📝 For local testing, you can use ngrok:")
        print("   1. Start the fulfillment server: ./run_fulfillment.sh")
        print("   2. In another terminal: ngrok http 8000")
        print("   3. Set WEBHOOK_URL=https://YOUR-NGROK-ID.ngrok.io/webhooks/shopify/order-create")
        print()
        
        use_local = input("Use localhost URL for testing? (y/n): ").lower() == 'y'
        if use_local:
            WEBHOOK_URL = "http://localhost:8000/webhooks/shopify/order-create"
            print(f"   Using: {WEBHOOK_URL}")
    
    # List existing webhooks
    print("\n📋 Checking existing webhooks...")
    webhooks = await list_webhooks()
    
    if webhooks:
        print(f"Found {len(webhooks)} webhook(s):")
        for webhook in webhooks:
            print(f"   - {webhook['topic']}: {webhook['address']}")
            print(f"     ID: {webhook['id']}")
            
        # Check if our webhook already exists
        order_webhooks = [w for w in webhooks if w['topic'] == 'orders/create']
        if order_webhooks:
            print("\n⚠️  Order creation webhook already exists!")
            replace = input("Replace existing webhook? (y/n): ").lower() == 'y'
            if replace:
                for webhook in order_webhooks:
                    await delete_webhook(webhook['id'])
                    print(f"   ✅ Deleted webhook {webhook['id']}")
            else:
                print("   Keeping existing webhook")
                return
    else:
        print("   No existing webhooks found")
    
    # Create new webhook
    print(f"\n🔧 Creating order webhook...")
    webhook = await create_webhook()
    
    if webhook:
        print(f"✅ Webhook created successfully!")
        print(f"   ID: {webhook['id']}")
        print(f"   Topic: {webhook['topic']}")
        print(f"   URL: {webhook['address']}")
        print()
        print("🎯 Next steps:")
        print("   1. Make sure your fulfillment server is running")
        print("   2. Create a test order in Shopify")
        print("   3. Check the data/orders/ directory for the webhook data")
    else:
        print("❌ Failed to create webhook")


if __name__ == "__main__":
    asyncio.run(main())