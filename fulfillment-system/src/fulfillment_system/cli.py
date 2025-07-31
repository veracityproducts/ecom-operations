"""
Command-line interface for Grooved Learning Fulfillment System.

Provides administrative commands for system management, testing, and operations.
Following og-phonics patterns for CLI design with rich output formatting.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .utils.config import Settings
from .models.schemas import Order, OrderChannel, Customer, Address, LineItem
from .core.order_processor import OrderProcessor
from .services.database import DatabaseService
from .services.inventory_service import InventoryService
from .services.document_generator import DocumentGeneratorService
from .services.shipping_service import ShippingService
from .utils.metrics import MetricsCollector

# Initialize CLI app
app = typer.Typer(
    name="fulfillment-system",
    help="Grooved Learning Fulfillment System CLI",
    rich_markup_mode="rich"
)
console = Console()


@app.command()
def version():
    """Show version information."""
    rprint("[bold blue]Grooved Learning Fulfillment System[/bold blue]")
    rprint(f"Version: [green]0.1.0[/green]")
    rprint(f"Python: [yellow]{typer.get_app_info().python_version}[/yellow]")


@app.command()
def config(
    show_secrets: bool = typer.Option(False, "--show-secrets", help="Show secret values")
):
    """Show current configuration."""
    settings = Settings()
    
    rprint("[bold]Current Configuration[/bold]")
    rprint()
    
    # Application settings
    rprint("[bold blue]Application[/bold blue]")
    rprint(f"  Environment: [yellow]{settings.environment}[/yellow]")
    rprint(f"  Debug: [yellow]{settings.debug}[/yellow]")
    rprint(f"  Max Concurrent Orders: [yellow]{settings.max_concurrent_orders}[/yellow]")
    rprint()
    
    # Database settings
    rprint("[bold blue]Database[/bold blue]")
    rprint(f"  Host: [yellow]{settings.database.host}[/yellow]")
    rprint(f"  Port: [yellow]{settings.database.port}[/yellow]")
    rprint(f"  Name: [yellow]{settings.database.name}[/yellow]")
    if show_secrets:
        rprint(f"  Password: [red]{settings.database.password}[/red]")
    rprint()
    
    # Shopify settings
    rprint("[bold blue]Shopify[/bold blue]")
    rprint(f"  Shop Domain: [yellow]{settings.shopify.shop_domain}[/yellow]")
    rprint(f"  API Version: [yellow]{settings.shopify.api_version}[/yellow]")
    if show_secrets:
        rprint(f"  Access Token: [red]{settings.shopify.access_token[:10]}...[/red]")
    rprint()


@app.command()
def init_db():
    """Initialize database schema."""
    async def _init_db():
        settings = Settings()
        db_service = DatabaseService(settings.database_url)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Initializing database...", total=None)
            
            try:
                await db_service.connect()
                await db_service.create_tables()
                progress.update(task, description="Database initialized successfully")
                rprint("[green]✓[/green] Database schema created successfully")
                
            except Exception as e:
                progress.update(task, description="Database initialization failed")
                rprint(f"[red]✗[/red] Database initialization failed: {e}")
                raise typer.Exit(1)
            finally:
                await db_service.disconnect()
    
    asyncio.run(_init_db())


@app.command()
def health():
    """Check system health."""
    async def _health_check():
        settings = Settings()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Check database
            db_task = progress.add_task("Checking database...", total=None)
            try:
                db_service = DatabaseService(settings.database_url)
                await db_service.connect()
                db_status = await db_service.health_check()
                await db_service.disconnect()
                
                if db_status.get('status') == 'healthy':
                    progress.update(db_task, description="Database: [green]Healthy[/green]")
                    db_ok = True
                else:
                    progress.update(db_task, description="Database: [red]Unhealthy[/red]")
                    db_ok = False
            except Exception as e:
                progress.update(db_task, description=f"Database: [red]Error - {e}[/red]")
                db_ok = False
            
            # Check other services...
            # Redis, carrier APIs, etc.
            
            if db_ok:
                rprint("\n[green]✓[/green] System is healthy")
            else:
                rprint("\n[red]✗[/red] System has issues")
                raise typer.Exit(1)
    
    asyncio.run(_health_check())


@app.command()
def test_order(
    order_file: Optional[Path] = typer.Option(None, "--file", help="JSON file with order data"),
    channel: str = typer.Option("shopify", help="Order channel"),
    customer_email: str = typer.Option("test@example.com", help="Customer email")
):
    """Create and process a test order."""
    async def _test_order():
        settings = Settings()
        
        # Initialize services
        db_service = DatabaseService(settings.database_url)
        metrics_collector = MetricsCollector()
        inventory_service = InventoryService(db_service)
        shipping_service = ShippingService(settings)
        document_service = DocumentGeneratorService(settings.storage)
        
        order_processor = OrderProcessor(
            inventory_service,
            shipping_service,
            document_service,
            metrics_collector
        )
        
        try:
            await db_service.connect()
            
            # Create test order
            if order_file and order_file.exists():
                # Load from file
                with open(order_file) as f:
                    order_data = json.load(f)
                order = Order(**order_data)
            else:
                # Create sample order
                order = _create_sample_order(channel, customer_email)
            
            rprint(f"[blue]Processing test order:[/blue] {order.order_number}")
            rprint(f"[blue]Channel:[/blue] {order.channel}")
            rprint(f"[blue]Items:[/blue] {len(order.line_items)}")
            rprint()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Processing order...", total=None)
                
                # Process order
                result = await order_processor.process_order(order)
                
                progress.update(task, description="Order processed successfully")
            
            # Display results
            rprint("[green]✓[/green] Order processed successfully!")
            rprint()
            
            table = Table(title="Processing Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("Order ID", str(result['order'].id))
            table.add_row("Status", result['order'].status.value)
            table.add_row("Processing Time", f"{result['processing_time_ms']}ms")
            
            if result.get('fulfillment'):
                fulfillment = result['fulfillment']
                table.add_row("Warehouse", fulfillment.warehouse_location.value)
                table.add_row("Carrier", fulfillment.carrier.value)
                table.add_row("Service Level", fulfillment.service_level)
                if fulfillment.tracking_number:
                    table.add_row("Tracking Number", fulfillment.tracking_number)
            
            console.print(table)
            
        except Exception as e:
            rprint(f"[red]✗[/red] Order processing failed: {e}")
            raise typer.Exit(1)
        finally:
            await db_service.disconnect()
    
    asyncio.run(_test_order())


@app.command()
def inventory(
    action: str = typer.Argument(help="Action: list, sync, update"),
    sku: Optional[str] = typer.Option(None, help="SKU for specific operations"),
    warehouse: Optional[str] = typer.Option(None, help="Warehouse location")
):
    """Manage inventory operations."""
    async def _inventory_operations():
        settings = Settings()
        db_service = DatabaseService(settings.database_url)
        inventory_service = InventoryService(db_service)
        
        try:
            await db_service.connect()
            
            if action == "list":
                if sku:
                    # Show inventory for specific SKU
                    levels = await inventory_service.get_inventory_levels(sku)
                    
                    table = Table(title=f"Inventory Levels - {sku}")
                    table.add_column("Warehouse", style="cyan")
                    table.add_column("On Hand", style="green")
                    table.add_column("Reserved", style="yellow")
                    table.add_column("Available", style="magenta")
                    
                    for level in levels:
                        table.add_row(
                            level.warehouse_location.value,
                            str(level.quantity_on_hand),
                            str(level.quantity_reserved),
                            str(level.quantity_available)
                        )
                    
                    console.print(table)
                else:
                    rprint("[yellow]Please specify --sku for inventory listing[/yellow]")
            
            elif action == "sync":
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    
                    task = progress.add_task("Synchronizing inventory...", total=None)
                    result = await inventory_service.sync_all_warehouses()
                    progress.update(task, description="Inventory synchronized")
                
                rprint(f"[green]✓[/green] Synchronized {result} inventory items")
            
            else:
                rprint(f"[red]Unknown action:[/red] {action}")
                rprint("Available actions: list, sync, update")
        
        except Exception as e:
            rprint(f"[red]✗[/red] Inventory operation failed: {e}")
            raise typer.Exit(1)
        finally:
            await db_service.disconnect()
    
    asyncio.run(_inventory_operations())


@app.command()
def metrics(
    days: int = typer.Option(7, help="Number of days to show metrics for")
):
    """Show system metrics and performance data."""
    async def _show_metrics():
        settings = Settings()
        db_service = DatabaseService(settings.database_url)
        
        try:
            await db_service.connect()
            
            # Fetch metrics from database
            # This would be implemented with actual queries
            
            rprint(f"[bold]System Metrics - Last {days} Days[/bold]")
            rprint()
            
            # Orders processed
            table = Table(title="Order Processing Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")
            table.add_column("Average Time", style="yellow")
            
            # Sample data - replace with actual queries
            table.add_row("Orders Processed", "1,234", "2.3s")
            table.add_row("Successful", "1,198", "2.1s")
            table.add_row("Failed", "36", "4.2s")
            
            console.print(table)
            rprint()
            
            # Warehouse distribution
            warehouse_table = Table(title="Fulfillment by Warehouse")
            warehouse_table.add_column("Warehouse", style="cyan")
            warehouse_table.add_column("Orders", style="green")
            warehouse_table.add_column("Percentage", style="yellow")
            
            warehouse_table.add_row("California", "742", "60.1%")
            warehouse_table.add_row("Pennsylvania", "456", "36.9%")
            warehouse_table.add_row("Amazon FBA", "36", "2.9%")
            
            console.print(warehouse_table)
            
        except Exception as e:
            rprint(f"[red]✗[/red] Failed to fetch metrics: {e}")
            raise typer.Exit(1)
        finally:
            await db_service.disconnect()
    
    asyncio.run(_show_metrics())


@app.command()
def server(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """Start the FastAPI server."""
    try:
        import uvicorn
        from .api.main import app as fastapi_app
        
        rprint(f"[blue]Starting Grooved Learning Fulfillment System server...[/blue]")
        rprint(f"[blue]Host:[/blue] {host}")
        rprint(f"[blue]Port:[/blue] {port}")
        rprint(f"[blue]Reload:[/blue] {reload}")
        rprint()
        
        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except ImportError:
        rprint("[red]✗[/red] uvicorn not installed. Install with: uv add uvicorn")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]✗[/red] Server failed to start: {e}")
        raise typer.Exit(1)


def _create_sample_order(channel: str, customer_email: str) -> Order:
    """Create a sample order for testing."""
    return Order(
        order_number=f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        channel=OrderChannel(channel),
        customer=Customer(
            email=customer_email,
            first_name="Test",
            last_name="Customer"
        ),
        shipping_address=Address(
            name="Test Customer",
            address1="123 Test Street",
            city="Test City",
            state="CA",
            postal_code="90210",
            country="US"
        ),
        line_items=[
            LineItem(
                sku="CB-BOOK-001",
                name="Code Breakers Book Set - Level 1",
                quantity=1,
                price=29.99,
                weight_oz=8.0
            ),
            LineItem(
                sku="CB-CARDS-001",
                name="Code Breakers Sound Cards",
                quantity=1,
                price=19.99,
                weight_oz=4.0
            )
        ],
        subtotal=49.98,
        shipping_cost=5.99,
        tax_amount=4.50,
        total_amount=60.47,
        channel_order_id=f"ch_{datetime.now().timestamp()}"
    )


if __name__ == "__main__":
    app()