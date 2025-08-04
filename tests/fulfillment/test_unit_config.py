#!/usr/bin/env python3
"""Unit tests for fulfillment configuration."""
import os
import pytest
from pathlib import Path
import sys

# Add fulfillment module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fulfillment.utils.config import Settings


def test_settings_loads_env():
    """Test that settings loads from environment variables."""
    settings = Settings()
    
    # Should load from .env file
    assert settings.shopify_shop_domain == "groovedlearning.com"
    assert settings.shopify_api_version == "2025-07"  # Updated to current version
    assert settings.api_port == 8750


def test_shippo_token_selection():
    """Test that correct Shippo token is selected based on environment."""
    settings = Settings()
    
    # In development/test mode
    assert settings.use_test_mode == True
    assert settings.shippo_token == settings.shippo_test_token
    assert settings.shippo_token.startswith("shippo_test_")


def test_warehouse_address_format():
    """Test warehouse address is properly formatted."""
    settings = Settings()
    
    address = settings.warehouse_ca_address
    assert isinstance(address, dict)
    assert address["name"] == "Grooved Learning CA"
    assert address["state"] == "CA"
    assert address["country"] == "US"
    assert all(key in address for key in ["name", "street1", "city", "state", "zip", "country"])


def test_api_configuration():
    """Test API configuration defaults."""
    settings = Settings()
    
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8750
    assert isinstance(settings.debug, bool)