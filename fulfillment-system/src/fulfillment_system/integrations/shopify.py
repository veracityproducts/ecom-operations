"""Shopify webhook integration for order processing."""
import hmac
import hashlib
import base64
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from pydantic import BaseModel, Field

from ..utils.config import settings
from ..models.schemas import (
    Order, OrderChannel, OrderStatus, Customer, Address, LineItem
)


class ShopifyWebhookVerifier:
    """Verify Shopify webhook signatures for security."""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.logger = logging.getLogger(__name__)
    
    def verify(self, raw_body: bytes, hmac_header: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.
        
        Args:
            raw_body: Raw request body (bytes)
            hmac_header: Value from X-Shopify-Hmac-Sha256 header
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            computed_hmac = base64.b64encode(
                hmac.new(
                    self.webhook_secret.encode('utf-8'),
                    raw_body,
                    digestmod=hashlib.sha256
                ).digest()
            ).decode('utf-8')
            
            is_valid = hmac.compare_digest(computed_hmac, hmac_header)
            
            if not is_valid:
                self.logger.warning("Invalid webhook signature received")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False


class ShopifyWebhookHeaders(BaseModel):
    """Shopify webhook headers for validation."""
    hmac: str = Field(alias="X-Shopify-Hmac-Sha256")
    event_id: str = Field(alias="X-Shopify-Event-Id")
    shop_domain: str = Field(alias="X-Shopify-Shop-Domain")
    topic: str = Field(alias="X-Shopify-Topic")
    api_version: Optional[str] = Field(default=None, alias="X-Shopify-API-Version")
    
    class Config:
        populate_by_name = True


class ShopifyOrderConverter:
    """Convert Shopify order data to internal Order model."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def convert_order(self, shopify_order: Dict[str, Any]) -> Order:
        """
        Convert Shopify order format to internal Order model.
        
        Args:
            shopify_order: Raw order data from Shopify webhook
            
        Returns:
            Order model instance
        """
        try:
            # Extract customer information
            customer = self._extract_customer(shopify_order)
            
            # Extract addresses
            shipping_address = self._extract_address(
                shopify_order.get("shipping_address", {})
            )
            billing_address = self._extract_address(
                shopify_order.get("billing_address", {})
            )
            
            # Extract line items
            line_items = self._extract_line_items(
                shopify_order.get("line_items", [])
            )
            
            # Create order instance
            order = Order(
                order_number=str(shopify_order["order_number"]),
                channel=OrderChannel.SHOPIFY,
                status=self._map_order_status(shopify_order),
                customer=customer,
                shipping_address=shipping_address,
                billing_address=billing_address,
                line_items=line_items,
                subtotal=float(shopify_order.get("subtotal_price", 0)),
                shipping_cost=float(shopify_order.get("total_shipping_price_set", {})
                                  .get("shop_money", {})
                                  .get("amount", 0)),
                tax_amount=float(shopify_order.get("total_tax", 0)),
                total_amount=float(shopify_order.get("total_price", 0)),
                currency=shopify_order.get("currency", "USD"),
                channel_order_id=str(shopify_order["id"]),
                notes=shopify_order.get("note"),
                tags=shopify_order.get("tags", "").split(", ") if shopify_order.get("tags") else [],
                created_at=datetime.fromisoformat(
                    shopify_order["created_at"].replace("Z", "+00:00")
                )
            )
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error converting Shopify order: {e}")
            raise
    
    def _extract_customer(self, order_data: Dict[str, Any]) -> Customer:
        """Extract customer information from order data."""
        customer_data = order_data.get("customer", {})
        
        # Handle case where customer data might be embedded in order
        if not customer_data:
            customer_data = {
                "id": order_data.get("customer_id"),
                "email": order_data.get("email"),
                "first_name": order_data.get("customer", {}).get("first_name"),
                "last_name": order_data.get("customer", {}).get("last_name"),
                "phone": order_data.get("phone")
            }
        
        return Customer(
            id=str(customer_data.get("id", "")),
            email=customer_data.get("email") or order_data.get("email", ""),
            first_name=customer_data.get("first_name", ""),
            last_name=customer_data.get("last_name", ""),
            phone=customer_data.get("phone") or order_data.get("phone")
        )
    
    def _extract_address(self, address_data: Dict[str, Any]) -> Address:
        """Extract address information."""
        if not address_data:
            # Return a placeholder address if none provided
            return Address(
                name="Not Provided",
                address1="Not Provided",
                city="Not Provided",
                state="NA",
                postal_code="00000",
                country="US"
            )
        
        return Address(
            name=f"{address_data.get('first_name', '')} {address_data.get('last_name', '')}".strip(),
            company=address_data.get("company"),
            address1=address_data.get("address1", ""),
            address2=address_data.get("address2"),
            city=address_data.get("city", ""),
            state=address_data.get("province_code") or address_data.get("province", ""),
            postal_code=address_data.get("zip") or address_data.get("postal_code", ""),
            country=address_data.get("country_code", "US"),
            phone=address_data.get("phone")
        )
    
    def _extract_line_items(self, line_items_data: List[Dict[str, Any]]) -> List[LineItem]:
        """Extract line items from order."""
        line_items = []
        
        for item_data in line_items_data:
            # Skip items that don't require fulfillment
            if not item_data.get("requires_shipping", True):
                continue
            
            line_item = LineItem(
                id=str(item_data.get("id", "")),
                sku=item_data.get("sku") or f"SHOPIFY-{item_data.get('variant_id', 'NO-SKU')}",
                name=item_data.get("name", "Unknown Product"),
                quantity=int(item_data.get("quantity", 1)),
                price=float(item_data.get("price", 0)),
                weight_oz=self._convert_weight_to_oz(
                    item_data.get("grams", 0)
                ),
                requires_shipping=item_data.get("requires_shipping", True),
                product_id=str(item_data.get("product_id", "")),
                variant_id=str(item_data.get("variant_id", ""))
            )
            line_items.append(line_item)
        
        return line_items
    
    def _convert_weight_to_oz(self, grams: float) -> float:
        """Convert weight from grams to ounces."""
        return grams * 0.035274 if grams else 0.0
    
    def _map_order_status(self, order_data: Dict[str, Any]) -> OrderStatus:
        """Map Shopify order status to internal status."""
        financial_status = order_data.get("financial_status", "").lower()
        fulfillment_status = order_data.get("fulfillment_status", "").lower()
        cancelled_at = order_data.get("cancelled_at")
        
        if cancelled_at:
            return OrderStatus.CANCELLED
        elif fulfillment_status == "fulfilled":
            return OrderStatus.SHIPPED
        elif financial_status == "paid":
            return OrderStatus.PENDING
        else:
            return OrderStatus.PENDING


class ShopifyAPIClient:
    """Client for making API calls to Shopify."""
    
    def __init__(self, shop_domain: str, access_token: str, api_version: str = "2024-01"):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_domain}.myshopify.com/admin/api/{api_version}"
        
        self.client = httpx.AsyncClient(
            headers={
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def create_webhook(self, topic: str, address: str) -> Dict[str, Any]:
        """
        Create a webhook subscription.
        
        Args:
            topic: Webhook topic (e.g., "orders/create")
            address: URL to receive webhooks
            
        Returns:
            Created webhook data
        """
        webhook_data = {
            "webhook": {
                "topic": topic,
                "address": address,
                "format": "json"
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/webhooks.json",
            json=webhook_data
        )
        response.raise_for_status()
        
        return response.json()
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all configured webhooks."""
        response = await self.client.get(f"{self.base_url}/webhooks.json")
        response.raise_for_status()
        
        return response.json().get("webhooks", [])
    
    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook subscription."""
        response = await self.client.delete(
            f"{self.base_url}/webhooks/{webhook_id}.json"
        )
        response.raise_for_status()
    
    async def update_fulfillment(
        self, 
        order_id: str, 
        tracking_number: str,
        tracking_company: str,
        line_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update order fulfillment status in Shopify.
        
        Args:
            order_id: Shopify order ID
            tracking_number: Shipping tracking number
            tracking_company: Carrier name
            line_items: Items being fulfilled
            
        Returns:
            Fulfillment data
        """
        fulfillment_data = {
            "fulfillment": {
                "line_items": line_items,
                "tracking_number": tracking_number,
                "tracking_company": tracking_company,
                "notify_customer": True,
                "location_id": None  # Use default location
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/orders/{order_id}/fulfillments.json",
            json=fulfillment_data
        )
        response.raise_for_status()
        
        return response.json()
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details by ID."""
        response = await self.client.get(
            f"{self.base_url}/orders/{order_id}.json"
        )
        response.raise_for_status()
        
        return response.json().get("order", {})


class ShopifyWebhookService:
    """Main service for handling Shopify webhooks."""
    
    def __init__(self):
        self.verifier = ShopifyWebhookVerifier(settings.shopify.webhook_secret)
        self.converter = ShopifyOrderConverter()
        self.api_client = ShopifyAPIClient(
            shop_domain=settings.shopify.shop_domain,
            access_token=settings.shopify.access_token,
            api_version=settings.shopify.api_version
        )
        self.logger = logging.getLogger(__name__)
    
    async def setup_webhooks(self, webhook_url_base: str) -> Dict[str, str]:
        """
        Set up required webhooks for order processing.
        
        Args:
            webhook_url_base: Base URL for webhook endpoints
            
        Returns:
            Dictionary of topic -> webhook_id mappings
        """
        webhook_topics = [
            "orders/create",
            "orders/updated", 
            "orders/cancelled",
            "orders/fulfilled",
            "orders/paid"
        ]
        
        webhook_ids = {}
        
        async with self.api_client as client:
            # First, list existing webhooks
            existing_webhooks = await client.list_webhooks()
            
            # Delete any existing webhooks for our topics
            for webhook in existing_webhooks:
                if webhook["topic"] in webhook_topics:
                    await client.delete_webhook(webhook["id"])
                    self.logger.info(f"Deleted existing webhook for {webhook['topic']}")
            
            # Create new webhooks
            for topic in webhook_topics:
                webhook_url = f"{webhook_url_base}/webhooks/shopify/{topic.replace('/', '-')}"
                
                try:
                    result = await client.create_webhook(topic, webhook_url)
                    webhook_ids[topic] = result["webhook"]["id"]
                    self.logger.info(f"Created webhook for {topic} -> {webhook_url}")
                except Exception as e:
                    self.logger.error(f"Failed to create webhook for {topic}: {e}")
        
        return webhook_ids
    
    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """
        Verify webhook authenticity.
        
        Args:
            raw_body: Raw request body
            headers: Request headers
            
        Returns:
            True if webhook is valid
        """
        hmac_header = headers.get("X-Shopify-Hmac-Sha256", "")
        return self.verifier.verify(raw_body, hmac_header)
    
    def process_order_webhook(self, webhook_data: Dict[str, Any]) -> Order:
        """
        Process order webhook data.
        
        Args:
            webhook_data: Parsed webhook JSON data
            
        Returns:
            Converted Order model
        """
        return self.converter.convert_order(webhook_data)
    
    async def mark_order_fulfilled(
        self,
        order: Order,
        tracking_number: str,
        carrier: str
    ) -> bool:
        """
        Mark order as fulfilled in Shopify.
        
        Args:
            order: Order model
            tracking_number: Shipping tracking number  
            carrier: Carrier name
            
        Returns:
            True if successful
        """
        try:
            # Prepare line items for fulfillment
            line_items = [
                {
                    "id": item.id,
                    "quantity": item.quantity
                }
                for item in order.line_items
                if item.id  # Only include items with Shopify IDs
            ]
            
            async with self.api_client as client:
                await client.update_fulfillment(
                    order_id=order.channel_order_id,
                    tracking_number=tracking_number,
                    tracking_company=carrier,
                    line_items=line_items
                )
            
            self.logger.info(
                f"Successfully marked order {order.order_number} as fulfilled "
                f"with tracking {tracking_number}"
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to mark order {order.order_number} as fulfilled: {e}"
            )
            return False


# Global service instance
_shopify_service: Optional[ShopifyWebhookService] = None


def get_shopify_service() -> ShopifyWebhookService:
    """Get or create Shopify service instance."""
    global _shopify_service
    if _shopify_service is None:
        _shopify_service = ShopifyWebhookService()
    return _shopify_service