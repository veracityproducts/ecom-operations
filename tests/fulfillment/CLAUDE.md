# Fulfillment Tests

## Test Structure
- `test_unit_shippo.py` - Shippo client unit tests
- `test_unit_webhooks.py` - Webhook handler unit tests
- `test_integration_order_flow.py` - Order processing integration tests
- `test_e2e_fulfillment.py` - Complete fulfillment workflow tests
- `fixtures/` - Test data and mock responses

## Running Tests
```bash
# All fulfillment tests
uv run pytest tests/fulfillment/

# Specific test file
uv run pytest tests/fulfillment/test_unit_shippo.py

# With coverage
uv run pytest tests/fulfillment/ --cov=fulfillment
```