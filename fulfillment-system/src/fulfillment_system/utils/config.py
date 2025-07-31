"""
Configuration management using Pydantic Settings.

Following og-phonics patterns for environment-based configuration
with proper validation and type hints.
"""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="fulfillment", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(description="Database password")
    
    # Connection pool settings
    min_connections: int = Field(default=5, description="Minimum connection pool size")
    max_connections: int = Field(default=20, description="Maximum connection pool size")
    
    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    
    # Connection settings
    max_connections: int = Field(default=50, description="Maximum connections")
    socket_timeout: int = Field(default=30, description="Socket timeout in seconds")
    
    @property
    def url(self) -> str:
        """Construct Redis URL."""
        auth_part = f":{self.password}@" if self.password else ""
        return f"redis://{auth_part}{self.host}:{self.port}/{self.db}"


class ShippingCarrierSettings(BaseSettings):
    """Shipping carrier API configuration."""
    model_config = SettingsConfigDict(env_prefix="SHIPPING_")
    
    # Shippo Configuration (Primary platform)
    shippo_api_token: str = Field(description="Shippo API token")
    shippo_test_api_token: Optional[str] = Field(default=None, description="Shippo test API token")
    shippo_base_url: str = Field(default="https://api.goshippo.com", description="Shippo API base URL")
    shippo_rate_limit_tier: str = Field(default="standard", description="Shippo rate limit tier")
    shippo_preferred_carrier: Optional[str] = Field(default="usps", description="Preferred carrier for rate selection")
    
    # USPS Configuration
    usps_api_key: Optional[str] = Field(default=None, description="USPS API key")
    usps_username: Optional[str] = Field(default=None, description="USPS username")
    usps_password: Optional[str] = Field(default=None, description="USPS password")
    usps_base_url: str = Field(default="https://api.usps.com", description="USPS API base URL")
    
    # UPS Configuration
    ups_api_key: Optional[str] = Field(default=None, description="UPS API key")
    ups_username: Optional[str] = Field(default=None, description="UPS username")
    ups_password: Optional[str] = Field(default=None, description="UPS password")
    ups_base_url: str = Field(default="https://api.ups.com", description="UPS API base URL")
    
    # FedEx Configuration
    fedex_api_key: Optional[str] = Field(default=None, description="FedEx API key")
    fedex_secret_key: Optional[str] = Field(default=None, description="FedEx secret key")
    fedex_base_url: str = Field(default="https://api.fedex.com", description="FedEx API base URL")
    
    # General settings
    default_package_type: str = Field(default="BOX", description="Default package type")
    max_weight_oz: int = Field(default=1600, description="Maximum package weight in ounces")
    
    @property
    def shippo_token(self) -> str:
        """Get appropriate Shippo token based on environment."""
        if hasattr(self, '_parent_settings') and hasattr(self._parent_settings, 'environment'):
            if self._parent_settings.environment == "production":
                return self.shippo_api_token
        return self.shippo_test_api_token or self.shippo_api_token


class ShopifySettings(BaseSettings):
    """Shopify Plus integration settings."""
    model_config = SettingsConfigDict(env_prefix="SHOPIFY_")
    
    shop_domain: str = Field(description="Shopify shop domain (without .myshopify.com)")
    access_token: str = Field(description="Shopify private app access token")
    webhook_secret: str = Field(description="Shopify webhook verification secret")
    api_version: str = Field(default="2023-01", description="Shopify API version")
    
    # Webhook configuration
    webhook_endpoints: List[str] = Field(
        default=["orders/create", "orders/updated", "orders/cancelled"],
        description="Webhook endpoints to handle"
    )
    
    @property
    def api_base_url(self) -> str:
        """Construct Shopify API base URL."""
        return f"https://{self.shop_domain}.myshopify.com/admin/api/{self.api_version}"


class StorageSettings(BaseSettings):
    """File storage configuration."""
    model_config = SettingsConfigDict(env_prefix="STORAGE_")
    
    provider: str = Field(default="google_drive", description="Storage provider")
    
    # Google Drive settings
    google_drive_credentials_path: Optional[str] = Field(
        default=None, 
        description="Path to Google Drive service account credentials"
    )
    google_drive_folder_id: Optional[str] = Field(
        default=None,
        description="Google Drive folder ID for document storage"
    )
    
    # S3 settings (alternative)
    s3_bucket_name: Optional[str] = Field(default=None, description="S3 bucket name")
    s3_region: Optional[str] = Field(default="us-west-2", description="S3 region")
    s3_access_key: Optional[str] = Field(default=None, description="S3 access key")
    s3_secret_key: Optional[str] = Field(default=None, description="S3 secret key")
    
    # Local storage settings (development)
    local_storage_path: str = Field(
        default="./storage",
        description="Local storage path for development"
    )


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""
    model_config = SettingsConfigDict(env_prefix="MONITORING_")
    
    # Prometheus settings
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json",
        description="Logging format (json or text)"
    )
    
    # Health check settings
    health_check_timeout: int = Field(
        default=30,
        description="Health check timeout in seconds"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    
    # API security
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    jwt_secret: Optional[str] = Field(default=None, description="JWT signing secret")
    jwt_expiry_minutes: int = Field(default=60, description="JWT token expiry in minutes")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "https://groovedlearning.com"],
        description="Allowed CORS origins"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1", "groovedlearning.com"],
        description="Allowed host headers"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Rate limit requests per minute"
    )
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit window in seconds"
    )


class WarehouseSettings(BaseSettings):
    """Warehouse configuration settings."""
    model_config = SettingsConfigDict(env_prefix="WAREHOUSE_")
    
    # California warehouse
    ca_name: str = Field(default="Grooved Learning CA", description="CA warehouse name")
    ca_address1: str = Field(default="123 Education Way", description="CA address line 1")
    ca_city: str = Field(default="Los Angeles", description="CA city")
    ca_state: str = Field(default="CA", description="CA state")
    ca_postal_code: str = Field(default="90210", description="CA postal code")
    ca_phone: Optional[str] = Field(default=None, description="CA phone number")
    
    # Pennsylvania warehouse
    pa_name: str = Field(default="Grooved Learning PA", description="PA warehouse name")
    pa_address1: str = Field(default="456 Learning Lane", description="PA address line 1")
    pa_city: str = Field(default="Philadelphia", description="PA city")
    pa_state: str = Field(default="PA", description="PA state")
    pa_postal_code: str = Field(default="19019", description="PA postal code")
    pa_phone: Optional[str] = Field(default=None, description="PA phone number")
    
    # Business rules
    default_warehouse_selection: str = Field(
        default="distance_optimized",
        description="Default warehouse selection strategy"
    )
    inventory_sync_interval_minutes: int = Field(
        default=15,
        description="Inventory sync interval in minutes"
    )


class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )
    
    # Application settings
    app_name: str = Field(default="Grooved Learning Fulfillment System")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    shipping: ShippingCarrierSettings = Field(default_factory=ShippingCarrierSettings)
    shopify: ShopifySettings = Field(default_factory=ShopifySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    warehouse: WarehouseSettings = Field(default_factory=WarehouseSettings)
    
    # Performance settings
    max_concurrent_orders: int = Field(
        default=50,
        description="Maximum concurrent order processing"
    )
    request_timeout_seconds: int = Field(
        default=30,
        description="HTTP request timeout"
    )
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'environment must be one of {valid_envs}')
        return v
    
    @property
    def database_url(self) -> str:
        """Get database URL."""
        return self.database.url
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        return self.redis.url
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed CORS origins."""
        return self.security.allowed_origins
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Get allowed host headers."""
        return self.security.allowed_hosts


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings