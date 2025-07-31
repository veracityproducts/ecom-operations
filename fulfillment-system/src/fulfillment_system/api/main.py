"""
FastAPI application for Grooved Learning Fulfillment System.

This is the main API entry point following FastAPI best practices
and og-phonics patterns for async API development.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import generate_latest, Counter, Histogram
from pydantic import ValidationError

from ..core.order_processor import OrderProcessor
from ..models.schemas import (
    Order, OrderCreateRequest, OrderResponse, WebhookPayload,
    FulfillmentError
)
from ..services.database import DatabaseService
from ..services.inventory_service import InventoryService
from ..services.document_generator import DocumentGeneratorService
from ..services.shipping_service import ShippingService
from ..utils.config import Settings
from ..utils.metrics import MetricsCollector
from ..utils.exceptions import (
    ProcessingError, InsufficientInventoryError, 
    DocumentGenerationError, ShippingError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('fulfillment_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('fulfillment_request_duration_seconds', 'Request duration')
ORDER_PROCESSING_DURATION = Histogram('order_processing_duration_seconds', 'Order processing time')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting Grooved Learning Fulfillment System")
    
    # Initialize services
    await app.state.database_service.connect()
    await app.state.metrics_collector.initialize()
    
    logger.info("Fulfillment system startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down fulfillment system")
    await app.state.database_service.disconnect()
    logger.info("Fulfillment system shutdown complete")


def create_app(settings: Settings) -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Grooved Learning Fulfillment System",
        description="API-first fulfillment automation with label + packing slip generation",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # Configure middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.allowed_hosts
    )
    
    # Initialize services (will be properly dependency injected in production)
    app.state.settings = settings
    app.state.database_service = DatabaseService(settings.database_url)
    app.state.metrics_collector = MetricsCollector()
    app.state.inventory_service = InventoryService(app.state.database_service)
    app.state.shipping_service = ShippingService(settings)
    app.state.document_service = DocumentGeneratorService(settings.storage_service)
    app.state.order_processor = OrderProcessor(
        app.state.inventory_service,
        app.state.shipping_service,
        app.state.document_service,
        app.state.metrics_collector
    )
    
    return app


# Dependency injection
def get_order_processor(request) -> OrderProcessor:
    """Get order processor instance."""
    return request.app.state.order_processor


def get_metrics_collector(request) -> MetricsCollector:
    """Get metrics collector instance."""
    return request.app.state.metrics_collector


# Initialize app
settings = Settings()
app = create_app(settings)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Grooved Learning Fulfillment System",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    try:
        # Check database connectivity
        db_status = await app.state.database_service.health_check()
        
        return {
            "status": "healthy",
            "database": db_status,
            "services": {
                "order_processor": "operational",
                "document_generator": "operational",
                "inventory_service": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.post("/orders", response_model=OrderResponse)
async def create_order(
    order_request: OrderCreateRequest,
    background_tasks: BackgroundTasks,
    order_processor: OrderProcessor = Depends(get_order_processor)
):
    """
    Create and process new order.
    
    This endpoint receives order data, validates it, and queues it for processing.
    Processing includes inventory allocation, shipping calculation, and document generation.
    """
    REQUEST_COUNT.labels(method="POST", endpoint="/orders").inc()
    
    try:
        # Convert request to internal order model
        order = Order(
            order_number=order_request.order_number,
            channel=order_request.channel,
            customer=order_request.customer,
            shipping_address=order_request.shipping_address,
            billing_address=order_request.billing_address,
            line_items=order_request.line_items,
            subtotal=order_request.subtotal,
            shipping_cost=order_request.shipping_cost,
            tax_amount=order_request.tax_amount,
            total_amount=order_request.total_amount,
            channel_order_id=order_request.channel_order_id,
            notes=order_request.notes,
            tags=order_request.tags
        )
        
        # Process order
        with REQUEST_DURATION.time():
            result = await order_processor.process_order(order)
        
        # Record processing metrics
        ORDER_PROCESSING_DURATION.observe(result['processing_time_ms'] / 1000)
        
        logger.info(f"Order {order.order_number} processed successfully")
        
        return OrderResponse(**result)
        
    except ValidationError as e:
        logger.error(f"Order validation failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=FulfillmentError(
                error_code="VALIDATION_ERROR",
                message="Order data validation failed",
                details={"validation_errors": e.errors()}
            ).dict()
        )
    except InsufficientInventoryError as e:
        logger.error(f"Insufficient inventory: {e}")
        raise HTTPException(
            status_code=409,
            detail=FulfillmentError(
                error_code="INSUFFICIENT_INVENTORY",
                message=str(e),
                details=e.details
            ).dict()
        )
    except (DocumentGenerationError, ShippingError) as e:
        logger.error(f"Fulfillment error: {e}")
        raise HTTPException(
            status_code=500,
            detail=FulfillmentError(
                error_code="FULFILLMENT_ERROR",
                message=str(e),
                details=getattr(e, 'details', None)
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error processing order: {e}")
        raise HTTPException(
            status_code=500,
            detail=FulfillmentError(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"error": str(e)}
            ).dict()
        )


@app.post("/webhooks/shopify")
async def shopify_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    order_processor: OrderProcessor = Depends(get_order_processor)
):
    """
    Handle Shopify Plus webhooks.
    
    Processes order events from Shopify and queues them for fulfillment processing.
    """
    REQUEST_COUNT.labels(method="POST", endpoint="/webhooks/shopify").inc()
    
    try:
        # Verify webhook signature (implementation needed)
        # await verify_shopify_webhook_signature(payload)
        
        if payload.event_type == "orders/create":
            # Transform Shopify order to internal format
            order = await transform_shopify_order(payload.data)
            
            # Queue for background processing
            background_tasks.add_task(
                process_order_background,
                order_processor,
                order
            )
            
            return {"status": "accepted", "order_id": order.id}
            
        elif payload.event_type == "orders/updated":
            # Handle order updates
            return {"status": "processed", "action": "order_updated"}
            
        else:
            logger.warning(f"Unhandled webhook event: {payload.event_type}")
            return {"status": "ignored", "reason": "unsupported_event"}
            
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Webhook processing failed", "details": str(e)}
        )


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order by ID with fulfillment status."""
    REQUEST_COUNT.labels(method="GET", endpoint="/orders/{order_id}").inc()
    
    try:
        # Implementation would fetch from database
        # order = await app.state.database_service.get_order(order_id)
        # return order
        
        return {"order_id": order_id, "status": "not_implemented"}
        
    except Exception as e:
        logger.error(f"Failed to fetch order {order_id}: {e}")
        raise HTTPException(status_code=404, detail="Order not found")


