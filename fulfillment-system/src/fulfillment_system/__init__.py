"""
Grooved Learning Fulfillment System

A comprehensive Python-based fulfillment automation platform that generates 
shipping labels AND packing slips programmatically, supporting multi-warehouse 
operations at scale.

Key Features:
- API-first architecture bypassing ShipStation packing slip limitations
- Multi-warehouse intelligent routing (CA, PA, Amazon FBA)
- Real-time Shopify Plus integration
- Automated document generation (labels + packing slips)
- Scalable to 500+ orders/day during peak season
"""

__version__ = "0.1.0"
__author__ = "Grooved Learning"
__email__ = "tech@groovedlearning.com"

# Export main components
from .core.order_processor import OrderProcessor
from .core.inventory_router import InventoryRouter
from .services.document_generator import DocumentGeneratorService
from .integrations.shopify_client import ShopifyClient

__all__ = [
    "OrderProcessor",
    "InventoryRouter", 
    "DocumentGeneratorService",
    "ShopifyClient",
]