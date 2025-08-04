# Grooved Learning Fulfillment Module

Clean, simple fulfillment system that generates shipping labels AND packing slips.

## Quick Start

1. **Start the server:**
   ```bash
   cd fulfillment && uv run uvicorn main:app --reload
   ```
   Or use the helper script from project root:
   ```bash
   ./run_fulfillment.sh
   ```

2. **View API docs:**
   http://localhost:8750/docs

3. **Test the API:**
   ```bash
   uv run python scripts/automation/test_fulfillment_api.py
   # Or test webhook:
   uv run python scripts/fulfillment/test_webhook.py
   ```

## Features

- ✅ Shopify webhook integration
- ✅ Shippo API for labels + packing slips ($0.05/label)
- ✅ Simple JSON file storage (data/orders/)
- ✅ Clean, modular structure

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /webhooks/shopify/order-create` - Receive Shopify orders
- `GET /orders/{order_id}` - Get order details with fulfillment status

## Environment Variables

Uses `.env` from project root:
- `SHIPPING_SHIPPO_TEST_API_TOKEN` - Shippo test API key
- `SHOPIFY_WEBHOOK_SECRET` - For webhook verification
- `SHOPIFY_ACCESS_TOKEN` - For updating order fulfillment
- `WAREHOUSE_CA_*` - California warehouse address

## Next Steps

1. Add webhook signature verification
2. Update Shopify with tracking numbers
3. Generate PDF packing slips
4. Add PostgreSQL for production