#!/usr/bin/env python3
"""Production deployment checklist for fulfillment system."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess

# Load environment
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


def check_requirement(name: str, condition: bool, critical: bool = True) -> bool:
    """Check a single requirement and print status."""
    status = "✅" if condition else ("❌" if critical else "⚠️")
    print(f"{status} {name}")
    if not condition and critical:
        print(f"   └─ This is required for production deployment")
    return condition


def run_command(cmd: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)


def main():
    """Run production deployment checklist."""
    print("🚀 Production Deployment Checklist")
    print("=" * 60)
    
    all_good = True
    
    # 1. Environment Configuration
    print("\n📋 Environment Configuration:")
    environment = os.getenv("ENVIRONMENT", "development")
    is_production = environment == "production"
    
    all_good &= check_requirement(
        f"Environment is set to: {environment}",
        True,  # Just informational
        critical=False
    )
    
    if not is_production:
        print("   └─ ℹ️  Currently in development mode")
        print("   └─ To deploy to production, set ENVIRONMENT=production")
    
    # 2. Shopify Configuration
    print("\n📋 Shopify Configuration:")
    shopify_checks = {
        "SHOPIFY_SHOP_DOMAIN configured": bool(os.getenv("SHOPIFY_SHOP_DOMAIN")),
        "SHOPIFY_ACCESS_TOKEN configured": bool(os.getenv("SHOPIFY_ACCESS_TOKEN")),
        "SHOPIFY_WEBHOOK_SECRET configured": bool(os.getenv("SHOPIFY_WEBHOOK_SECRET")),
        "SHOPIFY_API_VERSION configured": bool(os.getenv("SHOPIFY_API_VERSION"))
    }
    
    for check, result in shopify_checks.items():
        all_good &= check_requirement(check, result)
    
    # 3. Shippo Configuration
    print("\n📋 Shippo Configuration:")
    shippo_checks = {
        "SHIPPING_SHIPPO_API_TOKEN configured": bool(os.getenv("SHIPPING_SHIPPO_API_TOKEN")),
        "SHIPPING_SHIPPO_TEST_API_TOKEN configured": bool(os.getenv("SHIPPING_SHIPPO_TEST_API_TOKEN")),
        "Warehouse CA address configured": bool(os.getenv("WAREHOUSE_CA_ADDRESS1"))
    }
    
    for check, result in shippo_checks.items():
        all_good &= check_requirement(check, result)
    
    # 4. Code Quality
    print("\n📋 Code Quality Checks:")
    
    # Check if server can start
    server_check, _ = run_command("timeout 3 uv run fulfillment/main.py > /dev/null 2>&1")
    all_good &= check_requirement(
        "FastAPI server starts without errors",
        server_check,
        critical=False
    )
    
    # Check for Python syntax errors
    syntax_check, _ = run_command("python -m py_compile fulfillment/**/*.py 2> /dev/null")
    all_good &= check_requirement(
        "No Python syntax errors",
        syntax_check
    )
    
    # 5. SSL/HTTPS Requirements
    print("\n📋 SSL/HTTPS Requirements:")
    print("⚠️  SSL certificate required for production webhook endpoint")
    print("   Options:")
    print("   1. Use a reverse proxy (nginx) with Let's Encrypt")
    print("   2. Deploy to a platform with automatic SSL (Heroku, Railway, etc.)")
    print("   3. Use ngrok for testing (not recommended for production)")
    
    # 6. Webhook Endpoint
    print("\n📋 Webhook Endpoint Configuration:")
    webhook_url = "https://your-domain.com/webhooks/shopify/order-create"
    print(f"⚠️  Production webhook URL needed: {webhook_url}")
    print("   Steps:")
    print("   1. Deploy the application to your server")
    print("   2. Configure SSL certificate")
    print("   3. Update Shopify webhook settings with the HTTPS URL")
    
    # 7. Database Considerations
    print("\n📋 Database Configuration:")
    print("ℹ️  Currently using JSON file storage")
    print("   For production, consider:")
    print("   - PostgreSQL for scalability")
    print("   - Airtable for easy management")
    print("   - Redis for caching")
    
    # 8. Monitoring & Logging
    print("\n📋 Monitoring & Logging:")
    print("⚠️  Production monitoring recommended:")
    print("   - Application logs (currently to stdout)")
    print("   - Error tracking (Sentry, Rollbar)")
    print("   - Performance monitoring (DataDog, New Relic)")
    print("   - Uptime monitoring (UptimeRobot, Pingdom)")
    
    # 9. Deployment Commands
    print("\n📋 Deployment Steps:")
    print("1. Update .env with production values:")
    print("   - Set ENVIRONMENT=production")
    print("   - Ensure all tokens are production tokens")
    print("   - Update webhook URL in Shopify")
    print("\n2. Start the server:")
    print("   ```")
    print("   uv run fulfillment/main.py")
    print("   ```")
    print("\n3. Or use a process manager:")
    print("   ```")
    print("   # Using PM2")
    print("   pm2 start 'uv run fulfillment/main.py' --name fulfillment")
    print("   ")
    print("   # Using systemd")
    print("   sudo systemctl start fulfillment")
    print("   ```")
    
    # 10. Testing Commands
    print("\n📋 Testing in Production:")
    print("1. Health check:")
    print("   curl https://your-domain.com/health")
    print("\n2. Test webhook (be careful - this will create real labels!):")
    print("   Use scripts/fulfillment/test_webhook.py with production URL")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    
    if all_good:
        print("✅ All critical checks passed!")
        print("\nNext steps:")
        print("1. Deploy application to server with SSL")
        print("2. Update Shopify webhook URL") 
        print("3. Switch to ENVIRONMENT=production")
        print("4. Test with a single order first")
    else:
        print("❌ Some critical checks failed")
        print("   Please fix the issues above before deploying to production")
        sys.exit(1)
    
    print("\n⚠️  IMPORTANT: Test with a single order before processing bulk orders!")
    print("   Remember: Live mode will charge $0.05 per label")


if __name__ == "__main__":
    main()