#!/usr/bin/env python3
"""Test script to verify server imports work correctly."""
import sys
from pathlib import Path

# Add fulfillment module to path (same as in tests)
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fulfillment.main import app
    print("✅ FastAPI app imported successfully")
    print(f"✅ App title: {app.title}")
    print(f"✅ App version: {app.version}")
    print("✅ Server startup validation complete")
except Exception as e:
    print(f"❌ Error importing app: {e}")
    sys.exit(1)