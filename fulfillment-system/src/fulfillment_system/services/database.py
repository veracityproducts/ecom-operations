"""Database service interface - currently using simple JSON storage."""
from typing import Optional, List, Dict, Any
import logging

from .simple_storage import get_storage
from ..models.schemas import Order, Fulfillment


class DatabaseService:
    """
    Database service that currently uses simple JSON storage.
    
    This interface makes it easy to swap to Airtable, PostgreSQL, or DuckDB later.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.storage = get_storage()
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
    
    async def connect(self):
        """Connect to database (no-op for file storage)."""
        self.is_connected = True
        self.logger.info("Database service initialized with JSON file storage")
    
    async def disconnect(self):
        """Disconnect from database (no-op for file storage)."""
        self.is_connected = False
        self.logger.info("Database service disconnected")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        stats = await self.storage.get_stats()
        return {
            "status": "healthy" if self.is_connected else "disconnected",
            "type": "json_file_storage",
            **stats
        }
    
    # Order operations
    
    async def create_order(self, order: Order) -> str:
        """Create new order."""
        return await self.storage.save_order(order)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return await self.storage.get_order(order_id)
    
    async def get_order_by_channel_id(self, channel_order_id: str) -> Optional[Order]:
        """Get order by channel order ID."""
        return await self.storage.get_order_by_channel_id(channel_order_id)
    
    async def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status."""
        order = await self.get_order(order_id)
        if order:
            order.status = status
            await self.storage.save_order(order)
            return True
        return False
    
    async def list_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List orders with optional filtering."""
        return await self.storage.list_orders(status, limit, offset)
    
    # Fulfillment operations
    
    async def create_fulfillment(self, fulfillment: Fulfillment) -> str:
        """Create fulfillment record."""
        return await self.storage.save_fulfillment(fulfillment)
    
    async def get_fulfillment_by_order(self, order_id: str) -> Optional[Fulfillment]:
        """Get fulfillment by order ID."""
        return await self.storage.get_fulfillment_by_order(order_id)
    
    async def update_fulfillment_status(
        self,
        fulfillment_id: str,
        status: str,
        tracking_number: Optional[str] = None
    ) -> bool:
        """Update fulfillment status."""
        # For now, we'll need to implement this when needed
        # The simple storage doesn't support updates yet
        return True
    
    # Export for migration
    
    async def export_for_airtable(self) -> Dict[str, List[Dict[str, Any]]]:
        """Export all data in Airtable format for easy migration."""
        return await self.storage.export_to_airtable_format()