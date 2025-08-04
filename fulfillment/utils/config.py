"""Configuration management for fulfillment module."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Shippo Configuration
    shippo_api_token: str = os.getenv("SHIPPING_SHIPPO_API_TOKEN", "")
    shippo_test_token: str = os.getenv("SHIPPING_SHIPPO_TEST_API_TOKEN", "")
    shippo_test_mode: bool = os.getenv("ENVIRONMENT", "development") != "production"
    use_test_mode: bool = os.getenv("ENVIRONMENT", "development") != "production"
    
    # Shopify Configuration
    shopify_shop_domain: str = os.getenv("SHOPIFY_SHOP_DOMAIN", "")
    shopify_access_token: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    shopify_webhook_secret: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    shopify_api_version: str = os.getenv("SHOPIFY_API_VERSION", "2024-01")
    
    # Warehouse Configuration
    warehouse_ca_name: str = os.getenv("WAREHOUSE_CA_NAME", "Grooved Learning CA")
    warehouse_ca_address1: str = os.getenv("WAREHOUSE_CA_ADDRESS1", "")
    warehouse_ca_city: str = os.getenv("WAREHOUSE_CA_CITY", "Los Angeles")
    warehouse_ca_state: str = os.getenv("WAREHOUSE_CA_STATE", "CA")
    warehouse_ca_zip: str = os.getenv("WAREHOUSE_CA_ZIP", "90210")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = int(os.getenv("API_PORT", "8750"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def shippo_token(self) -> str:
        """Get the appropriate Shippo token based on environment."""
        return self.shippo_test_token if self.use_test_mode else self.shippo_api_token
    
    @property
    def warehouse_ca_address(self) -> dict:
        """Get CA warehouse address as dict for Shippo."""
        return {
            "name": self.warehouse_ca_name,
            "street1": self.warehouse_ca_address1,
            "city": self.warehouse_ca_city,
            "state": self.warehouse_ca_state,
            "zip": self.warehouse_ca_zip,
            "country": "US"
        }


settings = Settings()