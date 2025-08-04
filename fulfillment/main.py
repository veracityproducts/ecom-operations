#!/usr/bin/env python3
"""
Production FastAPI server for Grooved Learning Fulfillment.

Follows proven patterns from og-phonics and science-reading-rag projects.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from fulfillment.utils.config import Settings
from fulfillment.shopify.webhook_handler import ShopifyWebhookHandler, ShopifyOrder
from fulfillment.shopify.client import ShopifyClient
from fulfillment.shippo.client import ShippoService, ShippoAddress, ShippoParcel, ShippoOrder

# Configure logging following our patterns
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Data storage directory
project_root = Path(__file__).parent.parent
ORDERS_DIR = project_root / "data" / "orders"
ORDERS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting up fulfillment service...")
    app.state.settings = settings
    app.state.webhook_handler = ShopifyWebhookHandler(settings)
    app.state.shippo_service = ShippoService(
        api_token=settings.shippo_token,
        test_mode=settings.shippo_test_mode,
        rate_limit_tier="standard"
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down fulfillment service...")
    # Cleanup handled by context managers


# Initialize FastAPI app with proper lifecycle management
app = FastAPI(
    title="Grooved Learning Fulfillment API",
    description="Production fulfillment system for educational products",
    version="1.0.0",
    lifespan=lifespan
)
    

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Grooved Learning Fulfillment",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health():
    """Detailed health check with service dependencies."""
    checks = {
        "api": "ok",
        "shippo_configured": bool(settings.shippo_token),
        "shopify_configured": bool(settings.shopify_webhook_secret and settings.shopify_access_token),
        "storage": ORDERS_DIR.exists(),
        "config_loaded": settings is not None
    }
    
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "checks": checks,
        "environment": "test" if settings.use_test_mode else "production",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhooks/shopify/order-create")
async def handle_order_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Shopify order creation webhook with proper validation."""
    try:
        # Parse and validate webhook using our handler
        webhook_handler: ShopifyWebhookHandler = app.state.webhook_handler
        shopify_order = await webhook_handler.parse_order_webhook(request)
        
        # Check if order should be processed
        if not webhook_handler.should_process_order(shopify_order):
            return {
                "status": "skipped",
                "order_id": shopify_order.id,
                "order_number": shopify_order.order_number,
                "reason": "Order not eligible for fulfillment"
            }
        
        # Save order data to file for tracking
        order_file = ORDERS_DIR / f"order_{shopify_order.id}.json"
        with open(order_file, "w") as f:
            f.write(shopify_order.model_dump_json(indent=2))
        
        # Process in background following our patterns
        background_tasks.add_task(process_order_fulfillment, shopify_order)
        
        return {
            "status": "accepted",
            "order_id": shopify_order.id,
            "order_number": shopify_order.order_number,
            "message": "Order webhook received and queued for processing"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, auth errors)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing webhook"
        )