@app.post("/orders/batch")
async def process_batch_orders(
    orders: list[OrderCreateRequest],
    background_tasks: BackgroundTasks,
    order_processor: OrderProcessor = Depends(get_order_processor)
):
    """Process multiple orders in batch."""
    REQUEST_COUNT.labels(method="POST", endpoint="/orders/batch").inc()
    
    try:
        # Convert to internal order models
        internal_orders = []
        for order_request in orders:
            order = Order(
                order_number=order_request.order_number,
                channel=order_request.channel,
                customer=order_request.customer,
                shipping_address=order_request.shipping_address,
                billing_address=order_request.billing_address,
                line_items=order_request.line_items,
                subtotal=order_request.subtotal,
                shipping_cost=order_request.shipping_cost,
                tax_amount=order_request.tax_amount,
                total_amount=order_request.total_amount,
                channel_order_id=order_request.channel_order_id,
                notes=order_request.notes,
                tags=order_request.tags
            )
            internal_orders.append(order)
        
        # Process batch
        results = await order_processor.process_batch(internal_orders)
        
        return {
            "batch_id": "generated_batch_id",
            "total_orders": len(orders),
            "successful": len(results['successful']),
            "failed": len(results['failed']),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Batch processing failed", "details": str(e)}
        )


@app.get("/inventory/{sku}")
async def get_inventory_levels(sku: str):
    """Get inventory levels for SKU across all warehouses."""
    REQUEST_COUNT.labels(method="GET", endpoint="/inventory/{sku}").inc()
    
    try:
        inventory_service = app.state.inventory_service
        levels = await inventory_service.get_inventory_levels(sku)
        
        return {"sku": sku, "inventory_levels": levels}
        
    except Exception as e:
        logger.error(f"Failed to fetch inventory for {sku}: {e}")
        raise HTTPException(status_code=404, detail="SKU not found")


@app.post("/inventory/sync")
async def sync_inventory():
    """Trigger inventory synchronization across all warehouses."""
    REQUEST_COUNT.labels(method="POST", endpoint="/inventory/sync").inc()
    
    try:
        inventory_service = app.state.inventory_service
        result = await inventory_service.sync_all_warehouses()
        
        return {"status": "completed", "synchronized_items": result}
        
    except Exception as e:
        logger.error(f"Inventory sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Inventory sync failed", "details": str(e)}
        )


# Background task functions

async def process_order_background(
    order_processor: OrderProcessor, 
    order: Order
) -> None:
    """Background task for processing orders."""
    try:
        result = await order_processor.process_order(order)
        logger.info(f"Background processing completed for order {order.order_number}")
    except Exception as e:
        logger.error(f"Background processing failed for order {order.order_number}: {e}")


async def transform_shopify_order(shopify_data: Dict[str, Any]) -> Order:
    """Transform Shopify webhook data to internal order model."""
    # Implementation would map Shopify fields to internal model
    # This is a placeholder
    pass


# Custom exception handlers

@app.exception_handler(ProcessingError)
async def processing_error_handler(request, exc: ProcessingError):
    """Handle processing errors."""
    return HTTPException(
        status_code=500,
        detail=FulfillmentError(
            error_code="PROCESSING_ERROR",
            message=str(exc),
            details=getattr(exc, 'details', None)
        ).dict()
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return HTTPException(
        status_code=422,
        detail=FulfillmentError(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()}
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )