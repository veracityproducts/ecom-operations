# Tests Directory Organization

## Structure
- `fulfillment/` - Tests for fulfillment module
- `inventory/` - Tests for inventory module  
- `analytics/` - Tests for analytics module
- `shared/` - Shared test utilities and fixtures

## Test Types
- `test_unit_*.py` - Unit tests for individual functions
- `test_integration_*.py` - Integration tests between components
- `test_e2e_*.py` - End-to-end workflow tests
- `conftest.py` - Pytest fixtures and configuration

## Rules
- Mirror the module structure exactly
- Use descriptive test names that explain what's being tested
- Each test file should be self-contained
- Run tests with: `uv run pytest tests/`