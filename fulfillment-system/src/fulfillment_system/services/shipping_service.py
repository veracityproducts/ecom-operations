"""Shipping service factory for managing carrier integrations."""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..integrations.shippo import (
    ShippoService,
    ShippoOrder,
    ShippoAddress,
    ShippoParcel
)
from ..utils.config import settings
from ..models.schemas import Order, ShippingLabel, PackingSlip, LineItem


class ShippingService:
    """Main shipping service that orchestrates label and packing slip generation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_shippo_service()
    
    def _init_shippo_service(self):
        """Initialize Shippo service with configuration."""
        api_token = (
            settings.shipping.shippo_api_token 
            if settings.is_production 
            else settings.shipping.shippo_test_api_token or settings.shipping.shippo_api_token
        )
        
        self.shippo = ShippoService(
            api_token=api_token,
            rate_limit_tier=settings.shipping.shippo_rate_limit_tier
        )
        
        self.logger.info(
            f"Initialized Shippo service (environment: {settings.environment}, "
            f"rate_limit_tier: {settings.shipping.shippo_rate_limit_tier})"
        )
    
    async def create_shipping_documents(
        self,
        order: Order,
        from_warehouse: str = "CA",
        preferred_carrier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create shipping label and packing slip for an order.
        
        Args:
            order: Order object with customer and product information
            from_warehouse: Warehouse code (CA or PA)
            preferred_carrier: Optional preferred carrier override
            
        Returns:
            Dictionary containing label and packing slip information
        """
        try:
            # Convert order to Shippo format
            shippo_order = self._convert_to_shippo_order(order, from_warehouse)
            
            # Calculate package dimensions based on products
            parcel = self._calculate_parcel_dimensions(order)
            
            # Use configured preferred carrier if not specified
            if not preferred_carrier:
                preferred_carrier = settings.shipping.shippo_preferred_carrier
            
            # Generate label and packing slip
            result = await self.shippo.create_combined_label_and_packing_slip(
                order=shippo_order,
                parcel=parcel,
                preferred_carrier=preferred_carrier
            )
            
            # Log success
            self.logger.info(
                f"Successfully created shipping documents for order {order.order_number}: "
                f"tracking={result['label']['tracking_number']}, "
                f"cost=${result['total_cost']:.2f}"
            )
            
            # Convert to internal format
            return self._format_shipping_result(result, order)
            
        except Exception as e:
            self.logger.error(
                f"Failed to create shipping documents for order {order.order_number}: {e}"
            )
            raise
    
    def _convert_to_shippo_order(self, order: Order, from_warehouse: str) -> ShippoOrder:
        """Convert internal order to Shippo order format."""
        # Get warehouse address
        from_address = self._get_warehouse_address(from_warehouse)
        
        # Convert customer address
        to_address = ShippoAddress(
            name=order.customer.full_name,
            street1=order.shipping_address.address1,
            street2=order.shipping_address.address2,
            city=order.shipping_address.city,
            state=order.shipping_address.state,
            zip=order.shipping_address.postal_code,
            country=order.shipping_address.country or "US",
            phone=order.customer.phone,
            email=order.customer.email
        )
        
        # Convert line items
        line_items = []
        for item in order.line_items:
            line_items.append({
                "title": item.name,
                "quantity": item.quantity,
                "sku": item.sku,
                "weight": str(item.weight_oz / 16.0) if item.weight_oz else "0.1",  # Convert oz to lb
                "weight_unit": "lb"
            })
        
        return ShippoOrder(
            order_number=order.order_number,
            to_address=to_address,
            from_address=from_address,
            line_items=line_items,
            placed_at=order.created_at
        )
    
    def _get_warehouse_address(self, warehouse_code: str) -> ShippoAddress:
        """Get warehouse address from configuration."""
        if warehouse_code.upper() == "PA":
            return ShippoAddress(
                name=settings.warehouse.pa_name,
                street1=settings.warehouse.pa_address1,
                city=settings.warehouse.pa_city,
                state=settings.warehouse.pa_state,
                zip=settings.warehouse.pa_postal_code,
                phone=settings.warehouse.pa_phone or "555-000-0000",
                email="shipping@groovedlearning.com"
            )
        else:  # Default to CA
            return ShippoAddress(
                name=settings.warehouse.ca_name,
                street1=settings.warehouse.ca_address1,
                city=settings.warehouse.ca_city,
                state=settings.warehouse.ca_state,
                zip=settings.warehouse.ca_postal_code,
                phone=settings.warehouse.ca_phone or "555-000-0000",
                email="shipping@groovedlearning.com"
            )
    
    def _calculate_parcel_dimensions(self, order: Order) -> ShippoParcel:
        """
        Calculate optimal parcel dimensions based on order items.
        
        This is a simplified implementation. In production, you would:
        1. Look up actual product dimensions from database
        2. Use bin packing algorithms for multi-item orders
        3. Consider special packaging requirements
        """
        # Calculate total weight (convert from oz to lb)
        total_weight = sum((item.weight_oz or 0) * item.quantity for item in order.line_items) / 16.0
        
        # For now, use standard box sizes based on weight
        # This should be replaced with actual product-based logic
        if total_weight <= 1.0:
            # Small envelope/box
            return ShippoParcel(
                length=10.0,
                width=7.0,
                height=1.0,
                weight=total_weight
            )
        elif total_weight <= 5.0:
            # Medium box
            return ShippoParcel(
                length=12.0,
                width=9.0,
                height=3.0,
                weight=total_weight
            )
        elif total_weight <= 15.0:
            # Large box
            return ShippoParcel(
                length=16.0,
                width=12.0,
                height=6.0,
                weight=total_weight
            )
        else:
            # Extra large box
            return ShippoParcel(
                length=20.0,
                width=16.0,
                height=10.0,
                weight=total_weight
            )
    
    def _format_shipping_result(
        self, 
        shippo_result: Dict[str, Any], 
        order: Order
    ) -> Dict[str, Any]:
        """Format Shippo result to internal structure."""
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "shippo_order_id": shippo_result["order_id"],
            "shipping_label": ShippingLabel(
                tracking_number=shippo_result["label"]["tracking_number"],
                carrier=shippo_result["label"]["carrier"],
                service_level="ground",  # TODO: Extract from rate
                label_url=shippo_result["label"]["url"],
                rate_amount=float(shippo_result["label"]["rate_amount"]),
                created_at=datetime.fromisoformat(shippo_result["created_at"])
            ),
            "packing_slip": PackingSlip(
                url=shippo_result["packing_slip"]["url"],
                expires_at=datetime.fromisoformat(shippo_result["packing_slip"]["expires_at"]),
                format="PDF"
            ),
            "total_cost": shippo_result["total_cost"],
            "created_at": shippo_result["created_at"]
        }
    
    async def get_shipping_rates(
        self,
        order: Order,
        from_warehouse: str = "CA"
    ) -> List[Dict[str, Any]]:
        """
        Get available shipping rates for an order.
        
        This can be used for rate shopping or displaying options to customers.
        """
        # Implementation would call Shippo's rate shopping API
        # For now, this is a placeholder
        raise NotImplementedError("Rate shopping not yet implemented")
    
    async def track_shipment(self, tracking_number: str, carrier: str) -> Dict[str, Any]:
        """
        Get tracking information for a shipment.
        
        This would integrate with Shippo's tracking API.
        """
        # Implementation would call Shippo's tracking API
        # For now, this is a placeholder
        raise NotImplementedError("Shipment tracking not yet implemented")


# Global shipping service instance
_shipping_service: Optional[ShippingService] = None


def get_shipping_service() -> ShippingService:
    """Get or create shipping service instance (singleton pattern)."""
    global _shipping_service
    if _shipping_service is None:
        _shipping_service = ShippingService()
    return _shipping_service