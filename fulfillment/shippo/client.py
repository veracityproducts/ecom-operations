"""Shippo API integration for shipping labels and packing slips."""
from typing import Optional, Dict, Any, List
import asyncio
import httpx
import logging
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import backoff
from contextlib import asynccontextmanager

# Pydantic Models for Type Safety
class ShippoAddress(BaseModel):
    name: str
    street1: str
    street2: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None

class ShippoParcel(BaseModel):
    length: float
    width: float
    height: float
    distance_unit: str = "in"
    weight: float
    mass_unit: str = "lb"

class ShippoOrder(BaseModel):
    order_number: str
    to_address: ShippoAddress
    from_address: Optional[ShippoAddress] = None
    line_items: List[Dict[str, Any]] = []
    placed_at: datetime
    order_status: str = "PAID"

class ShippoLabelResponse(BaseModel):
    object_id: str
    label_url: str
    tracking_number: str
    rate: str  # This is actually just the rate ID in the response
    status: str
    messages: List[Dict[str, str]] = []

class ShippoPackingSlipResponse(BaseModel):
    packing_slip_url: str
    expires_at: datetime

# Rate Limiting Configuration
class RateLimitConfig:
    """Shippo API rate limiting configuration based on tier"""
    def __init__(self, tier: str = "standard"):
        # Shippo rate limits (requests per minute)
        self.limits = {
            "test": 60,      # Test environment
            "standard": 300,  # Standard plan
            "professional": 600,  # Professional plan
            "enterprise": 1200   # Enterprise plan
        }
        self.rpm = self.limits.get(tier, 300)
        self.requests_per_second = self.rpm / 60
        self.semaphore = asyncio.Semaphore(int(self.requests_per_second * 2))

# Enhanced HTTP Client with Rate Limiting
class ShippoClient:
    """Production-ready async Shippo API client with rate limiting and retry logic"""
    
    def __init__(
        self,
        api_token: str,
        test_mode: bool = False,
        base_url: str = "https://api.goshippo.com",
        timeout: int = 30,
        max_concurrent: int = 10,
        rate_limit_tier: str = "standard"
    ):
        self.api_token = api_token
        self.test_mode = test_mode
        self.base_url = base_url.rstrip("/")
        self.rate_limit = RateLimitConfig(rate_limit_tier)
        
        # Configure httpx client with production settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=max_concurrent,
                max_connections=max_concurrent * 2
            ),
            headers={
                "Authorization": f"ShippoToken {api_token}",
                "Content-Type": "application/json",
                "User-Agent": "Grooved-Learning-Shippo-Client/1.0"
            }
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException),
        max_tries=3,
        max_time=60,
        jitter=backoff.full_jitter
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> httpx.Response:
        """Make rate-limited HTTP request with exponential backoff retry"""
        
        async with self.rate_limit.semaphore:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            try:
                response = await self.client.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    self.logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise httpx.HTTPStatusError(
                        f"Rate limited", 
                        request=response.request, 
                        response=response
                    )
                
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error {e.response.status_code}: {e}")
                if e.response.status_code >= 500:
                    # Server errors should be retried
                    raise
                else:
                    # Client errors should not be retried
                    self._handle_client_error(e)
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                self.logger.error(f"Connection error: {e}")
                raise
    
    def _handle_client_error(self, error: httpx.HTTPStatusError):
        """Handle client errors with detailed logging"""
        status_code = error.response.status_code
        
        error_details = {
            400: "Bad Request - Check request parameters",
            401: "Unauthorized - Check API token",
            402: "Payment Required - Check account status",
            403: "Forbidden - Check permissions",
            404: "Not Found - Check resource ID",
            422: "Unprocessable Entity - Check data validation"
        }
        
        message = error_details.get(status_code, f"Client error: {status_code}")
        self.logger.error(f"{message}: {error.response.text}")

