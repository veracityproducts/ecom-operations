"""Simple JSON file storage for quick prototyping."""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from uuid import UUID

from ..models.schemas import Order, Fulfillment


class SimpleJsonStorage:
    """
    Simple JSON-based storage for orders and fulfillments.
    
    This is perfect for testing and can easily transition to Airtable later.
    All data is stored in human-readable JSON files.
    """
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.orders_dir = self.data_dir / "orders"
        self.fulfillments_dir = self.data_dir / "fulfillments"
        self.orders_dir.mkdir(exist_ok=True)
        self.fulfillments_dir.mkdir(exist_ok=True)
        
        # Index files for quick lookups
        self.orders_index_file = self.data_dir / "orders_index.json"
        self.fulfillments_index_file = self.data_dir / "fulfillments_index.json"
        
        # Load or create indexes
        self._load_indexes()
    
    def _load_indexes(self):
        """Load or create index files."""
        if self.orders_index_file.exists():
            with open(self.orders_index_file, 'r') as f:
                self.orders_index = json.load(f)
        else:
            self.orders_index = {}
            self._save_orders_index()
        
        if self.fulfillments_index_file.exists():
            with open(self.fulfillments_index_file, 'r') as f:
                self.fulfillments_index = json.load(f)
        else:
            self.fulfillments_index = {}
            self._save_fulfillments_index()
    
    def _save_orders_index(self):
        """Save orders index to file."""
        with open(self.orders_index_file, 'w') as f:
            json.dump(self.orders_index, f, indent=2)
    
    def _save_fulfillments_index(self):
        """Save fulfillments index to file."""
        with open(self.fulfillments_index_file, 'w') as f:
            json.dump(self.fulfillments_index, f, indent=2)
    
    async def save_order(self, order: Order) -> str:
        """
        Save order to JSON file.
        
        Returns:
            Order ID as string
        """
        order_id = str(order.id)
        order_data = order.model_dump(mode='json')
        
        # Save order file
        order_file = self.orders_dir / f"{order.order_number}.json"
        with open(order_file, 'w') as f:
            json.dump(order_data, f, indent=2, default=str)
        
        # Update index
        self.orders_index[order_id] = {
            "order_number": order.order_number,
            "channel_order_id": order.channel_order_id,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "customer_email": order.customer.email,
            "total_amount": float(order.total_amount),
            "file_path": str(order_file.name)
        }
        self._save_orders_index()
        
        return order_id
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        if order_id not in self.orders_index:
            return None
        
        order_info = self.orders_index[order_id]
        order_file = self.orders_dir / order_info["file_path"]
        
        if not order_file.exists():
            return None
        
        with open(order_file, 'r') as f:
            order_data = json.load(f)
        
        return Order(**order_data)
    
    async def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        order_file = self.orders_dir / f"{order_number}.json"
        
        if not order_file.exists():
            return None
        
        with open(order_file, 'r') as f:
            order_data = json.load(f)
        
        return Order(**order_data)
    
    async def get_order_by_channel_id(self, channel_order_id: str) -> Optional[Order]:
        """Get order by channel order ID (e.g., Shopify ID)."""
        for order_id, order_info in self.orders_index.items():
            if order_info["channel_order_id"] == channel_order_id:
                return await self.get_order(order_id)
        return None
    
    async def list_orders(
        self, 
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List orders with optional filtering."""
        orders = []
        
        for order_id, order_info in self.orders_index.items():
            if status and order_info["status"] != status:
                continue
            orders.append({
                "id": order_id,
                **order_info
            })
        
        # Sort by created_at descending
        orders.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        return orders[offset:offset + limit]
    
    async def save_fulfillment(self, fulfillment: Fulfillment) -> str:
        """Save fulfillment to JSON file."""
        fulfillment_id = str(fulfillment.id)
        fulfillment_data = fulfillment.model_dump(mode='json')
        
        # Save fulfillment file
        fulfillment_file = self.fulfillments_dir / f"{fulfillment_id}.json"
        with open(fulfillment_file, 'w') as f:
            json.dump(fulfillment_data, f, indent=2, default=str)
        
        # Update index
        self.fulfillments_index[fulfillment_id] = {
            "order_id": str(fulfillment.order_id),
            "tracking_number": fulfillment.tracking_number,
            "carrier": fulfillment.carrier,
            "status": fulfillment.status,
            "created_at": fulfillment.created_at.isoformat(),
            "file_path": str(fulfillment_file.name)
        }
        self._save_fulfillments_index()
        
        return fulfillment_id
    
    async def get_fulfillment_by_order(self, order_id: str) -> Optional[Fulfillment]:
        """Get fulfillment by order ID."""
        for fulfillment_id, fulfillment_info in self.fulfillments_index.items():
            if fulfillment_info["order_id"] == order_id:
                fulfillment_file = self.fulfillments_dir / fulfillment_info["file_path"]
                if fulfillment_file.exists():
                    with open(fulfillment_file, 'r') as f:
                        fulfillment_data = json.load(f)
                    return Fulfillment(**fulfillment_data)
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        status_counts = {}
        for order_info in self.orders_index.values():
            status = order_info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_orders": len(self.orders_index),
            "total_fulfillments": len(self.fulfillments_index),
            "orders_by_status": status_counts,
            "storage_path": str(self.data_dir.absolute())
        }
    
    async def export_to_airtable_format(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Export all data in Airtable-ready format.
        
        This makes transitioning to Airtable super easy!
        """
        # Orders table
        orders_data = []
        for order_id in self.orders_index:
            order = await self.get_order(order_id)
            if order:
                orders_data.append({
                    "Order ID": str(order.id),
                    "Order Number": order.order_number,
                    "Channel": order.channel,
                    "Status": order.status,
                    "Customer Name": order.customer.full_name,
                    "Customer Email": order.customer.email,
                    "Shipping Address": order.shipping_address.formatted_address,
                    "Total Amount": float(order.total_amount),
                    "Created At": order.created_at.isoformat(),
                    "Channel Order ID": order.channel_order_id,
                    "Tags": ", ".join(order.tags),
                    "Notes": order.notes
                })
        
        # Line Items table
        line_items_data = []
        for order_id in self.orders_index:
            order = await self.get_order(order_id)
            if order:
                for item in order.line_items:
                    line_items_data.append({
                        "Order ID": str(order.id),
                        "Order Number": order.order_number,
                        "SKU": item.sku,
                        "Product Name": item.name,
                        "Quantity": item.quantity,
                        "Price": float(item.price),
                        "Weight (oz)": item.weight_oz
                    })
        
        # Fulfillments table
        fulfillments_data = []
        for fulfillment_id in self.fulfillments_index:
            fulfillment_file = self.fulfillments_dir / self.fulfillments_index[fulfillment_id]["file_path"]
            if fulfillment_file.exists():
                with open(fulfillment_file, 'r') as f:
                    fulfillment_data = json.load(f)
                fulfillment = Fulfillment(**fulfillment_data)
                fulfillments_data.append({
                    "Fulfillment ID": str(fulfillment.id),
                    "Order ID": str(fulfillment.order_id),
                    "Warehouse": fulfillment.warehouse_location,
                    "Carrier": fulfillment.carrier,
                    "Tracking Number": fulfillment.tracking_number,
                    "Status": fulfillment.status,
                    "Shipping Cost": float(fulfillment.shipping_cost) if fulfillment.shipping_cost else 0,
                    "Label URL": fulfillment.label_url,
                    "Packing Slip URL": fulfillment.packing_slip_url,
                    "Created At": fulfillment.created_at.isoformat()
                })
        
        return {
            "Orders": orders_data,
            "Line Items": line_items_data,
            "Fulfillments": fulfillments_data
        }


# Global storage instance
_storage: Optional[SimpleJsonStorage] = None


def get_storage() -> SimpleJsonStorage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = SimpleJsonStorage()
    return _storage