#!/usr/bin/env python3
"""Simple test to verify Shippo API connection."""
import os
import httpx
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

async def test_shippo_api():
    """Test direct Shippo API connection."""
    token = os.getenv("SHIPPING_SHIPPO_TEST_API_TOKEN")
    if not token:
        print("❌ No Shippo test token found in .env")
        return
        
    print(f"🔑 Using token: {token[:10]}...")
    
    async with httpx.AsyncClient() as client:
        # Test API connection
        response = await client.get(
            "https://api.goshippo.com/carrier_accounts",
            headers={"Authorization": f"ShippoToken {token}"}
        )
        
        if response.status_code == 200:
            print("✅ Shippo API connection successful!")
            accounts = response.json()
            print(f"📦 Found {len(accounts.get('results', []))} carrier accounts")
        else:
            print(f"❌ API error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(test_shippo_api())