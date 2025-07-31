"""
Pydantic models for Grooved Learning Fulfillment System.

Following og-phonics patterns for data validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, validator


class OrderChannel(str, Enum):
    """Sales channel enumeration."""
    SHOPIFY = "shopify"
    AMAZON = "amazon"
    TIKTOK = "tiktok"
    MANUAL = "manual"


class OrderStatus(str, Enum):
    """Order processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    ROUTED = "routed"
    LABELED = "labeled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    ERROR = "error"


class WarehouseLocation(str, Enum):
    """Warehouse location enumeration."""
    CALIFORNIA = "CA"
    PENNSYLVANIA = "PA"
    AMAZON_FBA = "FBA"
    TIKTOK_WAREHOUSE = "TIKTOK"


class CarrierType(str, Enum):
    """Shipping carrier enumeration."""
    USPS = "USPS"
    UPS = "UPS"
    FEDEX = "FedEx"


class Address(BaseModel):
    """Shipping address model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    address1: str = Field(..., min_length=1, max_length=100)
    address2: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., min_length=1, max_length=50)
    state: str = Field(..., min_length=2, max_length=50)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=3)
    phone: Optional[str] = Field(None, max_length=20)
    
    @validator('postal_code')
    def validate_postal_code(cls, v, values):
        """Validate postal code format."""
        if values.get('country') == 'US':
            # US ZIP code validation
            import re
            if not re.match(r'^\d{5}(-\d{4})?$', v):
                raise ValueError('Invalid US ZIP code format')
        return v
    
    @property
    def formatted_address(self) -> str:
        """Return formatted address string."""
        lines = [self.name]
        if self.company:
            lines.append(self.company)
        lines.append(self.address1)
        if self.address2:
            lines.append(self.address2)
        lines.append(f"{self.city}, {self.state} {self.postal_code}")
        if self.country != "US":
            lines.append(self.country)
        return "\n".join(lines)


class Customer(BaseModel):
    """Customer information model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: Optional[str] = None
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    
    @property
    def full_name(self) -> str:
        """Return full customer name."""
        return f"{self.first_name} {self.last_name}"


class LineItem(BaseModel):
    """Order line item model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: Optional[str] = None
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=1)
    price: Decimal = Field(..., ge=0)
    weight_oz: Optional[float] = Field(None, ge=0)
    requires_shipping: bool = Field(default=True)
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    
    @property
    def total_price(self) -> Decimal:
        """Calculate total price for line item."""
        return self.price * self.quantity
    
    @property
    def total_weight_oz(self) -> float:
        """Calculate total weight for line item."""
        return (self.weight_oz or 0) * self.quantity


class Order(BaseModel):
    """Main order model."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    id: UUID = Field(default_factory=uuid4)
    order_number: str = Field(..., min_length=1, max_length=50)
    channel: OrderChannel
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    
    customer: Customer
    shipping_address: Address
    billing_address: Optional[Address] = None
    
    line_items: List[LineItem] = Field(..., min_items=1)
    
    subtotal: Decimal = Field(..., ge=0)
    shipping_cost: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Decimal = Field(..., ge=0)
    
    currency: str = Field(default="USD", min_length=3, max_length=3)
    
    # Metadata
    channel_order_id: str = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('line_items')
    def validate_line_items(cls, v):
        """Ensure line items are valid."""
        if not v:
            raise ValueError('Order must have at least one line item')
        
        # Check for duplicate SKUs
        skus = [item.sku for item in v]
        if len(skus) != len(set(skus)):
            raise ValueError('Duplicate SKUs not allowed in line items')
        
        return v
    
    @property
    def total_weight_oz(self) -> float:
        """Calculate total order weight."""
        return sum(item.total_weight_oz for item in self.line_items)
    
    @property
    def requires_shipping(self) -> bool:
        """Check if order requires shipping."""
        return any(item.requires_shipping for item in self.line_items)
    
    @property
    def shipping_items(self) -> List[LineItem]:
        """Get items that require shipping."""
        return [item for item in self.line_items if item.requires_shipping]


class InventoryLevel(BaseModel):
    """Inventory level tracking model."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: UUID = Field(default_factory=uuid4)
    sku: str = Field(..., min_length=1, max_length=50)
    warehouse_location: WarehouseLocation
    
    quantity_on_hand: int = Field(..., ge=0)
    quantity_reserved: int = Field(..., ge=0)
    quantity_available: int = Field(..., ge=0)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('quantity_available')
    def validate_available_quantity(cls, v, values):
        """Ensure available quantity is correct."""
        on_hand = values.get('quantity_on_hand', 0)
        reserved = values.get('quantity_reserved', 0)
        expected_available = on_hand - reserved
        
        if v != expected_available:
            raise ValueError(
                f'Available quantity {v} does not match '
                f'on_hand ({on_hand}) - reserved ({reserved}) = {expected_available}'
            )
        return v


class ShippingRate(BaseModel):
    """Shipping rate model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    carrier: CarrierType
    service_level: str = Field(..., min_length=1, max_length=50)
    cost: Decimal = Field(..., ge=0)
    estimated_days: int = Field(..., ge=1)
    guaranteed: bool = Field(default=False)
    
    # Additional details
    description: Optional[str] = None
    max_weight_oz: Optional[float] = Field(None, ge=0)
    
    @property
    def cost_per_day(self) -> Decimal:
        """Calculate cost efficiency metric."""
        return self.cost / self.estimated_days


class Fulfillment(BaseModel):
    """Fulfillment tracking model."""
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
    
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    
    warehouse_location: WarehouseLocation
    carrier: CarrierType
    service_level: str = Field(..., min_length=1, max_length=50)
    
    tracking_number: Optional[str] = Field(None, max_length=100)
    label_url: Optional[str] = None
    packing_slip_url: Optional[str] = None
    
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    
    # Cost tracking
    shipping_cost: Optional[Decimal] = Field(None, ge=0)
    labor_cost: Optional[Decimal] = Field(None, ge=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    @property
    def is_shipped(self) -> bool:
        """Check if fulfillment has been shipped."""
        return self.shipped_at is not None
    
    @property
    def is_delivered(self) -> bool:
        """Check if fulfillment has been delivered."""
        return self.delivered_at is not None


class ProcessingMetrics(BaseModel):
    """Processing performance metrics model."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    stage: str = Field(..., min_length=1, max_length=50)
    processing_time_ms: int = Field(..., ge=0)
    success: bool
    error_message: Optional[str] = Field(None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response Models

class OrderCreateRequest(BaseModel):
    """Request model for creating orders."""
    order_number: str
    channel: OrderChannel
    customer: Customer
    shipping_address: Address
    billing_address: Optional[Address] = None
    line_items: List[LineItem]
    subtotal: Decimal
    shipping_cost: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Decimal
    channel_order_id: str
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class OrderResponse(BaseModel):
    """Response model for order operations."""
    order: Order
    fulfillment: Optional[Fulfillment] = None
    processing_time_ms: Optional[int] = None


class InventoryUpdateRequest(BaseModel):
    """Request model for inventory updates."""
    sku: str
    warehouse_location: WarehouseLocation
    quantity_on_hand: int = Field(..., ge=0)
    quantity_reserved: int = Field(..., ge=0)


class WebhookPayload(BaseModel):
    """Generic webhook payload model."""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    source: str = Field(..., min_length=1)
    
    # Optional signature verification
    signature: Optional[str] = None


# Error Models

class FulfillmentError(BaseModel):
    """Error response model."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(BaseModel):
    """Validation error details."""
    field: str
    message: str
    value: Any = None