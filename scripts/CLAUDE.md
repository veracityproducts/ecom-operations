# Scripts Directory Organization

## Structure
- `fulfillment/` - Fulfillment-related scripts
- `inventory/` - Inventory management scripts
- `analytics/` - Data analysis and reporting scripts
- `automation/` - Cross-module automation scripts
- `utilities/` - Helper scripts and tools

## Script Types
- `setup_*.py` - One-time setup scripts
- `sync_*.py` - Data synchronization scripts
- `analyze_*.py` - Analysis and reporting scripts
- `test_*.py` - Manual testing scripts
- `migrate_*.py` - Data migration scripts

## Rules
- Scripts should be runnable from project root
- Include help text and examples in docstrings
- Use environment variables from root .env
- Make executable with proper shebang line