async def process_order_fulfillment(shopify_order: ShopifyOrder):
    """
    Process order fulfillment using modular services.
    Follows error handling patterns from og-phonics project.
    """
    logger.info(f"Processing fulfillment for order {shopify_order.order_number}")
    
    try:
        # Get services from app state
        webhook_handler: ShopifyWebhookHandler = app.state.webhook_handler
        shippo_service: ShippoService = app.state.shippo_service
        
        # Extract shipping information
        shipping_info = webhook_handler.extract_shipping_info(shopify_order)
        to_address = ShippoAddress(**shipping_info)
        
        # Use configured warehouse address
        from_address = ShippoAddress(**settings.warehouse_ca_address)
        
        # Calculate package weight from line items
        package_weight = webhook_handler.calculate_package_weight(shopify_order)
        
        # Create parcel (simplified dimensions for now)
        parcel = ShippoParcel(
            length=10.0,
            width=8.0,
            height=4.0,
            weight=package_weight,
            distance_unit="in",
            mass_unit="lb"
        )
        
        # Convert to Shippo order format
        shippo_order = ShippoOrder(
            order_number=shopify_order.order_number,
            to_address=to_address,
            from_address=from_address,
            line_items=[
                {
                    "title": item.get("name", ""),
                    "quantity": item.get("quantity", 1),
                    "total_price": item.get("price", "0.00"),
                    "currency": shopify_order.currency,
                    "sku": item.get("sku", "")
                }
                for item in shopify_order.line_items
            ],
            placed_at=datetime.fromisoformat(shopify_order.created_at.replace('Z', '+00:00'))
        )
        
        # Create shipping label (skip packing slip for now to simplify)
        label_result = await shippo_service.get_rates_and_create_label(
            from_address=from_address,
            to_address=to_address,
            parcel=parcel,
            preferred_carrier=None  # Use cheapest rate
        )
        
        # Get tracking info
        tracking_number = label_result.tracking_number or f"TEST{shopify_order.id}"
        carrier = getattr(label_result, 'rate_details', {}).get('provider', 'USPS')
        
        # Map to Shopify carrier format
        carrier_mapping = {
            "usps": "USPS",
            "ups": "UPS",
            "fedex": "FedEx",
            "dhl_express": "DHL Express",
        }
        tracking_company = carrier_mapping.get(carrier.lower(), "Other")
        
        # Update Shopify with fulfillment
        shopify_client = ShopifyClient(
            shop_domain=settings.shopify_shop_domain,
            access_token=settings.shopify_access_token,
            api_version=settings.shopify_api_version
        )
        
        async with shopify_client:
            fulfillment = await shopify_client.update_order_fulfillment(
                order_id=shopify_order.id,
                fulfillment_data={
                    "tracking_number": tracking_number,
                    "tracking_company": tracking_company,
                    "notify_customer": True
                }
            )
        
        # Prepare result
        result = {
            "order_id": shopify_order.id,
            "order_name": shopify_order.order_number,
            "fulfillment_id": fulfillment["id"],
            "label": {
                "url": label_result.label_url or "N/A",
                "tracking_number": tracking_number,
                "carrier": tracking_company,
                "cost": getattr(label_result, 'rate_details', {}).get('amount', '0.00')
            },
            "shopify_fulfillment": {
                "id": fulfillment["id"],
                "status": fulfillment["status"]
            },
            "created_at": datetime.now().isoformat()
        }
        
        # Save fulfillment result
        fulfillment_file = ORDERS_DIR / f"fulfillment_{shopify_order.id}.json"
        with open(fulfillment_file, "w") as f:
            import json
            json.dump(result, f, indent=2)
        
        logger.info(
            f"✅ Fulfillment completed for order {shopify_order.order_number}: "
            f"Tracking: {tracking_number}, "
            f"Shopify Fulfillment: {fulfillment['id']}"
        )
        
    except ValueError as e:
        logger.error(f"Validation error processing order {shopify_order.order_number}: {e}")
    except Exception as e:
        logger.error(f"Failed to process order {shopify_order.order_number}: {e}")
        # In production, this would trigger alerting/retry mechanisms


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details with fulfillment status."""
    order_file = ORDERS_DIR / f"order_{order_id}.json"
    if not order_file.exists():
        raise HTTPException(status_code=404, detail="Order not found")
        
    with open(order_file) as f:
        import json
        order = json.load(f)
        
    # Check for fulfillment data
    fulfillment_file = ORDERS_DIR / f"fulfillment_{order_id}.json"
    if fulfillment_file.exists():
        with open(fulfillment_file) as f:
            order["fulfillment"] = json.load(f)
    else:
        # Check for legacy label data
        label_file = ORDERS_DIR / f"label_{order_id}.json"
        if label_file.exists():
            with open(label_file) as f:
                order["legacy_fulfillment"] = json.load(f)
            
    return order


@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str):
    """Get simplified order fulfillment status."""
    fulfillment_file = ORDERS_DIR / f"fulfillment_{order_id}.json"
    
    if not fulfillment_file.exists():
        return {
            "order_id": order_id,
            "status": "pending",
            "message": "Order not yet processed"
        }
    
    with open(fulfillment_file) as f:
        import json
        fulfillment = json.load(f)
    
    return {
        "order_id": order_id,
        "status": "fulfilled",
        "tracking_number": fulfillment["label"]["tracking_number"],
        "carrier": fulfillment["label"]["carrier"],
        "label_url": fulfillment["label"]["url"],
        "packing_slip_url": fulfillment["packing_slip"]["url"],
        "total_cost": fulfillment["total_cost"],
        "created_at": fulfillment["created_at"]
    }


@app.post("/test/order-webhook")
async def test_order_webhook(order_data: dict, background_tasks: BackgroundTasks):
    """Test endpoint for order webhooks without signature verification."""
    if not settings.use_test_mode:
        raise HTTPException(
            status_code=403,
            detail="Test endpoint only available in test mode"
        )
    
    try:
        # Parse directly without signature verification
        shopify_order = ShopifyOrder(**order_data)
        
        # Check if order should be processed
        webhook_handler: ShopifyWebhookHandler = app.state.webhook_handler
        if not webhook_handler.should_process_order(shopify_order):
            return {
                "status": "skipped",
                "order_id": shopify_order.id,
                "order_number": shopify_order.order_number,
                "reason": "Order not eligible for fulfillment"
            }
        
        # Save order data to file for tracking
        order_file = ORDERS_DIR / f"order_{shopify_order.id}.json"
        with open(order_file, "w") as f:
            f.write(shopify_order.model_dump_json(indent=2))
        
        # Process in background
        background_tasks.add_task(process_order_fulfillment, shopify_order)
        
        return {
            "status": "received",
            "order_id": shopify_order.id,
            "order_number": shopify_order.order_number,
            "message": "Test order webhook received and queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Test webhook error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test webhook processing error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fulfillment.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )