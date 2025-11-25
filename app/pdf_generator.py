"""
PDF Generator Module for GEE Analysis Reports
Creates professional, publication-quality PDF reports with beautiful visualizations
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                PageBreak, Table, TableStyle, Frame, PageTemplate)
from reportlab.pdfgen import canvas
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Any
import os

from app.chart_generator import ChartGenerator
from app.map_renderer import MapRenderer


class PDFReportGenerator:
    """Generate comprehensive PDF reports for geospatial analysis"""
    
    def __init__(self):
        """Initialize PDF generator with styling"""
        self.chart_gen = ChartGenerator()
        self.map_render = MapRenderer()
        
        # Modern color palette inspired by Figma design systems
        self.colors = {
            'primary': colors.HexColor('#1E3A8A'),      # Deep blue
            'secondary': colors.HexColor('#3B82F6'),    # Bright blue
            'accent': colors.HexColor('#8B5CF6'),       # Purple
            'success': colors.HexColor('#10B981'),      # Green
            'warning': colors.HexColor('#F59E0B'),      # Amber
            'danger': colors.HexColor('#EF4444'),       # Red
            'light_bg': colors.HexColor('#F9FAFB'),     # Very light gray
            'dark_bg': colors.HexColor('#111827'),      # Very dark gray
            'gradient_start': colors.HexColor('#667eea'),# Gradient purple
            'gradient_end': colors.HexColor('#764ba2'),  # Gradient deep purple
            'card_bg': colors.HexColor('#FFFFFF'),       # White
            'border': colors.HexColor('#E5E7EB')         # Light border
        }
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles with modern design"""
        # Main Title style - Large and bold with gradient effect
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=32,
            textColor=self.colors['primary'],
            spaceAfter=30,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=38
        ))
        
        # Section Heading style - Modern and clean
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=20,
            textColor=self.colors['secondary'],
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            leading=24,
            borderPadding=(10, 0, 5, 0)
        ))
        
        # Subheading style - Elegant
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading3'],
            fontSize=16,
            textColor=self.colors['dark_bg'],
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            leading=20
        ))
        
        # Body text style - Readable and clean
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=16,
            textColor=colors.HexColor('#374151')
        ))
        
        # Highlight style - Eye-catching
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['BodyText'],
            fontSize=13,
            textColor=self.colors['success'],
            fontName='Helvetica-Bold',
            spaceAfter=10,
            leading=16
        ))
        
        # Card Title style
        self.styles.add(ParagraphStyle(
            name='CardTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=self.colors['primary'],
            fontName='Helvetica-Bold',
            spaceAfter=8,
            alignment=TA_CENTER
        ))
        
        # Metric Value style
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=24,
            textColor=self.colors['secondary'],
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=5
        ))
        
        # Caption style
        self.styles.add(ParagraphStyle(
            name='Caption',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER,
            spaceAfter=8
        ))
    
    def generate_report(self, analysis_data: Dict, output_path: Optional[str] = None) -> BytesIO:
        """
        Generate comprehensive PDF report
        
        Args:
            analysis_data: Complete analysis results
            output_path: Optional file path to save PDF
            
        Returns:
            BytesIO: PDF buffer
        """
        try:
            print(f"📊 Starting PDF generation with data keys: {list(analysis_data.keys())}")
            
            # Ensure we have required fields
            if 'latitude' not in analysis_data:
                analysis_data['latitude'] = 'N/A'
            if 'longitude' not in analysis_data:
                analysis_data['longitude'] = 'N/A'
            if 'analysis_date' not in analysis_data:
                analysis_data['analysis_date'] = datetime.now().strftime('%B %d, %Y')
            
            # Create buffer
            buffer = BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer if not output_path else output_path,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=1*inch,
                bottomMargin=0.75*inch
            )
            
            # Build story (content)
            story = []
            
            # 1. Cover Page
            print("📄 Creating cover page...")
            story.extend(self._create_cover_page(analysis_data))
            story.append(PageBreak())
            
            # 2. Executive Summary
            print("📊 Creating executive summary...")
            story.extend(self._create_executive_summary(analysis_data))
            story.append(PageBreak())
            
            # 3. Location & Area Analysis
            print("🗺️ Creating location section...")
            story.extend(self._create_location_section(analysis_data))
            story.append(PageBreak())
            
            # 4. Vegetation Analysis (if available)
            if 'vegetation' in analysis_data and analysis_data['vegetation']:
                print("🌱 Creating vegetation section...")
                story.extend(self._create_vegetation_section(analysis_data['vegetation']))
                story.append(PageBreak())
            
            # 5. Building Analysis (if available)
            if 'buildings' in analysis_data and analysis_data['buildings']:
                print("🏢 Creating building section...")
                story.extend(self._create_building_section(analysis_data['buildings']))
                story.append(PageBreak())
            
            # 6. Administrative Context (if available)
            if 'administrative' in analysis_data and analysis_data['administrative']:
                print("🏛️ Creating administrative section...")
                story.extend(self._create_administrative_section(analysis_data['administrative']))
                story.append(PageBreak())
            
            # 7. Additional Layers (if available)
            print("📑 Creating additional layers section...")
            story.extend(self._create_additional_layers_section(analysis_data))
            story.append(PageBreak())
            
            # 8. Recommendations & Conclusions
            print("💡 Creating recommendations section...")
            story.extend(self._create_recommendations_section(analysis_data))
            
            # Build PDF
            print("🔨 Building PDF document...")
            doc.build(story, onFirstPage=self._add_header_footer,
                     onLaterPages=self._add_header_footer)
            
            print("✅ PDF generated successfully!")
            
            # Return buffer
            if not output_path:
                buffer.seek(0)
                return buffer
            else:
                with open(output_path, 'rb') as f:
                    buffer = BytesIO(f.read())
                return buffer
                
        except Exception as e:
            print(f"❌ Error generating PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"PDF generation failed: {str(e)}")
    
    def _create_cover_page(self, data: Dict) -> List:
        """Create stunning modern cover page with gradient background effect"""
        elements = []
        
        # Add spacing from top
        elements.append(Spacer(1, 0.5*inch))
        
        # Create a decorative header box with gradient-like effect
        header_box_data = [['']]
        header_box = Table(header_box_data, colWidths=[6.5*inch], rowHeights=[0.3*inch])
        header_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['gradient_start']),
            ('ROUNDEDCORNERS', [15, 15, 15, 15]),
        ]))
        elements.append(header_box)
        elements.append(Spacer(1, 0.3*inch))
        
        # Icon/Logo placeholder with styled box
        icon_text = Paragraph(
            '<font size="36" color="#667eea">🛰️</font>',
            self.styles['CustomTitle']
        )
        elements.append(icon_text)
        elements.append(Spacer(1, 0.2*inch))
        
        # Main title with modern styling
        title = Paragraph(
            '<b><font size="36" color="#1E3A8A">GEOSPATIAL ANALYSIS</font></b><br/>'
            '<font size="28" color="#3B82F6">COMPREHENSIVE REPORT</font>',
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        # Decorative line
        line_table = Table([['']], colWidths=[4*inch], rowHeights=[0.05*inch])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['secondary']),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ]))
        elements.append(line_table)
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Subtitle with modern description
        subtitle = Paragraph(
            '<font size="13" color="#6B7280"><i>Powered by Google Earth Engine • Sentinel-2 • MODIS • FAO GAUL</i></font>',
            self.styles['CustomBody']
        )
        elements.append(subtitle)
        elements.append(Spacer(1, 0.8*inch))
        
        # Location information in modern card style
        location_html = f"""
        <para align="center" spaceAfter="8">
            <font size="13" color="#1E3A8A"><b>📍 ANALYSIS LOCATION</b></font>
        </para>
        <para align="center" spaceAfter="5">
            <font size="11" color="#374151">
                <b>Coordinates:</b> {data.get('latitude', 'N/A')}°N, {data.get('longitude', 'N/A')}°E
            </font>
        </para>
        <para align="center" spaceAfter="15">
            <font size="10" color="#6B7280">
                {data.get('administrative', {}).get('country', 'N/A')} → 
                {data.get('administrative', {}).get('state', 'N/A')} → 
                {data.get('administrative', {}).get('district', 'N/A')}
            </font>
        </para>
        """
        
        location_para = Paragraph(location_html, self.styles['CustomBody'])
        
        # Create modern card for location info
        location_card = Table(
            [[location_para]],
            colWidths=[5.5*inch]
        )
        location_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['card_bg']),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['dark_bg']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('BOX', (0, 0), (-1, -1), 2, self.colors['border']),
            ('ROUNDEDCORNERS', [12, 12, 12, 12]),
        ]))
        
        elements.append(location_card)
        elements.append(Spacer(1, 0.6*inch))
        
        # Analysis metadata in grid format
        analysis_date = data.get('analysis_date', datetime.now().strftime('%B %d, %Y'))
        analysis_type = 'Polygon Analysis' if data.get('polygon') else 'Point Analysis'
        
        metadata_data = [
            ['📅 Report Date', '🎯 Analysis Type', '📊 Data Quality'],
            [analysis_date, analysis_type, 'High Confidence'],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 2*inch, 2*inch])
        metadata_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['light_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['primary']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Data row
            ('BACKGROUND', (0, 1), (-1, 1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, 1), self.colors['dark_bg']),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('TOPPADDING', (0, 1), (-1, 1), 15),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 15),
            # Borders
            ('BOX', (0, 0), (-1, -1), 1.5, self.colors['border']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['secondary']),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.colors['border']),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        
        elements.append(metadata_table)
        elements.append(Spacer(1, 0.8*inch))
        
        # Footer with branding
        footer_text = Paragraph(
            '<para align="center">'
            '<font size="10" color="#8B5CF6"><b>🌍 Earth Engine Geospatial Intelligence Platform</b></font><br/>'
            '<font size="8" color="#9CA3AF">Satellite-driven insights for sustainable development and planning</font>'
            '</para>',
            self.styles['CustomBody']
        )
        elements.append(footer_text)
        
        return elements
    
    def _create_executive_summary(self, data: Dict) -> List:
        """Create executive summary page"""
        elements = []
        
        # Title
        title = Paragraph("Executive Summary", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Key findings
        elements.append(Paragraph("Key Findings", self.styles['CustomHeading']))
        
        summary_points = []
        
        # Vegetation summary
        if 'vegetation' in data and data['vegetation']:
            veg = data['vegetation'].get('metrics', {})
            health_idx = veg.get('vegetation_health_index', 0)
            summary_points.append(
                f"<b>Vegetation Health:</b> Health index of {health_idx:.3f} "
                f"({'Excellent' if health_idx > 0.7 else 'Good' if health_idx > 0.5 else 'Fair' if health_idx > 0.3 else 'Poor'})"
            )
            summary_points.append(
                f"<b>NDVI:</b> Mean value of {veg.get('mean_ndvi', 0):.3f} indicating "
                f"{'dense' if veg.get('mean_ndvi', 0) > 0.6 else 'moderate' if veg.get('mean_ndvi', 0) > 0.3 else 'sparse'} vegetation"
            )
        
        # Building summary
        if 'buildings' in data and data['buildings']:
            bldg = data['buildings'].get('metrics', {})
            summary_points.append(
                f"<b>Building Count:</b> {bldg.get('building_count', 0):,} structures identified"
            )
            summary_points.append(
                f"<b>Built-up Coverage:</b> {bldg.get('coverage_percentage', 0):.2f}% of analysis area"
            )
        
        # Administrative summary
        if 'administrative' in data and data['administrative']:
            admin = data['administrative']
            summary_points.append(
                f"<b>Administrative Context:</b> Located in {admin.get('district', 'N/A')}, "
                f"{admin.get('state', 'N/A')}, {admin.get('country', 'N/A')}"
            )
        
        # Create summary list
        for point in summary_points:
            p = Paragraph(f"• {point}", self.styles['CustomBody'])
            elements.append(p)
            elements.append(Spacer(1, 0.1*inch))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Add summary dashboard chart
        try:
            dashboard_img = self.chart_gen.create_summary_dashboard(data)
            img = Image(dashboard_img, width=6.5*inch, height=4.5*inch)
            elements.append(img)
        except Exception as e:
            print(f"Error creating summary dashboard: {e}")
        
        return elements
    
    def _create_location_section(self, data: Dict) -> List:
        """Create location and area analysis section"""
        elements = []
        
        title = Paragraph("Location & Analysis Area", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Determine if polygon or point analysis
        if 'polygon' in data and data['polygon']:
            # Polygon analysis
            elements.append(Paragraph("Analysis Area (Polygon)", self.styles['CustomHeading']))
            
            polygon_text = f"""
            This analysis covers a custom-defined polygon area with the following characteristics:<br/>
            <b>Number of vertices:</b> {len(data['polygon'])}<br/>
            <b>Approximate area:</b> {data.get('area_km2', 'N/A')} km²<br/>
            <b>Analysis type:</b> Precise boundary-based analysis
            """
            elements.append(Paragraph(polygon_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Render polygon map
            try:
                polygon_img = self.map_render.render_polygon_on_map(
                    data['polygon'],
                    title="Analysis Polygon"
                )
                img = Image(polygon_img, width=5.5*inch, height=5.5*inch)
                elements.append(img)
            except Exception as e:
                print(f"Error rendering polygon: {e}")
        else:
            # Point analysis
            elements.append(Paragraph("Analysis Location (Point)", self.styles['CustomHeading']))
            
            lat = data.get('latitude', 0)
            lon = data.get('longitude', 0)
            buffer = data.get('buffer_meters', 750)
            
            point_text = f"""
            This analysis is centered on a specific point location with a buffer zone:<br/>
            <b>Coordinates:</b> {lat}°N, {lon}°E<br/>
            <b>Buffer radius:</b> {buffer} meters<br/>
            <b>Analysis area:</b> ~{(3.14159 * (buffer/1000)**2):.2f} km²
            """
            elements.append(Paragraph(point_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Render point map
            try:
                point_img = self.map_render.render_point_location(
                    lat, lon, buffer,
                    title="Analysis Location"
                )
                img = Image(point_img, width=5.5*inch, height=5.5*inch)
                elements.append(img)
            except Exception as e:
                print(f"Error rendering point location: {e}")
        
        return elements
    
    def _create_vegetation_section(self, vegetation_data: Dict) -> List:
        """Create vegetation analysis section"""
        elements = []
        
        title = Paragraph("Vegetation Analysis", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        desc = Paragraph(
            "Comprehensive vegetation health assessment using multiple satellite-derived indices. "
            "This analysis combines Sentinel-2 and MODIS data for maximum reliability and coverage.",
            self.styles['CustomBody']
        )
        elements.append(desc)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add vegetation health chart
        try:
            veg_chart = self.chart_gen.create_vegetation_health_chart(vegetation_data)
            img = Image(veg_chart, width=6.5*inch, height=5.5*inch)
            elements.append(img)
        except Exception as e:
            print(f"Error creating vegetation chart: {e}")
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Detailed metrics table
        metrics = vegetation_data.get('metrics', {})
        
        data_rows = [
            ['<b>Metric</b>', '<b>Value</b>', '<b>Interpretation</b>'],
            ['NDVI', f"{metrics.get('mean_ndvi', 0):.3f}",
             'Normalized Difference Vegetation Index'],
            ['EVI', f"{metrics.get('mean_evi', 0):.3f}",
             'Enhanced Vegetation Index'],
            ['SAVI', f"{metrics.get('mean_savi', 0):.3f}",
             'Soil-Adjusted Vegetation Index'],
            ['Health Index', f"{metrics.get('vegetation_health_index', 0):.3f}",
             'Overall vegetation health metric']
        ]
        
        metrics_table = Table(data_rows, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['secondary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(metrics_table)
        
        # Add visualization maps if available
        if 'visualization_urls' in vegetation_data:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("Satellite Imagery Visualizations", self.styles['CustomHeading']))
            
            viz_urls = vegetation_data['visualization_urls']
            
            # Create multi-layer visualization
            try:
                multi_viz = self.map_render.create_multi_layer_visualization(viz_urls)
                img = Image(multi_viz, width=6.5*inch, height=6.5*inch)
                elements.append(img)
            except Exception as e:
                print(f"Error creating multi-layer visualization: {e}")
        
        return elements
    
    def _create_building_section(self, building_data: Dict) -> List:
        """Create building analysis section"""
        elements = []
        
        title = Paragraph("Building Intelligence Analysis", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        desc = Paragraph(
            "Building footprint analysis using Google Research Open Buildings dataset. "
            "This section provides insights into urban development, building density, and land use patterns.",
            self.styles['CustomBody']
        )
        elements.append(desc)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add building chart
        try:
            bldg_chart = self.chart_gen.create_building_analysis_chart(building_data)
            img = Image(bldg_chart, width=6.5*inch, height=5.5*inch)
            elements.append(img)
        except Exception as e:
            print(f"Error creating building chart: {e}")
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Detailed metrics
        metrics = building_data.get('metrics', {})
        
        building_summary = f"""
        <b>Total Buildings Identified:</b> {metrics.get('building_count', 0):,}<br/>
        <b>Total Built-up Area:</b> {metrics.get('total_area_km2', 0):.2f} km²<br/>
        <b>Average Building Size:</b> {metrics.get('average_area_m2', 0):.0f} m²<br/>
        <b>Building Density:</b> {metrics.get('density_per_km2', 0):.0f} buildings/km²<br/>
        <b>Coverage Percentage:</b> {metrics.get('coverage_percentage', 0):.2f}%
        """
        
        elements.append(Paragraph(building_summary, self.styles['CustomBody']))
        
        return elements
    
    def _create_administrative_section(self, admin_data: Dict) -> List:
        """Create administrative context section"""
        elements = []
        
        title = Paragraph("Administrative Context", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        desc = Paragraph(
            "Administrative boundaries analysis using FAO Global Administrative Unit Layers (GAUL). "
            "This provides official geographic context for planning and reporting purposes.",
            self.styles['CustomBody']
        )
        elements.append(desc)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add administrative chart
        try:
            admin_chart = self.chart_gen.create_administrative_chart(admin_data)
            img = Image(admin_chart, width=6*inch, height=4*inch)
            elements.append(img)
        except Exception as e:
            print(f"Error creating administrative chart: {e}")
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Administrative hierarchy table
        admin_rows = [
            ['<b>Level</b>', '<b>Name</b>', '<b>Code</b>'],
            ['Country (ADM0)', admin_data.get('country', 'N/A'), admin_data.get('country_code', 'N/A')],
            ['State/Province (ADM1)', admin_data.get('state', 'N/A'), admin_data.get('state_code', 'N/A')],
            ['District (ADM2)', admin_data.get('district', 'N/A'), admin_data.get('district_code', 'N/A')]
        ]
        
        admin_table = Table(admin_rows, colWidths=[2*inch, 2.5*inch, 2*inch])
        admin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['warning']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgoldenrodyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(admin_table)
        
        return elements
    
    def _create_additional_layers_section(self, data: Dict) -> List:
        """Create section for additional analysis layers"""
        elements = []
        
        # Check if there are other layers
        additional_layers = []
        for key in ['elevation', 'landcover', 'water', 'soil', 'climate', 'population']:
            if key in data and data[key]:
                additional_layers.append((key, data[key]))
        
        if not additional_layers:
            return elements
        
        title = Paragraph("Additional Analysis Layers", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        desc = Paragraph(
            "Supplementary geospatial datasets providing additional context and insights.",
            self.styles['CustomBody']
        )
        elements.append(desc)
        elements.append(Spacer(1, 0.2*inch))
        
        # Create summary for each layer
        for layer_name, layer_data in additional_layers:
            elements.append(Paragraph(layer_name.title(), self.styles['CustomSubHeading']))
            
            # Add layer-specific information
            if isinstance(layer_data, dict) and 'metrics' in layer_data:
                metrics_text = "<br/>".join([f"<b>{k}:</b> {v}" for k, v in layer_data['metrics'].items()])
                elements.append(Paragraph(metrics_text, self.styles['CustomBody']))
            
            elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_recommendations_section(self, data: Dict) -> List:
        """Create recommendations and conclusions section"""
        elements = []
        
        title = Paragraph("Recommendations & Conclusions", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Generate recommendations based on analysis results
        recommendations = []
        
        # Vegetation-based recommendations
        if 'vegetation' in data and data['vegetation']:
            veg_health = data['vegetation'].get('metrics', {}).get('vegetation_health_index', 0)
            if veg_health < 0.4:
                recommendations.append(
                    "Consider vegetation restoration or enhancement programs to improve ecological health."
                )
            elif veg_health > 0.7:
                recommendations.append(
                    "Maintain current vegetation management practices to preserve high ecological value."
                )
        
        # Building-based recommendations
        if 'buildings' in data and data['buildings']:
            coverage = data['buildings'].get('metrics', {}).get('coverage_percentage', 0)
            if coverage > 60:
                recommendations.append(
                    "High building density detected. Consider green space development and urban heat mitigation."
                )
            elif coverage < 20:
                recommendations.append(
                    "Low building density indicates potential for planned development or conservation."
                )
        
        # General recommendations
        recommendations.extend([
            "Continue regular monitoring using satellite data to track changes over time.",
            "Integrate findings with local planning documents and regulations.",
            "Consider seasonal variations in vegetation and land use patterns.",
            "Validate satellite-derived data with ground truth observations where critical."
        ])
        
        # Add recommendations
        elements.append(Paragraph("<b>Key Recommendations:</b>", self.styles['CustomHeading']))
        for i, rec in enumerate(recommendations, 1):
            p = Paragraph(f"{i}. {rec}", self.styles['CustomBody'])
            elements.append(p)
            elements.append(Spacer(1, 0.1*inch))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Conclusions
        elements.append(Paragraph("<b>Conclusions:</b>", self.styles['CustomHeading']))
        
        conclusion_text = """
        This comprehensive geospatial analysis provides valuable insights for planning, monitoring, 
        and decision-making. The integration of multiple satellite datasets ensures robust and 
        reliable results. Regular re-analysis is recommended to track temporal changes and assess 
        the effectiveness of interventions.
        """
        elements.append(Paragraph(conclusion_text, self.styles['CustomBody']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Data sources and disclaimers
        elements.append(Paragraph("<b>Data Sources & Acknowledgments:</b>", self.styles['CustomSubHeading']))
        
        sources_text = """
        • <b>Sentinel-2:</b> European Space Agency (ESA) Copernicus Program<br/>
        • <b>MODIS:</b> NASA Terra and Aqua satellites<br/>
        • <b>Google Open Buildings:</b> Google Research<br/>
        • <b>FAO GAUL:</b> UN Food and Agriculture Organization<br/>
        • <b>Google Earth Engine:</b> Analysis platform
        """
        elements.append(Paragraph(sources_text, self.styles['CustomBody']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        disclaimer_text = """
        <i><b>Disclaimer:</b> This analysis is based on satellite remote sensing data and automated 
        algorithms. While every effort has been made to ensure accuracy, results should be validated 
        with ground observations for critical applications. Satellite data may be affected by cloud 
        cover, atmospheric conditions, and temporal variations.</i>
        """
        elements.append(Paragraph(disclaimer_text, self.styles['CustomBody']))
        
        return elements
    
    def _add_header_footer(self, canvas, doc):
        """Add modern header and footer to each page"""
        canvas.saveState()
        
        # Modern Header with gradient-like effect
        canvas.setFillColor(self.colors['primary'])
        canvas.rect(0.5*inch, A4[1] - 0.7*inch, A4[0] - 1*inch, 0.4*inch, fill=1, stroke=0)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 11)
        canvas.drawString(0.75*inch, A4[1] - 0.5*inch, "🛰️ GEE Geospatial Analysis Report")
        
        # Modern accent line
        canvas.setFillColor(self.colors['secondary'])
        canvas.rect(0.5*inch, A4[1] - 0.75*inch, A4[0] - 1*inch, 0.08*inch, fill=1, stroke=0)
        
        # Footer with modern design
        canvas.setFillColor(self.colors['light_bg'])
        canvas.rect(0.5*inch, 0.3*inch, A4[0] - 1*inch, 0.5*inch, fill=1, stroke=0)
        
        # Page number in circle
        canvas.setFillColor(self.colors['secondary'])
        canvas.circle(A4[0] - 1*inch, 0.55*inch, 0.18*inch, fill=1, stroke=0)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 11)
        page_text = f"{doc.page}"
        canvas.drawCentredString(A4[0] - 1*inch, 0.51*inch, page_text)
        
        # Generation date
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6B7280'))
        gen_date = datetime.now().strftime('%B %d, %Y')
        canvas.drawString(0.75*inch, 0.55*inch, f"Generated: {gen_date}")
        
        # Branding
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(self.colors['accent'])
        canvas.drawString(0.75*inch, 0.42*inch, "Earth Engine Intelligence Platform")
        
        canvas.restoreState()
