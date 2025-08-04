#!/usr/bin/env python3
"""Verify and display webhook configuration for Shopify."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


def verify_webhook_config():
    """Verify webhook configuration is ready for production."""
    print("🔒 Shopify Webhook Configuration Check")
    print("=" * 50)
    
    # Check webhook secret
    webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    if webhook_secret:
        print("✅ SHOPIFY_WEBHOOK_SECRET is configured")
        print(f"   Length: {len(webhook_secret)} characters")
        print(f"   Preview: {webhook_secret[:5]}...{webhook_secret[-5:]}")
    else:
        print("❌ SHOPIFY_WEBHOOK_SECRET is not set!")
        print("   This is required for production webhook verification")
    
    # Check environment
    environment = os.getenv("ENVIRONMENT", "development")
    print(f"\n📍 Environment: {environment}")
    if environment == "production":
        print("   ⚠️  Production mode - webhook verification is REQUIRED")
    else:
        print("   ℹ️  Development mode - webhook verification can be skipped")
    
    # Check Shopify configuration
    print("\n🛍️  Shopify Configuration:")
    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-01")
    
    configs = [
        ("SHOPIFY_SHOP_DOMAIN", shop_domain),
        ("SHOPIFY_ACCESS_TOKEN", access_token),
        ("SHOPIFY_API_VERSION", api_version)
    ]
    
    all_configured = True
    for name, value in configs:
        if value:
            if "TOKEN" in name:
                print(f"✅ {name} is configured ({len(value)} chars)")
            else:
                print(f"✅ {name}: {value}")
        else:
            print(f"❌ {name} is not set!")
            all_configured = False
    
    # Webhook endpoint info
    print("\n🔗 Webhook Endpoint:")
    api_port = os.getenv("API_PORT", "8750")
    print(f"   Development: http://localhost:{api_port}/webhooks/shopify/order-create")
    print(f"   Production: https://your-domain.com/webhooks/shopify/order-create")
    print(f"   Test endpoint: http://localhost:{api_port}/test/order-webhook")
    
    # Instructions
    print("\n📋 Shopify Webhook Setup Instructions:")
    print("1. Go to Shopify Admin → Settings → Notifications → Webhooks")
    print("2. Create webhook for 'Order creation' event")
    print("3. Set URL to your production endpoint (with HTTPS)")
    print("4. Copy the webhook signing key")
    print("5. Set SHOPIFY_WEBHOOK_SECRET in .env to the signing key")
    
    if not webhook_secret:
        print("\n⚠️  ACTION REQUIRED: Set SHOPIFY_WEBHOOK_SECRET before production!")
    
    return all_configured and bool(webhook_secret)


if __name__ == "__main__":
    is_ready = verify_webhook_config()
    
    print("\n" + "=" * 50)
    if is_ready:
        print("✅ Webhook configuration is ready for production!")
    else:
        print("❌ Webhook configuration needs attention")
        sys.exit(1)