"""
Order processing pipeline following og-phonics modular architecture patterns.

This module implements the core order processing workflow that coordinates
inventory routing, document generation, and fulfillment tracking.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from ..models.schemas import (
    Order, OrderStatus, Fulfillment, ProcessingMetrics,
    WarehouseLocation, CarrierType
)
from ..services.inventory_service import InventoryService
from ..services.document_generator import DocumentGeneratorService
from ..services.shipping_service import ShippingService
from ..utils.metrics import MetricsCollector
from ..utils.exceptions import (
    ProcessingError, InsufficientInventoryError, 
    DocumentGenerationError, ShippingError
)

logger = logging.getLogger(__name__)


class ProcessingStage(ABC):
    """
    Abstract base class for order processing stages.
    
    Following the pipeline pattern from og-phonics for modular, testable components.
    """
    
    @abstractmethod
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process order through this stage.
        
        Args:
            order: Order to process
            context: Processing context from previous stages
            
        Returns:
            Updated context for next stage
            
        Raises:
            ProcessingError: If processing fails
        """
        pass
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Return human-readable stage name for logging."""
        pass


class ValidationStage(ProcessingStage):
    """Validate order data and business rules."""
    
    @property
    def stage_name(self) -> str:
        return "validation"
    
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order meets processing requirements."""
        start_time = datetime.utcnow()
        
        try:
            # Basic data validation (already done by Pydantic)
            if not order.requires_shipping:
                raise ProcessingError("Order contains no shippable items")
            
            # Business rule validation
            if order.total_weight_oz > 1600:  # 100 lbs
                raise ProcessingError("Order exceeds maximum weight limit")
            
            # Educational product specific validation
            await self._validate_educational_products(order)
            
            context['validation'] = {
                'validated_at': start_time,
                'shipping_required': True,
                'weight_oz': order.total_weight_oz
            }
            
            logger.info(f"Order {order.order_number} validated successfully")
            return context
            
        except Exception as e:
            logger.error(f"Validation failed for order {order.order_number}: {e}")
            raise ProcessingError(f"Validation failed: {str(e)}") from e
    
    async def _validate_educational_products(self, order: Order) -> None:
        """Validate educational product specific rules."""
        # Check for valid educational product SKUs
        educational_prefixes = ['CB-', 'CW-', 'EH-', 'SH-']  # Code Breakers, Cursive, etc.
        
        for item in order.line_items:
            if not any(item.sku.startswith(prefix) for prefix in educational_prefixes):
                logger.warning(f"Non-standard SKU pattern: {item.sku}")
        
        # Validate bundle consistency
        bundle_skus = [item.sku for item in order.line_items if '-SET' in item.sku]
        if bundle_skus:
            await self._validate_bundle_items(order, bundle_skus)
    
    async def _validate_bundle_items(self, order: Order, bundle_skus: List[str]) -> None:
        """Validate bundle items are consistent."""
        # Implementation for bundle validation logic
        pass


class InventoryAllocationStage(ProcessingStage):
    """Allocate inventory and select optimal warehouse."""
    
    def __init__(self, inventory_service: InventoryService):
        self.inventory_service = inventory_service
    
    @property
    def stage_name(self) -> str:
        return "inventory_allocation"
    
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate inventory and select warehouse."""
        start_time = datetime.utcnow()
        
        try:
            # Check inventory availability across warehouses
            availability = await self.inventory_service.check_availability(
                [item.sku for item in order.shipping_items]
            )
            
            if not availability['can_fulfill']:
                raise InsufficientInventoryError(
                    f"Insufficient inventory for order {order.order_number}",
                    details=availability['shortfalls']
                )
            
            # Select optimal warehouse
            warehouse = await self.inventory_service.select_optimal_warehouse(
                order.shipping_items,
                order.shipping_address
            )
            
            # Reserve inventory
            reservation_id = await self.inventory_service.reserve_inventory(
                order.shipping_items,
                warehouse,
                order.id
            )
            
            context['inventory_allocation'] = {
                'warehouse': warehouse,
                'reservation_id': reservation_id,
                'allocated_at': start_time,
                'availability_check': availability
            }
            
            logger.info(
                f"Inventory allocated for order {order.order_number} "
                f"at warehouse {warehouse.value}"
            )
            return context
            
        except InsufficientInventoryError:
            raise
        except Exception as e:
            logger.error(f"Inventory allocation failed for order {order.order_number}: {e}")
            raise ProcessingError(f"Inventory allocation failed: {str(e)}") from e


class ShippingCalculationStage(ProcessingStage):
    """Calculate shipping rates and select carrier."""
    
    def __init__(self, shipping_service: ShippingService):
        self.shipping_service = shipping_service
    
    @property
    def stage_name(self) -> str:
        return "shipping_calculation"
    
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate shipping rates and select optimal carrier."""
        start_time = datetime.utcnow()
        
        try:
            warehouse = context['inventory_allocation']['warehouse']
            
            # Get shipping rates from all carriers
            rates = await self.shipping_service.get_shipping_rates(
                order.shipping_items,
                order.shipping_address,
                warehouse
            )
            
            if not rates:
                raise ShippingError("No shipping rates available")
            
            # Select best rate (considering cost and service level)
            selected_rate = await self._select_optimal_rate(rates, order)
            
            context['shipping_calculation'] = {
                'selected_rate': selected_rate,
                'all_rates': rates,
                'calculated_at': start_time
            }
            
            logger.info(
                f"Shipping calculated for order {order.order_number}: "
                f"{selected_rate.carrier.value} {selected_rate.service_level} "
                f"${selected_rate.cost}"
            )
            return context
            
        except Exception as e:
            logger.error(f"Shipping calculation failed for order {order.order_number}: {e}")
            raise ProcessingError(f"Shipping calculation failed: {str(e)}") from e
    
    async def _select_optimal_rate(self, rates: List, order: Order):
        """Select optimal shipping rate based on business rules."""
        # Priority: Cost optimization for educational products
        # But ensure reasonable delivery time
        
        # Filter rates by maximum delivery time (7 days for standard)
        valid_rates = [rate for rate in rates if rate.estimated_days <= 7]
        
        if not valid_rates:
            valid_rates = rates  # Fallback to all rates
        
        # Sort by cost, select cheapest
        valid_rates.sort(key=lambda r: r.cost)
        return valid_rates[0]


