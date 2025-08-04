#!/usr/bin/env python3
"""Verify Shippo API configuration and test mode switching."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx
import asyncio

# Load environment
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


async def test_shippo_token(token: str, is_test: bool = True) -> bool:
    """Test if a Shippo API token is valid."""
    headers = {
        "Authorization": f"ShippoToken {token}",
        "Content-Type": "application/json"
    }
    
    mode_label = "TEST" if is_test else "LIVE"
    print(f"\n🔍 Testing {mode_label} token...")
    print(f"   Token preview: {token[:15]}...{token[-5:]}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test with carrier accounts endpoint
            response = await client.get(
                "https://api.goshippo.com/carrier_accounts",
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"   ✅ {mode_label} token is valid!")
                data = response.json()
                print(f"   Found {len(data.get('results', []))} carrier accounts")
                return True
            else:
                print(f"   ❌ {mode_label} token failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing {mode_label} token: {e}")
            return False


def verify_shippo_config():
    """Verify Shippo configuration for production readiness."""
    print("📦 Shippo API Configuration Check")
    print("=" * 50)
    
    # Get tokens
    test_token = os.getenv("SHIPPING_SHIPPO_TEST_API_TOKEN", "")
    live_token = os.getenv("SHIPPING_SHIPPO_API_TOKEN", "")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Check tokens exist
    has_test = bool(test_token)
    has_live = bool(live_token)
    
    print("🔑 Token Configuration:")
    if has_test:
        print("✅ SHIPPING_SHIPPO_TEST_API_TOKEN is configured")
    else:
        print("❌ SHIPPING_SHIPPO_TEST_API_TOKEN is not set!")
    
    if has_live:
        print("✅ SHIPPING_SHIPPO_API_TOKEN is configured")
    else:
        print("❌ SHIPPING_SHIPPO_API_TOKEN is not set!")
    
    # Check environment
    print(f"\n📍 Environment: {environment}")
    is_production = environment == "production"
    
    if is_production:
        print("   🚀 Production mode - will use LIVE token")
        active_token = live_token
        is_test_mode = False
    else:
        print("   🧪 Development mode - will use TEST token")
        active_token = test_token
        is_test_mode = True
    
    # Additional configuration
    print("\n⚙️  Additional Configuration:")
    base_url = os.getenv("SHIPPING_SHIPPO_BASE_URL", "https://api.goshippo.com")
    rate_limit = os.getenv("SHIPPING_SHIPPO_RATE_LIMIT_TIER", "standard")
    carrier = os.getenv("SHIPPING_SHIPPO_PREFERRED_CARRIER", "")
    
    print(f"   Base URL: {base_url}")
    print(f"   Rate Limit Tier: {rate_limit}")
    print(f"   Preferred Carrier: {carrier or 'None (will use cheapest)'}")
    
    return {
        "has_test": has_test,
        "has_live": has_live,
        "environment": environment,
        "is_production": is_production,
        "active_token": active_token,
        "is_test_mode": is_test_mode,
        "test_token": test_token,
        "live_token": live_token
    }


async def main():
    """Main verification process."""
    config = verify_shippo_config()
    
    # Check for --test-live flag
    test_live = "--test-live" in sys.argv
    
    # Test tokens if available
    if config["has_test"]:
        test_valid = await test_shippo_token(config["test_token"], is_test=True)
    else:
        test_valid = False
        print("\n⚠️  Cannot test TEST token - not configured")
    
    if config["has_live"]:
        if test_live:
            print("\n🔍 Testing LIVE token (--test-live flag provided)...")
            live_valid = await test_shippo_token(config["live_token"], is_test=False)
        else:
            live_valid = None
            print("\n✋ Live token detected but not tested")
            print("   To test live token, run with --test-live flag")
    else:
        live_valid = False
        print("\n⚠️  Cannot test LIVE token - not configured")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Configuration Summary:")
    print(f"   Environment: {config['environment']}")
    print(f"   Active Mode: {'LIVE' if config['is_production'] else 'TEST'}")
    print(f"   Test Token: {'✅ Valid' if test_valid else '❌ Invalid/Missing'}")
    print(f"   Live Token: {'✅ Valid' if live_valid else '❓ Not Tested' if live_valid is None else '❌ Invalid/Missing'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not config["has_live"] and config["is_production"]:
        print("   🚨 CRITICAL: Production mode but no LIVE token configured!")
    elif config["is_production"] and not live_valid and live_valid is not None:
        print("   🚨 CRITICAL: Production LIVE token is invalid!")
    elif not config["is_production"] and not test_valid:
        print("   ⚠️  WARNING: Test token is invalid or missing")
    else:
        print("   ✅ Configuration looks good for current environment")
    
    # Mode switching instructions
    print("\n🔄 To switch between TEST and PRODUCTION modes:")
    print("   1. Set ENVIRONMENT=production in .env for live mode")
    print("   2. Set ENVIRONMENT=development in .env for test mode")
    print("   3. Restart the fulfillment service")
    
    # Label cost info
    print("\n💰 Shippo Label Costs:")
    print("   Test Mode: $0.00 (free test labels)")
    print("   Live Mode: $0.05 per label (includes packing slip)")
    
    is_ready = (config["is_production"] and live_valid) or (not config["is_production"] and test_valid)
    
    if is_ready:
        print("\n✅ Shippo configuration is ready for current environment!")
    else:
        print("\n❌ Shippo configuration needs attention")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())