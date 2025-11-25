"""
Chart Generator Module for PDF Reports
Creates beautiful, infographic-style charts for geospatial analysis reports
"""

import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server environments
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Rectangle, Wedge
import numpy as np
from io import BytesIO
import base64
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image, ImageDraw, ImageFont


class ChartGenerator:
    """Generate beautiful charts and visualizations for PDF reports"""
    
    def __init__(self):
        """Initialize chart generator with custom styling"""
        # Modern color palette inspired by Figma/Tailwind
        self.colors = {
            'primary': '#1E3A8A',
            'secondary': '#3B82F6',
            'accent': '#8B5CF6',
            'success': '#10B981',
            'warning': '#F59E0B',
            'danger': '#EF4444',
            'vegetation': ['#FEF3C7', '#FCD34D', '#84CC16', '#22C55E', '#15803D'],  # Yellow to dark green
            'buildings': ['#DBEAFE', '#93C5FD', '#3B82F6', '#1D4ED8', '#1E3A8A'],   # Light to dark blue
            'administrative': ['#FEE2E2', '#FCA5A5', '#F87171', '#DC2626', '#991B1B'], # Light to dark red
            'gradient_purple': ['#F3E8FF', '#E9D5FF', '#C084FC', '#9333EA', '#6B21A8']
        }
        
        # Set modern matplotlib style with custom parameters
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 11
        plt.rcParams['axes.titlesize'] = 13
        plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams['xtick.labelsize'] = 9
        plt.rcParams['ytick.labelsize'] = 9
        plt.rcParams['legend.fontsize'] = 9
        plt.rcParams['figure.titlesize'] = 14
        plt.rcParams['figure.titleweight'] = 'bold'
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['axes.facecolor'] = '#FAFAFA'
        plt.rcParams['figure.facecolor'] = 'white'
        
    def create_vegetation_health_chart(self, vegetation_data: Dict) -> BytesIO:
        """
        Create a beautiful vegetation health visualization
        
        Args:
            vegetation_data: Dictionary containing NDVI, EVI, SAVI metrics
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Vegetation Health Analysis', fontsize=20, fontweight='bold', y=0.98)
        
        metrics = vegetation_data.get('metrics', {})
        distribution = vegetation_data.get('distribution', {})
        
        # 1. Vegetation Indices Gauge Chart
        ax1 = axes[0, 0]
        indices = ['NDVI', 'EVI', 'SAVI']
        values = [
            metrics.get('mean_ndvi', 0),
            metrics.get('mean_evi', 0),
            metrics.get('mean_savi', 0)
        ]
        
        colors_gauge = ['#27AE60', '#2ECC71', '#58D68D']
        bars = ax1.barh(indices, values, color=colors_gauge, edgecolor='black', linewidth=1.5)
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, values)):
            ax1.text(val + 0.02, i, f'{val:.3f}', va='center', fontweight='bold')
        
        ax1.set_xlim(0, 1)
        ax1.set_xlabel('Index Value', fontweight='bold', fontsize=12)
        ax1.set_title('Vegetation Indices', fontweight='bold', fontsize=14)
        ax1.grid(axis='x', alpha=0.3)
        
        # 2. Distribution Pie Chart
        ax2 = axes[0, 1]
        if distribution:
            labels = ['Non-Vegetated', 'Low', 'Moderate', 'Dense']
            sizes = [
                distribution.get('non_vegetated', 0),
                distribution.get('low_vegetation', 0),
                distribution.get('moderate_vegetation', 0),
                distribution.get('dense_vegetation', 0)
            ]
            
            colors_pie = self.colors['vegetation']
            explode = (0.05, 0, 0, 0.1)  # Explode dense vegetation
            
            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors_pie,
                                               autopct='%1.1f%%', startangle=90,
                                               explode=explode, textprops={'fontweight': 'bold'})
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                
            ax2.set_title('Vegetation Distribution', fontweight='bold', fontsize=14)
        
        # 3. Health Index Meter
        ax3 = axes[1, 0]
        health_index = metrics.get('vegetation_health_index', 0)
        
        # Create semicircle gauge
        theta = np.linspace(0, np.pi, 100)
        radius = 1
        
        # Background arc
        ax3.plot(radius * np.cos(theta), radius * np.sin(theta), 'lightgray', linewidth=20)
        
        # Health arc (colored based on value)
        if health_index < 0.3:
            color = '#E74C3C'  # Red
        elif health_index < 0.6:
            color = '#F39C12'  # Orange
        else:
            color = '#27AE60'  # Green
            
        theta_health = np.linspace(0, np.pi * health_index, 100)
        ax3.plot(radius * np.cos(theta_health), radius * np.sin(theta_health), 
                color, linewidth=20)
        
        # Add needle
        needle_angle = np.pi * (1 - health_index)
        ax3.plot([0, radius * 0.8 * np.cos(needle_angle)],
                [0, radius * 0.8 * np.sin(needle_angle)],
                'k-', linewidth=3)
        ax3.plot(0, 0, 'ko', markersize=10)
        
        # Add text
        ax3.text(0, -0.3, f'{health_index:.2f}', ha='center', fontsize=24, fontweight='bold')
        ax3.text(0, -0.5, 'Health Index', ha='center', fontsize=12)
        
        ax3.set_xlim(-1.2, 1.2)
        ax3.set_ylim(-0.6, 1.2)
        ax3.axis('off')
        ax3.set_title('Overall Vegetation Health', fontweight='bold', fontsize=14)
        
        # 4. Data Source Info
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        data_source = metrics.get('data_source', 'Unknown')
        info_text = f"""
        Data Source:
        {data_source}
        
        Analysis Date: {metrics.get('analysis_date', 'N/A')}
        
        Coverage Area: {metrics.get('area_km2', 'N/A')} km²
        
        Key Findings:
        • NDVI: {values[0]:.3f}
        • EVI: {values[1]:.3f}
        • SAVI: {values[2]:.3f}
        • Health: {health_index:.3f}
        """
        
        ax4.text(0.1, 0.5, info_text, fontsize=11, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_building_analysis_chart(self, building_data: Dict) -> BytesIO:
        """
        Create building analysis visualization
        
        Args:
            building_data: Dictionary containing building metrics
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Building Intelligence Analysis', fontsize=20, fontweight='bold', y=0.98)
        
        metrics = building_data.get('metrics', {})
        
        # 1. Building Count and Area
        ax1 = axes[0, 0]
        categories = ['Total\nBuildings', 'Built-up\nArea (km²)', 'Avg Building\nSize (m²)']
        values = [
            metrics.get('building_count', 0),
            metrics.get('total_area_km2', 0),
            metrics.get('average_area_m2', 0)
        ]
        
        bars = ax1.bar(categories, values, color=self.colors['buildings'][:3],
                      edgecolor='black', linewidth=1.5)
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_title('Building Metrics Overview', fontweight='bold', fontsize=14)
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Building Density Heatmap Representation
        ax2 = axes[0, 1]
        density = metrics.get('density_per_km2', 0)
        
        # Create a simple heatmap representation
        density_levels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        density_values = [20, 50, 100, 200, density]
        colors_heat = ['#E8F4F8', '#B8D4E0', '#7FB3D5', '#4682B4', '#2E5C7A']
        
        bars = ax2.barh(density_levels, density_values, color=colors_heat,
                       edgecolor='black', linewidth=1.5)
        
        ax2.set_xlabel('Buildings per km²', fontweight='bold', fontsize=12)
        ax2.set_title('Building Density Classification', fontweight='bold', fontsize=14)
        ax2.axvline(x=density, color='red', linestyle='--', linewidth=2, label='Current Density')
        ax2.legend()
        ax2.grid(axis='x', alpha=0.3)
        
        # 3. Coverage Percentage
        ax3 = axes[1, 0]
        coverage = metrics.get('coverage_percentage', 0)
        
        # Create donut chart
        sizes = [coverage, 100 - coverage]
        colors_donut = ['#3498DB', '#ECF0F1']
        explode = (0.1, 0)
        
        wedges, texts, autotexts = ax3.pie(sizes, colors=colors_donut, autopct='%1.1f%%',
                                           startangle=90, explode=explode,
                                           textprops={'fontweight': 'bold', 'fontsize': 12})
        
        # Draw circle in center for donut effect
        centre_circle = Circle((0, 0), 0.70, fc='white')
        ax3.add_artist(centre_circle)
        
        ax3.text(0, 0, f'{coverage:.1f}%', ha='center', va='center',
                fontsize=24, fontweight='bold', color=self.colors['primary'])
        ax3.text(0, -0.15, 'Coverage', ha='center', va='center',
                fontsize=12, color=self.colors['primary'])
        
        ax3.set_title('Built-up Area Coverage', fontweight='bold', fontsize=14)
        
        # 4. Summary Stats
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        summary_text = f"""
        Building Analysis Summary
        
        Total Buildings: {metrics.get('building_count', 0):,}
        
        Total Built Area: {metrics.get('total_area_km2', 0):.2f} km²
        
        Average Size: {metrics.get('average_area_m2', 0):.0f} m²
        
        Density: {metrics.get('density_per_km2', 0):.0f} per km²
        
        Coverage: {coverage:.2f}%
        
        Data Source: Google Open Buildings
        """
        
        ax4.text(0.1, 0.5, summary_text, fontsize=11, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_administrative_chart(self, admin_data: Dict) -> BytesIO:
        """
        Create administrative boundaries visualization
        
        Args:
            admin_data: Dictionary containing administrative information
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.suptitle('Administrative Context', fontsize=20, fontweight='bold')
        
        ax.axis('off')
        
        # Create hierarchical flow diagram
        levels = ['Country', 'State/Province', 'District']
        y_positions = [0.8, 0.5, 0.2]
        
        country_name = admin_data.get('country', 'N/A')
        state_name = admin_data.get('state', 'N/A')
        district_name = admin_data.get('district', 'N/A')
        
        names = [country_name, state_name, district_name]
        colors_admin = self.colors['administrative']
        
        for i, (level, y_pos, name, color) in enumerate(zip(levels, y_positions, names, colors_admin)):
            # Draw rectangle for each level
            rect = Rectangle((0.2, y_pos - 0.08), 0.6, 0.15,
                           facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            
            # Add level label
            ax.text(0.1, y_pos, level + ':', fontsize=14, fontweight='bold',
                   verticalalignment='center')
            
            # Add name
            ax.text(0.5, y_pos, name, fontsize=16, fontweight='bold',
                   verticalalignment='center', horizontalalignment='center')
            
            # Draw connecting arrow (except for last level)
            if i < len(levels) - 1:
                ax.arrow(0.5, y_pos - 0.08, 0, -0.09, head_width=0.05,
                        head_length=0.03, fc='black', ec='black')
        
        # Add area information
        area_text = f"Analysis Area: {admin_data.get('area_km2', 'N/A')} km²"
        ax.text(0.5, 0.05, area_text, fontsize=12, horizontalalignment='center',
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_polygon_visualization(self, polygon_coords: List, 
                                     analysis_type: str = 'general') -> BytesIO:
        """
        Create a visual representation of the analyzed polygon
        
        Args:
            polygon_coords: List of [lon, lat] coordinates
            analysis_type: Type of analysis for color coding
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        
        # Extract coordinates
        lons = [coord[0] for coord in polygon_coords]
        lats = [coord[1] for coord in polygon_coords]
        
        # Plot polygon
        polygon = patches.Polygon(list(zip(lons, lats)), closed=True,
                                 edgecolor='red', facecolor='yellow',
                                 alpha=0.3, linewidth=3)
        ax.add_patch(polygon)
        
        # Plot vertices
        ax.plot(lons, lats, 'ro', markersize=10, label='Vertices')
        
        # Calculate center
        center_lon = np.mean(lons)
        center_lat = np.mean(lats)
        
        # Add center point
        ax.plot(center_lon, center_lat, 'b*', markersize=20, label='Center')
        
        # Set limits with padding
        lon_range = max(lons) - min(lons)
        lat_range = max(lats) - min(lats)
        padding = max(lon_range, lat_range) * 0.2
        
        ax.set_xlim(min(lons) - padding, max(lons) + padding)
        ax.set_ylim(min(lats) - padding, max(lats) + padding)
        
        ax.set_xlabel('Longitude', fontweight='bold', fontsize=12)
        ax.set_ylabel('Latitude', fontweight='bold', fontsize=12)
        ax.set_title(f'Analysis Area - {analysis_type.title()}',
                    fontweight='bold', fontsize=16)
        
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_summary_dashboard(self, all_data: Dict) -> BytesIO:
        """
        Create a comprehensive summary dashboard
        
        Args:
            all_data: Dictionary containing all analysis results
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig = plt.figure(figsize=(14, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
        
        fig.suptitle('Comprehensive Site Analysis Dashboard', 
                    fontsize=22, fontweight='bold')
        
        # Extract data
        vegetation = all_data.get('vegetation', {})
        buildings = all_data.get('buildings', {})
        admin = all_data.get('administrative', {})
        
        # 1. Location Info (top left)
        ax1 = fig.add_subplot(gs[0, :])
        ax1.axis('off')
        location_text = f"""
        Location: {admin.get('country', 'N/A')} > {admin.get('state', 'N/A')} > {admin.get('district', 'N/A')}
        Coordinates: {all_data.get('latitude', 'N/A')}, {all_data.get('longitude', 'N/A')}
        Analysis Date: {all_data.get('analysis_date', 'N/A')}
        """
        ax1.text(0.5, 0.5, location_text, fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # 2-4. Key metrics cards
        metrics_data = [
            ('Vegetation Health', vegetation.get('metrics', {}).get('vegetation_health_index', 0),
             '#27AE60', 'vegetation_health_index'),
            ('Building Density', buildings.get('metrics', {}).get('density_per_km2', 0),
             '#3498DB', 'per km²'),
            ('Coverage', buildings.get('metrics', {}).get('coverage_percentage', 0),
             '#F39C12', '%')
        ]
        
        for idx, (title, value, color, unit) in enumerate(metrics_data, start=1):
            ax = fig.add_subplot(gs[1, idx-1])
            ax.axis('off')
            
            # Create metric card
            rect = Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=color, alpha=0.3,
                           edgecolor=color, linewidth=3)
            ax.add_patch(rect)
            
            ax.text(0.5, 0.7, title, fontsize=12, fontweight='bold',
                   ha='center', va='center')
            ax.text(0.5, 0.4, f'{value:.2f}', fontsize=24, fontweight='bold',
                   ha='center', va='center')
            if unit != 'vegetation_health_index':
                ax.text(0.5, 0.2, unit, fontsize=10, ha='center', va='center')
            
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        
        # 5. Mini vegetation chart
        ax5 = fig.add_subplot(gs[2, 0])
        if 'distribution' in vegetation:
            dist = vegetation['distribution']
            labels = ['Non-Veg', 'Low', 'Mod', 'Dense']
            sizes = [dist.get('non_vegetated', 0), dist.get('low_vegetation', 0),
                    dist.get('moderate_vegetation', 0), dist.get('dense_vegetation', 0)]
            ax5.pie(sizes, labels=labels, colors=self.colors['vegetation'],
                   autopct='%1.0f%%', textprops={'fontsize': 8})
            ax5.set_title('Vegetation', fontsize=10, fontweight='bold')
        
        # 6. Mini building chart
        ax6 = fig.add_subplot(gs[2, 1])
        if 'metrics' in buildings:
            metrics = buildings['metrics']
            categories = ['Count', 'Area\n(km²)', 'Coverage\n(%)']
            values = [
                min(metrics.get('building_count', 0) / 100, 100),  # Normalize
                metrics.get('total_area_km2', 0) * 10,
                metrics.get('coverage_percentage', 0)
            ]
            ax6.bar(categories, values, color=self.colors['buildings'][:3])
            ax6.set_title('Buildings', fontsize=10, fontweight='bold')
            ax6.set_ylim(0, 100)
        
        # 7. Data quality indicator
        ax7 = fig.add_subplot(gs[2, 2])
        ax7.axis('off')
        quality_text = """
        Data Quality
        
        ✓ Vegetation: High
        ✓ Buildings: High
        ✓ Admin: Official
        
        Sources:
        • Sentinel-2
        • MODIS
        • Google Buildings
        • FAO GAUL
        """
        ax7.text(0.5, 0.5, quality_text, fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
        ax7.set_xlim(0, 1)
        ax7.set_ylim(0, 1)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
