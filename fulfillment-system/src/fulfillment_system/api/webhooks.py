"""Webhook endpoints for external integrations."""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from ..integrations.shopify import get_shopify_service
from ..services.shipping_service import get_shipping_service
from ..services.database import DatabaseService
from ..core.order_processor import process_order
from ..utils.config import settings
from ..models.schemas import Fulfillment, OrderStatus, WarehouseLocation


router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# Store processed event IDs to prevent duplicates
# In production, use Redis or database
processed_events = set()


@router.post("/shopify/orders-create")
async def handle_order_create(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Shopify order creation webhook.
    
    This endpoint receives new orders from Shopify and initiates
    the fulfillment process.
    """
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Extract headers
    headers = dict(request.headers)
    
    # Verify webhook authenticity
    shopify_service = get_shopify_service()
    if not shopify_service.verify_webhook(raw_body, headers):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Check for duplicate events
    event_id = headers.get("x-shopify-event-id", "")
    if event_id in processed_events:
        logger.info(f"Duplicate event {event_id} ignored")
        return JSONResponse({"status": "ok", "message": "Duplicate event"})
    
    # Mark event as processed
    processed_events.add(event_id)
    
    # Parse webhook data
    try:
        webhook_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook data: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Add background task to process order
    background_tasks.add_task(
        process_new_order,
        webhook_data,
        headers.get("x-shopify-shop-domain", "")
    )
    
    # Return immediate response to Shopify
    return JSONResponse({"status": "ok", "message": "Order received"})


@router.post("/shopify/orders-updated")
async def handle_order_update(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Shopify order update webhook."""
    # Similar structure to order create
    raw_body = await request.body()
    headers = dict(request.headers)
    
    shopify_service = get_shopify_service()
    if not shopify_service.verify_webhook(raw_body, headers):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    event_id = headers.get("x-shopify-event-id", "")
    if event_id in processed_events:
        return JSONResponse({"status": "ok", "message": "Duplicate event"})
    
    processed_events.add(event_id)
    
    try:
        webhook_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook data: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Process order update
    background_tasks.add_task(
        process_order_update,
        webhook_data,
        headers.get("x-shopify-shop-domain", "")
    )
    
    return JSONResponse({"status": "ok", "message": "Update received"})


@router.post("/shopify/orders-cancelled")
async def handle_order_cancel(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Shopify order cancellation webhook."""
    raw_body = await request.body()
    headers = dict(request.headers)
    
    shopify_service = get_shopify_service()
    if not shopify_service.verify_webhook(raw_body, headers):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    event_id = headers.get("x-shopify-event-id", "")
    if event_id in processed_events:
        return JSONResponse({"status": "ok", "message": "Duplicate event"})
    
    processed_events.add(event_id)
    
    try:
        webhook_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook data: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Process order cancellation
    background_tasks.add_task(
        process_order_cancellation,
        webhook_data,
        headers.get("x-shopify-shop-domain", "")
    )
    
    return JSONResponse({"status": "ok", "message": "Cancellation received"})


async def process_new_order(order_data: Dict[str, Any], shop_domain: str):
    """
    Background task to process new order.
    
    This function:
    1. Converts Shopify order to internal format
    2. Determines optimal warehouse
    3. Generates shipping label and packing slip
    4. Updates Shopify with fulfillment info
    """
    try:
        logger.info(f"Processing new order from {shop_domain}")
        
        # Convert Shopify order to internal format
        shopify_service = get_shopify_service()
        order = shopify_service.process_order_webhook(order_data)
        
        logger.info(f"Processing order {order.order_number} with {len(order.line_items)} items")
        
        # Determine warehouse (simplified for now - use CA)
        # TODO: Implement actual warehouse routing logic
        warehouse = "CA"
        
        # Generate shipping documents
        shipping_service = get_shipping_service()
        shipping_result = await shipping_service.create_shipping_documents(
            order=order,
            from_warehouse=warehouse,
            preferred_carrier=settings.shipping.shippo_preferred_carrier
        )
        
        logger.info(
            f"Generated shipping documents for order {order.order_number}: "
            f"tracking={shipping_result['shipping_label'].tracking_number}"
        )
        
        # Update Shopify with fulfillment information
        success = await shopify_service.mark_order_fulfilled(
            order=order,
            tracking_number=shipping_result['shipping_label'].tracking_number,
            carrier=shipping_result['shipping_label'].carrier
        )
        
        if success:
            logger.info(f"Successfully fulfilled order {order.order_number}")
        else:
            logger.error(f"Failed to update Shopify for order {order.order_number}")
        
        # Save order and fulfillment data to database
        db_service = DatabaseService()
        await db_service.connect()
        
        # Save order
        order_id = await db_service.create_order(order)
        logger.info(f"Saved order {order.order_number} with ID {order_id}")
        
        # Create and save fulfillment record
        fulfillment = Fulfillment(
            order_id=order.id,
            warehouse_location=WarehouseLocation.CALIFORNIA if warehouse == "CA" else WarehouseLocation.PENNSYLVANIA,
            carrier=shipping_result['shipping_label'].carrier,
            service_level=shipping_result['shipping_label'].service_level,
            tracking_number=shipping_result['shipping_label'].tracking_number,
            label_url=shipping_result['shipping_label'].label_url,
            packing_slip_url=shipping_result['packing_slip'].url,
            status=OrderStatus.LABELED,
            shipping_cost=shipping_result['shipping_label'].rate_amount
        )
        
        fulfillment_id = await db_service.create_fulfillment(fulfillment)
        logger.info(f"Created fulfillment record {fulfillment_id}")
        
        await db_service.disconnect()
        
        # TODO: Send confirmation email to customer
        # TODO: Update inventory levels
        
    except Exception as e:
        logger.error(f"Error processing new order: {e}", exc_info=True)
        # TODO: Implement error recovery and alerting


async def process_order_update(order_data: Dict[str, Any], shop_domain: str):
    """Background task to process order updates."""
    try:
        logger.info(f"Processing order update from {shop_domain}")
        
        # Convert order data
        shopify_service = get_shopify_service()
        order = shopify_service.process_order_webhook(order_data)
        
        # TODO: Implement update logic based on what changed
        # - Check if shipping address changed
        # - Check if items were added/removed
        # - Update local database
        
        logger.info(f"Processed update for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Error processing order update: {e}", exc_info=True)


async def process_order_cancellation(order_data: Dict[str, Any], shop_domain: str):
    """Background task to process order cancellations."""
    try:
        logger.info(f"Processing order cancellation from {shop_domain}")
        
        # Convert order data
        shopify_service = get_shopify_service()
        order = shopify_service.process_order_webhook(order_data)
        
        # TODO: Implement cancellation logic
        # - Cancel shipping label if not yet shipped
        # - Update inventory levels
        # - Update local database
        
        logger.info(f"Processed cancellation for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Error processing order cancellation: {e}", exc_info=True)


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhooks."""
    return {
        "status": "healthy",
        "service": "webhooks",
        "shopify_configured": bool(settings.shopify.webhook_secret)
    }