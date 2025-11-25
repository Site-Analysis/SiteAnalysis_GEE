"""
Map Renderer Module for PDF Reports
Renders satellite imagery and map visualizations with polygon overlays
"""

import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server environments
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from io import BytesIO
from typing import List, Dict, Optional, Tuple
import requests
from PIL import Image
import io


class MapRenderer:
    """Render maps and satellite imagery for PDF reports"""
    
    def __init__(self):
        """Initialize map renderer"""
        self.tile_size = 256
        
    def render_polygon_on_map(self, polygon_coords: List[List[float]], 
                             title: str = "Analysis Area",
                             highlight_color: str = '#FF0000') -> BytesIO:
        """
        Render a polygon on a simple map background
        
        Args:
            polygon_coords: List of [lon, lat] coordinates
            title: Title for the map
            highlight_color: Color for the polygon
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        
        # Extract coordinates
        lons = [coord[0] for coord in polygon_coords]
        lats = [coord[1] for coord in polygon_coords]
        
        # Create polygon patch
        polygon = MplPolygon(list(zip(lons, lats)), closed=True,
                            edgecolor=highlight_color, facecolor=highlight_color,
                            alpha=0.4, linewidth=3, linestyle='-')
        ax.add_patch(polygon)
        
        # Add vertex markers
        ax.plot(lons, lats, 'o', color=highlight_color, markersize=8,
               markeredgecolor='white', markeredgewidth=2, label='Vertices')
        
        # Calculate and mark center
        center_lon = np.mean(lons)
        center_lat = np.mean(lats)
        ax.plot(center_lon, center_lat, '*', color='blue', markersize=20,
               markeredgecolor='white', markeredgewidth=2, label='Center', zorder=10)
        
        # Add coordinate labels
        for i, (lon, lat) in enumerate(zip(lons, lats)):
            ax.annotate(f'P{i+1}\n({lon:.4f}, {lat:.4f})',
                       xy=(lon, lat), xytext=(10, 10),
                       textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                       fontsize=8, fontweight='bold')
        
        # Set limits with padding
        lon_range = max(lons) - min(lons)
        lat_range = max(lats) - min(lats)
        padding = max(lon_range, lat_range) * 0.15
        
        ax.set_xlim(min(lons) - padding, max(lons) + padding)
        ax.set_ylim(min(lats) - padding, max(lats) + padding)
        
        # Styling
        ax.set_xlabel('Longitude (°)', fontweight='bold', fontsize=12)
        ax.set_ylabel('Latitude (°)', fontweight='bold', fontsize=12)
        ax.set_title(title, fontweight='bold', fontsize=16, pad=20)
        
        ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
        ax.set_facecolor('#E8F4F8')
        ax.legend(loc='upper right', fontsize=10)
        
        # Add north arrow
        self._add_north_arrow(ax, 0.95, 0.95)
        
        # Add scale bar
        self._add_scale_bar(ax, lon_range, lat_range)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def render_point_location(self, lat: float, lon: float,
                            buffer_meters: int = 750,
                            title: str = "Analysis Location") -> BytesIO:
        """
        Render a point location with buffer circle
        
        Args:
            lat: Latitude
            lon: Longitude
            buffer_meters: Buffer radius in meters
            title: Title for the map
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        
        # Convert buffer from meters to degrees (approximate)
        buffer_deg = buffer_meters / 111000  # 1 degree ≈ 111km
        
        # Create circle for buffer zone
        circle = plt.Circle((lon, lat), buffer_deg, color='#3498DB',
                          alpha=0.3, linewidth=2, edgecolor='#2980B9',
                          label=f'{buffer_meters}m Buffer')
        ax.add_patch(circle)
        
        # Add center point
        ax.plot(lon, lat, 'r*', markersize=30, markeredgecolor='white',
               markeredgewidth=2, label='Analysis Point', zorder=10)
        
        # Add coordinate label
        ax.annotate(f'({lon:.4f}°, {lat:.4f}°)',
                   xy=(lon, lat), xytext=(0, -buffer_deg * 1.5),
                   textcoords='data',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
                   fontsize=11, fontweight='bold', ha='center')
        
        # Set limits
        padding = buffer_deg * 1.3
        ax.set_xlim(lon - padding, lon + padding)
        ax.set_ylim(lat - padding, lat + padding)
        
        # Styling
        ax.set_xlabel('Longitude (°)', fontweight='bold', fontsize=12)
        ax.set_ylabel('Latitude (°)', fontweight='bold', fontsize=12)
        ax.set_title(title, fontweight='bold', fontsize=16, pad=20)
        
        ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
        ax.set_facecolor('#E8F4F8')
        ax.legend(loc='upper right', fontsize=10)
        ax.set_aspect('equal')
        
        # Add north arrow
        self._add_north_arrow(ax, 0.95, 0.95)
        
        # Add scale bar (showing buffer size)
        ax.text(0.05, 0.05, f'Buffer Radius: {buffer_meters}m',
               transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
               fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def render_satellite_visualization(self, url: str, 
                                      title: str = "Satellite Imagery") -> Optional[BytesIO]:
        """
        Fetch and render satellite visualization from Earth Engine
        
        Args:
            url: Earth Engine visualization URL
            title: Title for the image
            
        Returns:
            BytesIO: PNG image buffer or None if fetch fails
        """
        try:
            # Fetch the image from Earth Engine
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Open image
            img = Image.open(io.BytesIO(response.content))
            
            # Create figure
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            
            # Display image
            ax.imshow(img)
            ax.axis('off')
            ax.set_title(title, fontweight='bold', fontsize=16, pad=10)
            
            # Add watermark
            ax.text(0.95, 0.05, 'Earth Engine Data',
                   transform=ax.transAxes, fontsize=8,
                   verticalalignment='bottom', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
            
            plt.tight_layout()
            
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            print(f"Error fetching satellite visualization: {e}")
            return None
    
    def create_multi_layer_visualization(self, visualization_urls: Dict[str, str],
                                        polygon_coords: Optional[List] = None) -> BytesIO:
        """
        Create a multi-panel visualization showing different analysis layers
        
        Args:
            visualization_urls: Dictionary of layer names to URLs
            polygon_coords: Optional polygon coordinates to overlay
            
        Returns:
            BytesIO: PNG image buffer
        """
        num_layers = len(visualization_urls)
        
        # Determine grid layout
        if num_layers <= 2:
            rows, cols = 1, num_layers
            figsize = (12, 6)
        elif num_layers <= 4:
            rows, cols = 2, 2
            figsize = (12, 12)
        else:
            rows = (num_layers + 2) // 3
            cols = 3
            figsize = (14, 5 * rows)
        
        fig, axes = plt.subplots(rows, cols, figsize=figsize)
        fig.suptitle('Multi-Layer Analysis Visualization', fontsize=18, fontweight='bold')
        
        # Flatten axes for easier indexing
        if num_layers == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if num_layers > 1 else [axes]
        
        # Plot each layer
        for idx, (layer_name, url) in enumerate(visualization_urls.items()):
            if idx >= len(axes):
                break
                
            ax = axes[idx]
            
            try:
                # Fetch image
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content))
                
                # Display
                ax.imshow(img)
                ax.set_title(layer_name.replace('_', ' ').title(),
                           fontweight='bold', fontsize=12)
                ax.axis('off')
                
            except Exception as e:
                ax.text(0.5, 0.5, f'Unable to load\n{layer_name}',
                       ha='center', va='center', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='lightgray'))
                ax.set_title(layer_name.replace('_', ' ').title(),
                           fontweight='bold', fontsize=12)
                ax.axis('off')
        
        # Hide unused subplots
        for idx in range(num_layers, len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def _add_north_arrow(self, ax, x: float, y: float):
        """Add a north arrow to the map"""
        # Transform from axes coordinates to data coordinates
        trans = ax.transAxes
        
        # Draw arrow
        arrow = patches.FancyArrowPatch((x, y - 0.05), (x, y),
                                       transform=trans,
                                       arrowstyle='->,head_width=0.4,head_length=0.8',
                                       color='black', linewidth=2)
        ax.add_patch(arrow)
        
        # Add 'N' label
        ax.text(x, y + 0.02, 'N', transform=trans,
               fontsize=14, fontweight='bold', ha='center', va='bottom')
    
    def _add_scale_bar(self, ax, lon_range: float, lat_range: float):
        """Add a scale bar to the map"""
        # Calculate scale bar length (approximate)
        scale_km = int(lon_range * 111)  # Convert degrees to km (approximate)
        
        # Round to nice number
        if scale_km < 1:
            scale_km = 1
        elif scale_km < 5:
            scale_km = 5
        elif scale_km < 10:
            scale_km = 10
        else:
            scale_km = (scale_km // 10) * 10
        
        # Add scale bar
        ax.text(0.05, 0.95, f'Scale: ~{scale_km} km',
               transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
               fontsize=10, fontweight='bold', verticalalignment='top')
    
    def create_comparison_view(self, before_url: Optional[str], 
                              after_url: Optional[str],
                              title: str = "Temporal Comparison") -> BytesIO:
        """
        Create a side-by-side comparison view
        
        Args:
            before_url: URL for before/baseline image
            after_url: URL for after/current image
            title: Title for the comparison
            
        Returns:
            BytesIO: PNG image buffer
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        fig.suptitle(title, fontsize=18, fontweight='bold')
        
        labels = ['Baseline/Before', 'Current/After']
        urls = [before_url, after_url]
        
        for ax, label, url in zip(axes, labels, urls):
            if url:
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    img = Image.open(io.BytesIO(response.content))
                    ax.imshow(img)
                except:
                    ax.text(0.5, 0.5, 'Image not available',
                           ha='center', va='center',
                           bbox=dict(boxstyle='round', facecolor='lightgray'))
            else:
                ax.text(0.5, 0.5, 'No data available',
                       ha='center', va='center',
                       bbox=dict(boxstyle='round', facecolor='lightgray'))
            
            ax.set_title(label, fontweight='bold', fontsize=14)
            ax.axis('off')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