class DocumentGenerationStage(ProcessingStage):
    """Generate shipping labels and packing slips."""
    
    def __init__(self, document_service: DocumentGeneratorService):
        self.document_service = document_service
    
    @property
    def stage_name(self) -> str:
        return "document_generation"
    
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate shipping documents."""
        start_time = datetime.utcnow()
        
        try:
            shipping_rate = context['shipping_calculation']['selected_rate']
            warehouse = context['inventory_allocation']['warehouse']
            
            # Generate documents concurrently
            documents = await self.document_service.generate_fulfillment_documents(
                order,
                shipping_rate,
                warehouse
            )
            
            context['document_generation'] = {
                'documents': documents,
                'generated_at': start_time
            }
            
            logger.info(
                f"Documents generated for order {order.order_number}: "
                f"label_url={documents.get('label_url')}, "
                f"packing_slip_url={documents.get('packing_slip_url')}"
            )
            return context
            
        except Exception as e:
            logger.error(f"Document generation failed for order {order.order_number}: {e}")
            raise DocumentGenerationError(f"Document generation failed: {str(e)}") from e


class FulfillmentCreationStage(ProcessingStage):
    """Create fulfillment record and update order status."""
    
    @property
    def stage_name(self) -> str:
        return "fulfillment_creation"
    
    async def process(self, order: Order, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fulfillment record."""
        start_time = datetime.utcnow()
        
        try:
            # Extract data from context
            warehouse = context['inventory_allocation']['warehouse']
            shipping_rate = context['shipping_calculation']['selected_rate']
            documents = context['document_generation']['documents']
            
            # Create fulfillment record
            fulfillment = Fulfillment(
                order_id=order.id,
                warehouse_location=warehouse,
                carrier=shipping_rate.carrier,
                service_level=shipping_rate.service_level,
                tracking_number=documents.get('tracking_number'),
                label_url=documents.get('label_url'),
                packing_slip_url=documents.get('packing_slip_url'),
                shipping_cost=shipping_rate.cost,
                status=OrderStatus.LABELED
            )
            
            context['fulfillment'] = fulfillment
            context['fulfillment_creation'] = {
                'created_at': start_time,
                'fulfillment_id': fulfillment.id
            }
            
            logger.info(f"Fulfillment created for order {order.order_number}")
            return context
            
        except Exception as e:
            logger.error(f"Fulfillment creation failed for order {order.order_number}: {e}")
            raise ProcessingError(f"Fulfillment creation failed: {str(e)}") from e