# Main Shippo Service Class
class ShippoService:
    """Production Shippo integration service following Grooved Learning patterns"""
    
    def __init__(self, api_token: str, test_mode: bool = False, rate_limit_tier: str = "standard"):
        self.client = ShippoClient(api_token, test_mode=test_mode, rate_limit_tier=rate_limit_tier)
        self.logger = logging.getLogger(__name__)
    
    async def create_order(self, order: ShippoOrder) -> Dict[str, Any]:
        """Create order in Shippo system"""
        
        order_data = {
            "to_address": order.to_address.model_dump(),
            "line_items": order.line_items,
            "placed_at": order.placed_at.isoformat(),
            "order_number": order.order_number,
            "order_status": order.order_status
        }
        
        if order.from_address:
            order_data["from_address"] = order.from_address.model_dump()
        
        async with self.client as client:
            response = await client._make_request(
                "POST", 
                "/orders/", 
                json=order_data
            )
            return response.json()
    
    async def create_label_with_known_rate(
        self,
        shipment_data: Dict[str, Any],
        rate_id: str
    ) -> ShippoLabelResponse:
        """Create shipping label when rate is already known (single API call)"""
        
        transaction_data = {
            **shipment_data,
            "rate": rate_id,
            "label_file_type": "PDF",
            "async": False  # Synchronous label creation
        }
        
        async with self.client as client:
            response = await client._make_request(
                "POST",
                "/transactions/",
                json=transaction_data
            )
            
            result = response.json()
            return ShippoLabelResponse(**result)
    
    async def get_rates_and_create_label(
        self,
        from_address: ShippoAddress,
        to_address: ShippoAddress,
        parcel: ShippoParcel,
        preferred_carrier: Optional[str] = None
    ) -> ShippoLabelResponse:
        """Two-step process: get rates, then create label (rate shopping)"""
        
        # Step 1: Create shipment to get rates
        shipment_data = {
            "address_from": from_address.model_dump(),
            "address_to": to_address.model_dump(),
            "parcels": [parcel.model_dump()],
            "async": False
        }
        
        async with self.client as client:
            # Get available rates
            shipment_response = await client._make_request(
                "POST",
                "/shipments/",
                json=shipment_data
            )
            
            shipment = shipment_response.json()
            rates = shipment.get("rates", [])
            
            if not rates:
                raise ValueError("No shipping rates available")
            
            # Select best rate (cheapest by default, or preferred carrier)
            selected_rate = self._select_best_rate(rates, preferred_carrier)
            
            # Step 2: Purchase label
            label_response = await self.create_label_with_known_rate(
                shipment_data, 
                selected_rate["object_id"]
            )
            
            # Add the full rate details to the response for convenience
            label_response_dict = label_response.model_dump()
            label_response_dict["rate_details"] = selected_rate
            
            return label_response
    
    def _select_best_rate(
        self, 
        rates: List[Dict[str, Any]], 
        preferred_carrier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Select the best shipping rate based on criteria"""
        
        valid_rates = [r for r in rates if r.get("messages", []) == []]
        
        if not valid_rates:
            raise ValueError("No valid shipping rates available")
        
        # Prefer specific carrier if requested
        if preferred_carrier:
            carrier_rates = [
                r for r in valid_rates 
                if r.get("provider", "").lower() == preferred_carrier.lower()
            ]
            if carrier_rates:
                return min(carrier_rates, key=lambda x: float(x["amount"]))
        
        # Default: cheapest rate
        return min(valid_rates, key=lambda x: float(x["amount"]))
    
    async def get_packing_slip(self, order_id: str) -> ShippoPackingSlipResponse:
        """Get packing slip PDF URL for order (expires in 24 hours)"""
        
        async with self.client as client:
            response = await client._make_request(
                "GET",
                f"/orders/{order_id}/packingslip/"
            )
            
            result = response.json()
            
            return ShippoPackingSlipResponse(
                packing_slip_url=result.get("packing_slip_url", ""),
                expires_at=datetime.now() + timedelta(hours=24)
            )
    
    async def create_combined_label_and_packing_slip(
        self,
        order: ShippoOrder,
        parcel: ShippoParcel,
        preferred_carrier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: Create order, generate label, get packing slip
        This is the $0.05/label solution mentioned in the PRP
        """
        
        try:
            # Step 1: Create order in Shippo
            order_result = await self.create_order(order)
            order_id = order_result["object_id"]
            
            # Step 2: Create shipping label
            label_result = await self.get_rates_and_create_label(
                from_address=order.from_address or self._get_default_from_address(),
                to_address=order.to_address,
                parcel=parcel,
                preferred_carrier=preferred_carrier
            )
            
            # Step 3: Get packing slip
            packing_slip_result = await self.get_packing_slip(order_id)
            
            return {
                "order_id": order_id,
                "label": {
                    "url": label_result.label_url,
                    "tracking_number": label_result.tracking_number,
                    "rate_amount": getattr(label_result, 'rate_details', {}).get("amount", "0.00"),
                    "carrier": getattr(label_result, 'rate_details', {}).get("provider", "")
                },
                "packing_slip": {
                    "url": packing_slip_result.packing_slip_url,
                    "expires_at": packing_slip_result.expires_at.isoformat()
                },
                "total_cost": float(getattr(label_result, 'rate_details', {}).get("amount", "0.00")) + 0.05,  # Label + $0.05 packing slip
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create combined label and packing slip: {e}")
            raise
    
    def _get_default_from_address(self) -> ShippoAddress:
        """Default Grooved Learning shipping address"""
        return ShippoAddress(
            name="Grooved Learning",
            street1="[Your Warehouse Address]",
            city="[Your City]",
            state="[Your State]",
            zip="[Your ZIP]",
            country="US",
            phone="[Your Phone]",
            email="shipping@groovedlearning.com"
        )