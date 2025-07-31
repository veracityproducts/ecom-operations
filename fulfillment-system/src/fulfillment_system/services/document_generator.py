"""
Document generation service for labels and packing slips.

This service overcomes ShipStation's packing slip limitation by generating
professional PDF documents independently while integrating with carrier APIs
for shipping labels.
"""

import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from ..models.schemas import Order, ShippingRate, WarehouseLocation, LineItem
from ..utils.exceptions import DocumentGenerationError
from ..utils.storage import StorageService

logger = logging.getLogger(__name__)


class DocumentTemplate:
    """Base class for document templates."""
    
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for Grooved Learning branding."""
        # Brand colors
        self.brand_primary = HexColor('#2E5984')  # Deep blue
        self.brand_secondary = HexColor('#E8742A')  # Orange accent
        self.brand_gray = HexColor('#6B7280')
        
        # Custom paragraph styles
        self.styles.add(ParagraphStyle(
            'BrandTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=self.brand_primary,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            'BrandSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.brand_secondary,
            fontStyle='italic',
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            'OrderInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))


class PackingSlipTemplate(DocumentTemplate):
    """Professional packing slip generator for Grooved Learning."""
    
    async def generate(
        self, 
        order: Order, 
        warehouse: WarehouseLocation,
        fulfillment_details: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate branded packing slip PDF.
        
        Args:
            order: Order information
            warehouse: Fulfilling warehouse
            fulfillment_details: Additional fulfillment data
            
        Returns:
            PDF bytes
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=1*inch,
                bottomMargin=1*inch
            )
            
            # Build document content
            story = []
            
            # Header
            story.extend(self._build_header())
            
            # Order information
            story.extend(self._build_order_info(order))
            
            # Shipping information  
            story.extend(self._build_shipping_info(order, warehouse))
            
            # Items table
            story.extend(self._build_items_table(order))
            
            # Educational message
            story.extend(self._build_educational_message())
            
            # Footer
            story.extend(self._build_footer(warehouse))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info(f"Packing slip generated for order {order.order_number}")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate packing slip for order {order.order_number}: {e}")
            raise DocumentGenerationError(f"Packing slip generation failed: {str(e)}") from e
    
    def _build_header(self) -> List:
        """Build document header with Grooved Learning branding."""
        content = []
        
        # Company name and tagline
        content.append(Paragraph("Grooved Learning", self.styles['BrandTitle']))
        content.append(Paragraph("Making Learning Engaging & Effective", self.styles['BrandSubtitle']))
        content.append(Spacer(1, 0.2*inch))
        
        return content
    
    def _build_order_info(self, order: Order) -> List:
        """Build order information section."""
        content = []
        
        # Order details
        order_info = [
            f"<b>Order #{order.order_number}</b>",
            f"Order Date: {order.created_at.strftime('%B %d, %Y')}",
            f"Channel: {order.channel.value.title()}"
        ]
        
        for info in order_info:
            content.append(Paragraph(info, self.styles['OrderInfo']))
        
        content.append(Spacer(1, 0.2*inch))
        return content
    
    def _build_shipping_info(self, order: Order, warehouse: WarehouseLocation) -> List:
        """Build shipping information section."""
        content = []
        
        # Create two-column layout for billing and shipping
        shipping_data = [
            ['<b>Ship To:</b>', '<b>Fulfilling From:</b>'],
            [
                self._format_address(order.shipping_address),
                self._get_warehouse_info(warehouse)
            ]
        ]
        
        shipping_table = Table(shipping_data, colWidths=[3*inch, 3*inch])
        shipping_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        content.append(shipping_table)
        content.append(Spacer(1, 0.3*inch))
        
        return content
    
    def _build_items_table(self, order: Order) -> List:
        """Build items table with educational product details."""
        content = []
        
        # Table header
        content.append(Paragraph("<b>Items Included in Your Order:</b>", self.styles['OrderInfo']))
        content.append(Spacer(1, 0.1*inch))
        
        # Build table data
        table_data = [
            ['<b>Qty</b>', '<b>Item</b>', '<b>SKU</b>', '<b>Notes</b>']
        ]
        
        for item in order.shipping_items:
            # Add educational context to product names
            educational_note = self._get_educational_note(item)
            
            table_data.append([
                str(item.quantity),
                item.name,
                item.sku,
                educational_note
            ])
        
        # Create table
        items_table = Table(
            table_data,
            colWidths=[0.6*inch, 3.5*inch, 1.2*inch, 1.5*inch]
        )
        
        items_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), self.brand_primary),
            ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, self.brand_gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['white', HexColor('#F9FAFB')]),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(items_table)
        content.append(Spacer(1, 0.3*inch))
        
        return content
    
    def _build_educational_message(self) -> List:
        """Build educational support message."""
        content = []
        
        message = """
        <b>Thank you for supporting your child's learning journey!</b><br/><br/>
        
        Your Grooved Learning products are designed using research-based methods 
        to make learning engaging and effective. Each item in your order supports 
        multi-sensory learning that helps children retain information better.<br/><br/>
        
        <b>Need support?</b> Visit groovedlearning.com/support for:<br/>
        • Product guides and tutorials<br/>
        • Additional learning resources<br/>
        • Customer support<br/><br/>
        
        <i>Happy Learning!</i><br/>
        The Grooved Learning Team
        """
        
        content.append(Paragraph(message, self.styles['Normal']))
        content.append(Spacer(1, 0.2*inch))
        
        return content
    
    def _build_footer(self, warehouse: WarehouseLocation) -> List:
        """Build document footer with contact information."""
        content = []
        
        footer_info = [
            "Grooved Learning • groovedlearning.com • support@groovedlearning.com",
            f"Shipped from our {warehouse.value} facility • Track your order online"
        ]
        
        for info in footer_info:
            footer_style = ParagraphStyle(
                'Footer',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=self.brand_gray,
                alignment=TA_CENTER
            )
            content.append(Paragraph(info, footer_style))
        
        return content
    
    def _format_address(self, address) -> str:
        """Format address for display."""
        lines = [address.name]
        if hasattr(address, 'company') and address.company:
            lines.append(address.company)
        lines.append(address.address1)
        if hasattr(address, 'address2') and address.address2:
            lines.append(address.address2)
        lines.append(f"{address.city}, {address.state} {address.postal_code}")
        if address.country != "US":
            lines.append(address.country)
        
        return '<br/>'.join(lines)
    
    def _get_warehouse_info(self, warehouse: WarehouseLocation) -> str:
        """Get warehouse address information."""
        warehouse_info = {
            WarehouseLocation.CALIFORNIA: 
                "Grooved Learning<br/>California Distribution Center<br/>Los Angeles, CA",
            WarehouseLocation.PENNSYLVANIA: 
                "Grooved Learning<br/>Pennsylvania Distribution Center<br/>Philadelphia, PA",
            WarehouseLocation.AMAZON_FBA: 
                "Amazon Fulfillment<br/>Various Locations<br/>Fulfilled by Amazon",
            WarehouseLocation.TIKTOK_WAREHOUSE: 
                "TikTok Shop Fulfillment<br/>Various Locations<br/>Fulfilled by TikTok"
        }
        
        return warehouse_info.get(warehouse, "Grooved Learning<br/>Distribution Center")
    
    def _get_educational_note(self, item: LineItem) -> str:
        """Get educational context note for product."""
        sku = item.sku.upper()
        
        if sku.startswith('CB-'):
            return "Phonics Learning"
        elif sku.startswith('CW-'):
            return "Handwriting Practice"
        elif sku.startswith('EH-'):
            return "English Handwriting"
        elif sku.startswith('SH-'):
            return "Spanish Handwriting"
        elif '-SET' in sku:
            return "Complete Set"
        else:
            return "Educational Tool"


class LabelIntegrationService:
    """Service for integrating with carrier APIs for label generation."""
    
    def __init__(self):
        self.carrier_clients = {}  # Will be populated with carrier API clients
    
    async def generate_shipping_label(
        self, 
        order: Order, 
        shipping_rate: ShippingRate,
        warehouse: WarehouseLocation
    ) -> Dict[str, Any]:
        """
        Generate shipping label via carrier API.
        
        Args:
            order: Order information
            shipping_rate: Selected shipping rate
            warehouse: Fulfilling warehouse
            
        Returns:
            Label data including URL and tracking number
        """
        try:
            carrier = shipping_rate.carrier.value
            
            # Get warehouse origin address
            origin_address = self._get_warehouse_address(warehouse)
            
            # Build shipment data
            shipment_data = {
                'origin': origin_address,
                'destination': {
                    'name': order.shipping_address.name,
                    'company': getattr(order.shipping_address, 'company', None),
                    'address1': order.shipping_address.address1,
                    'address2': getattr(order.shipping_address, 'address2', None),
                    'city': order.shipping_address.city,
                    'state': order.shipping_address.state,
                    'postal_code': order.shipping_address.postal_code,
                    'country': order.shipping_address.country,
                    'phone': getattr(order.shipping_address, 'phone', None)
                },
                'packages': [{
                    'weight_oz': order.total_weight_oz,
                    'length': 12,  # Default packaging dimensions
                    'width': 9,
                    'height': 3
                }],
                'service_level': shipping_rate.service_level,
                'reference': order.order_number
            }
            
            # Generate label through appropriate carrier client
            if carrier in self.carrier_clients:
                label_result = await self.carrier_clients[carrier].generate_label(shipment_data)
                
                logger.info(f"Shipping label generated for order {order.order_number}")
                return label_result
            else:
                raise DocumentGenerationError(f"No client configured for carrier {carrier}")
                
        except Exception as e:
            logger.error(f"Failed to generate shipping label for order {order.order_number}: {e}")
            raise DocumentGenerationError(f"Label generation failed: {str(e)}") from e
    
    def _get_warehouse_address(self, warehouse: WarehouseLocation) -> Dict[str, str]:
        """Get warehouse origin address for shipping."""
        addresses = {
            WarehouseLocation.CALIFORNIA: {
                'name': 'Grooved Learning',
                'address1': '123 Education Way',
                'city': 'Los Angeles',
                'state': 'CA',
                'postal_code': '90210',
                'country': 'US'
            },
            WarehouseLocation.PENNSYLVANIA: {
                'name': 'Grooved Learning',
                'address1': '456 Learning Lane',
                'city': 'Philadelphia',
                'state': 'PA',
                'postal_code': '19019',
                'country': 'US'
            }
        }
        
        return addresses.get(warehouse, addresses[WarehouseLocation.CALIFORNIA])


class DocumentGeneratorService:
    """
    Main service for generating all fulfillment documents.
    
    Coordinates packing slip and label generation to overcome ShipStation limitations.
    """
    
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.packing_slip_template = PackingSlipTemplate(storage_service)
        self.label_service = LabelIntegrationService()
    
    async def generate_fulfillment_documents(
        self,
        order: Order,
        shipping_rate: ShippingRate,
        warehouse: WarehouseLocation
    ) -> Dict[str, Any]:
        """
        Generate all documents needed for fulfillment.
        
        Args:
            order: Order to fulfill
            shipping_rate: Selected shipping rate
            warehouse: Fulfilling warehouse
            
        Returns:
            Dictionary with document URLs and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate documents concurrently
            import asyncio
            
            packing_slip_task = asyncio.create_task(
                self._generate_and_store_packing_slip(order, warehouse)
            )
            
            label_task = asyncio.create_task(
                self.label_service.generate_shipping_label(order, shipping_rate, warehouse)
            )
            
            # Wait for both to complete
            packing_slip_result, label_result = await asyncio.gather(
                packing_slip_task, label_task
            )
            
            # Optionally combine documents
            combined_pdf = await self._combine_documents(
                packing_slip_result['pdf_bytes'],
                label_result.get('label_pdf_bytes')
            )
            
            combined_url = None
            if combined_pdf:
                combined_url = await self.storage_service.store_document(
                    combined_pdf,
                    f"combined_{order.order_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
                    'combined'
                )
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'packing_slip_url': packing_slip_result['url'],
                'label_url': label_result.get('label_url'),
                'combined_url': combined_url,
                'tracking_number': label_result.get('tracking_number'),
                'carrier': shipping_rate.carrier.value,
                'service_level': shipping_rate.service_level,
                'generation_time_seconds': generation_time,
                'warehouse': warehouse.value
            }
            
            logger.info(
                f"All documents generated for order {order.order_number} "
                f"in {generation_time:.2f} seconds"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed for order {order.order_number}: {e}")
            raise DocumentGenerationError(
                f"Failed to generate fulfillment documents: {str(e)}"
            ) from e
    
    async def _generate_and_store_packing_slip(
        self, 
        order: Order, 
        warehouse: WarehouseLocation
    ) -> Dict[str, Any]:
        """Generate packing slip and store it."""
        # Generate PDF
        pdf_bytes = await self.packing_slip_template.generate(order, warehouse)
        
        # Store in cloud storage
        filename = f"packing_slip_{order.order_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        url = await self.storage_service.store_document(pdf_bytes, filename, 'packing_slips')
        
        return {
            'pdf_bytes': pdf_bytes,
            'url': url,
            'filename': filename
        }
    
    async def _combine_documents(
        self, 
        packing_slip_pdf: bytes, 
        label_pdf: Optional[bytes]
    ) -> Optional[bytes]:
        """Combine packing slip and label into single PDF."""
        if not label_pdf:
            return None
        
        try:
            from pypdf import PdfReader, PdfWriter
            import io
            
            writer = PdfWriter()
            
            # Add packing slip pages
            packing_slip_reader = PdfReader(io.BytesIO(packing_slip_pdf))
            for page in packing_slip_reader.pages:
                writer.add_page(page)
            
            # Add label pages
            label_reader = PdfReader(io.BytesIO(label_pdf))
            for page in label_reader.pages:
                writer.add_page(page)
            
            # Write combined PDF
            output = io.BytesIO()
            writer.write(output)
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Failed to combine documents: {e}")
            return None
    
    async def regenerate_documents(
        self, 
        order_id: UUID, 
        document_type: str = 'all'
    ) -> Dict[str, Any]:
        """
        Regenerate documents for an existing order.
        
        Args:
            order_id: Order to regenerate documents for
            document_type: Type of document ('packing_slip', 'label', 'all')
            
        Returns:
            Updated document information
        """
        # Implementation would fetch order from database and regenerate requested documents
        pass