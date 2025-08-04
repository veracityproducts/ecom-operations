"""Shopify API client for interacting with Shopify Admin API."""
import httpx
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ShopifyClient:
    """Client for Shopify Admin API operations."""
    
    def __init__(self, shop_domain: str, access_token: str, api_version: str = "2025-01"):
        """Initialize Shopify client."""
        self.shop_domain = shop_domain.replace("https://", "").replace("http://", "")
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{self.shop_domain}/admin/api/{api_version}"
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            headers={
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def get_orders(self, **params) -> Dict[str, Any]:
        """Fetch orders from Shopify."""
        try:
            response = await self.client.get(
                f"{self.base_url}/orders.json",
                params=params
            )
            response.raise_for_status()
            
            # Include headers in response for pagination
            return {
                "orders": response.json().get("orders", []),
                "headers": dict(response.headers)
            }
        except httpx.HTTPError as e:
            logger.error(f"Error fetching orders: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Fetch a specific order."""
        try:
            response = await self.client.get(
                f"{self.base_url}/orders/{order_id}.json"
            )
            response.raise_for_status()
            return response.json()["order"]
        except httpx.HTTPError as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            raise
    
    async def get_fulfillment_orders(self, order_id: str) -> List[Dict[str, Any]]:
        """Get fulfillment orders for an order."""
        try:
            response = await self.client.get(
                f"{self.base_url}/orders/{order_id}/fulfillment_orders.json"
            )
            response.raise_for_status()
            return response.json()["fulfillment_orders"]
        except httpx.HTTPError as e:
            logger.error(f"Error getting fulfillment orders for order {order_id}: {e}")
            raise
    
    async def create_fulfillment(self, tracking_number: str, tracking_company: str, 
                                fulfillment_order_id: str, notify_customer: bool = False) -> Dict[str, Any]:
        """Create a fulfillment using the newer fulfillment orders API."""
        try:
            fulfillment_data = {
                "fulfillment": {
                    "notify_customer": notify_customer,
                    "tracking_info": {
                        "number": tracking_number,
                        "company": tracking_company
                    },
                    "line_items_by_fulfillment_order": [
                        {
                            "fulfillment_order_id": fulfillment_order_id,
                            "fulfillment_order_line_items": []  # Empty = all items
                        }
                    ]
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/fulfillments.json",
                json=fulfillment_data
            )
            response.raise_for_status()
            return response.json()["fulfillment"]
        except httpx.HTTPError as e:
            logger.error(f"Error creating fulfillment: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    async def update_order_fulfillment(self, order_id: str, fulfillment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fulfillment for an order (compatibility method)."""
        # Get fulfillment orders first
        fulfillment_orders = await self.get_fulfillment_orders(order_id)
        if not fulfillment_orders:
            raise ValueError(f"No fulfillment orders found for order {order_id}")
        
        # Use the first open fulfillment order
        fo = next((fo for fo in fulfillment_orders if fo["status"] == "open"), None)
        if not fo:
            raise ValueError(f"No open fulfillment orders found for order {order_id}")
        
        # Create fulfillment using the newer API
        return await self.create_fulfillment(
            tracking_number=fulfillment_data.get("tracking_number", ""),
            tracking_company=fulfillment_data.get("tracking_company", "Other"),
            fulfillment_order_id=fo["id"],
            notify_customer=fulfillment_data.get("notify_customer", False)
        )
    
    async def register_webhook(self, topic: str, address: str) -> Dict[str, Any]:
        """Register a webhook with Shopify."""
        try:
            response = await self.client.post(
                f"{self.base_url}/webhooks.json",
                json={
                    "webhook": {
                        "topic": topic,
                        "address": address,
                        "format": "json"
                    }
                }
            )
            response.raise_for_status()
            return response.json()["webhook"]
        except httpx.HTTPError as e:
            logger.error(f"Error registering webhook: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks."""
        try:
            response = await self.client.get(
                f"{self.base_url}/webhooks.json"
            )
            response.raise_for_status()
            return response.json()["webhooks"]
        except httpx.HTTPError as e:
            logger.error(f"Error listing webhooks: {e}")
            raise