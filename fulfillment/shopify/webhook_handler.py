"""Shopify webhook handler following Grooved Learning patterns."""
import json
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

from fulfillment.utils.config import Settings

logger = logging.getLogger(__name__)


class ShopifyOrder(BaseModel):
    """Shopify order webhook payload model."""
    id: int
    order_number: str
    name: str
    email: Optional[str] = None
    total_price: str
    currency: str
    fulfillment_status: Optional[str] = None
    financial_status: str
    shipping_address: Optional[Dict[str, Any]] = None
    line_items: list[Dict[str, Any]] = []
    created_at: str
    updated_at: str


class ShopifyWebhookHandler:
    """Production webhook handler with signature verification."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.webhook_secret = settings.shopify_webhook_secret
        self.logger = logging.getLogger(__name__)
    
    async def verify_webhook_signature(self, request: Request) -> bool:
        """Verify webhook signature using HMAC-SHA256."""
        if not self.webhook_secret:
            self.logger.warning("No webhook secret configured - skipping verification")
            return True
        
        # Get signature from header
        signature_header = request.headers.get("X-Shopify-Hmac-Sha256")
        if not signature_header:
            self.logger.error("Missing webhook signature header")
            return False
        
        # Get raw body
        body = await request.body()
        
        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()  # Use digest() instead of hexdigest()
        
        # Shopify sends base64 encoded signature
        expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
        
        # Compare signatures
        is_valid = hmac.compare_digest(signature_header, expected_signature_base64)
        
        if not is_valid:
            self.logger.error(f"Invalid webhook signature. Expected: {expected_signature_base64[:10]}..., Got: {signature_header[:10]}...")
        
        return is_valid
    
    async def parse_order_webhook(self, request: Request) -> ShopifyOrder:
        """Parse and validate Shopify order webhook payload."""
        try:
            # Verify signature first
            if not await self.verify_webhook_signature(request):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid webhook signature"
                )
            
            # Parse JSON payload
            body = await request.body()
            order_data = json.loads(body)
            
            # Validate with Pydantic
            order = ShopifyOrder(**order_data)
            
            self.logger.info(
                f"Parsed order webhook: {order.order_number} "
                f"(ID: {order.id}, Status: {order.financial_status})"
            )
            
            return order
            
        except ValidationError as e:
            self.logger.error(f"Order validation error: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid order data: {e}"
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error parsing webhook: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
    
    def should_process_order(self, order: ShopifyOrder) -> bool:
        """Determine if order should be processed for fulfillment."""
        # Only process paid orders
        if order.financial_status.lower() != "paid":
            self.logger.info(
                f"Skipping order {order.order_number} - "
                f"financial status: {order.financial_status}"
            )
            return False
        
        # Skip if already fulfilled
        if order.fulfillment_status == "fulfilled":
            self.logger.info(
                f"Skipping order {order.order_number} - already fulfilled"
            )
            return False
        
        # Must have shipping address
        if not order.shipping_address:
            self.logger.warning(
                f"Skipping order {order.order_number} - no shipping address"
            )
            return False
        
        # Must have line items
        if not order.line_items:
            self.logger.warning(
                f"Skipping order {order.order_number} - no line items"
            )
            return False
        
        return True
    
    def extract_shipping_info(self, order: ShopifyOrder) -> Dict[str, Any]:
        """Extract shipping information for label creation."""
        shipping = order.shipping_address
        if not shipping:
            raise ValueError("No shipping address available")
        
        return {
            "name": shipping.get(
                "name", 
                f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip()
            ),
            "street1": shipping.get("address1", ""),
            "street2": shipping.get("address2", ""),
            "city": shipping.get("city", ""),
            "state": shipping.get("province_code", shipping.get("province", "")),
            "zip": shipping.get("zip", ""),
            "country": shipping.get("country_code", "US"),
            "phone": shipping.get("phone", ""),
            "email": order.email or ""
        }
    
    def calculate_package_weight(self, order: ShopifyOrder) -> float:
        """Calculate total package weight from line items."""
        total_weight = 0.0
        
        for item in order.line_items:
            # Get weight in grams, convert to pounds
            weight_grams = float(item.get("grams", 0))
            weight_pounds = weight_grams / 453.592  # grams to pounds
            quantity = int(item.get("quantity", 1))
            
            total_weight += weight_pounds * quantity
        
        # Minimum weight of 1 lb for small items
        return max(total_weight, 1.0)