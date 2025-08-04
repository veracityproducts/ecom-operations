# Fulfillment Scripts

## Scripts
- `test_webhook.py` - Test Shopify webhook locally
- `setup_webhook.py` - Register webhook with Shopify
- `sync_orders.py` - Pull historical orders from Shopify
- `test_shippo_api.py` - Test Shippo API connection
- `analyze_shipping_costs.py` - Analyze potential savings

## Usage
All scripts run from project root:
```bash
uv run python scripts/fulfillment/test_webhook.py
```