class OrderProcessor:
    """
    Main order processing orchestrator.
    
    Implements the pipeline pattern from og-phonics with comprehensive error handling
    and performance monitoring.
    """
    
    def __init__(
        self,
        inventory_service: InventoryService,
        shipping_service: ShippingService,
        document_service: DocumentGeneratorService,
        metrics_collector: MetricsCollector
    ):
        self.inventory_service = inventory_service
        self.shipping_service = shipping_service
        self.document_service = document_service
        self.metrics_collector = metrics_collector
        
        # Initialize processing pipeline
        self.stages = [
            ValidationStage(),
            InventoryAllocationStage(inventory_service),
            ShippingCalculationStage(shipping_service),
            DocumentGenerationStage(document_service),
            FulfillmentCreationStage()
        ]
    
    async def process_order(self, order: Order) -> Dict[str, Any]:
        """
        Process order through entire fulfillment pipeline.
        
        Args:
            order: Order to process
            
        Returns:
            Processing results including fulfillment data
            
        Raises:
            ProcessingError: If any stage fails after retries
        """
        overall_start = datetime.utcnow()
        context = {'order': order}
        
        try:
            # Process through each stage
            for stage in self.stages:
                stage_start = datetime.utcnow()
                
                try:
                    context = await stage.process(order, context)
                    
                    # Record stage metrics
                    stage_duration = (datetime.utcnow() - stage_start).total_seconds() * 1000
                    await self._record_stage_metrics(
                        order.id, stage.stage_name, stage_duration, True
                    )
                    
                except Exception as e:
                    # Record failure metrics
                    stage_duration = (datetime.utcnow() - stage_start).total_seconds() * 1000
                    await self._record_stage_metrics(
                        order.id, stage.stage_name, stage_duration, False, str(e)
                    )
                    
                    # Attempt cleanup for failed processing
                    await self._cleanup_failed_processing(order, context, stage.stage_name)
                    raise
            
            # Update order status
            order.status = OrderStatus.LABELED
            order.updated_at = datetime.utcnow()
            
            # Record overall processing time
            total_duration = (datetime.utcnow() - overall_start).total_seconds() * 1000
            await self.metrics_collector.record_order_processing(
                order.id, total_duration, True
            )
            
            logger.info(
                f"Order {order.order_number} processed successfully in {total_duration:.0f}ms"
            )
            
            return {
                'order': order,
                'fulfillment': context.get('fulfillment'),
                'processing_time_ms': int(total_duration),
                'context': context
            }
            
        except Exception as e:
            # Record overall failure metrics
            total_duration = (datetime.utcnow() - overall_start).total_seconds() * 1000
            await self.metrics_collector.record_order_processing(
                order.id, total_duration, False, str(e)
            )
            
            logger.error(
                f"Order {order.order_number} processing failed after {total_duration:.0f}ms: {e}"
            )
            
            # Update order status to error
            order.status = OrderStatus.ERROR
            order.updated_at = datetime.utcnow()
            
            raise ProcessingError(
                f"Order processing failed: {str(e)}",
                details={'order_id': str(order.id), 'stage_context': context}
            ) from e
    
    async def _record_stage_metrics(
        self, 
        order_id: UUID, 
        stage: str, 
        duration_ms: float,
        success: bool, 
        error_message: Optional[str] = None
    ) -> None:
        """Record processing metrics for a stage."""
        metrics = ProcessingMetrics(
            order_id=order_id,
            stage=stage,
            processing_time_ms=int(duration_ms),
            success=success,
            error_message=error_message
        )
        
        await self.metrics_collector.record_stage_metrics(metrics)
    
    async def _cleanup_failed_processing(
        self, 
        order: Order, 
        context: Dict[str, Any], 
        failed_stage: str
    ) -> None:
        """Clean up resources after processing failure."""
        try:
            # Release inventory reservation if it was made
            if 'inventory_allocation' in context:
                reservation_id = context['inventory_allocation'].get('reservation_id')
                if reservation_id:
                    await self.inventory_service.release_reservation(reservation_id)
                    logger.info(f"Released inventory reservation {reservation_id}")
            
            # Additional cleanup based on failed stage
            if failed_stage == 'document_generation':
                # Clean up any partial document generation
                pass
                
        except Exception as cleanup_error:
            logger.error(f"Cleanup failed for order {order.order_number}: {cleanup_error}")
    
    async def process_batch(self, orders: List[Order]) -> List[Dict[str, Any]]:
        """
        Process multiple orders concurrently.
        
        Args:
            orders: List of orders to process
            
        Returns:
            List of processing results
        """
        logger.info(f"Starting batch processing of {len(orders)} orders")
        
        # Process orders concurrently with semaphore to control concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent processing
        
        async def process_with_semaphore(order: Order):
            async with semaphore:
                return await self.process_order(order)
        
        tasks = [process_with_semaphore(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({
                    'order': orders[i],
                    'error': str(result),
                    'exception': result
                })
            else:
                successful.append(result)
        
        logger.info(
            f"Batch processing completed: {len(successful)} successful, {len(failed)} failed"
        )
        
        return {
            'successful': successful,
            'failed': failed,
            'total_processed': len(orders)
        }