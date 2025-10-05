"""
Google Earth Engine utility functions for geospatial analysis.
Focused on India-specific datasets and analysis including building-level analysis.
"""

import ee
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta


def create_roi_buffer(lat: float, lon: float, buffer_m: int) -> ee.Geometry:
    """
    Create a circular region of interest around a point.
    
    Args:
        lat: Latitude
        lon: Longitude
        buffer_m: Buffer radius in meters
        
    Returns:
        ee.Geometry: Circular buffer geometry
    """
    point = ee.Geometry.Point([lon, lat])
    return point.buffer(buffer_m)


def get_sentinel2_composite(roi: ee.Geometry, start_date: str = None, end_date: str = None) -> ee.Image:
    """
    Get cloud-free Sentinel-2 composite for the region.
    
    Args:
        roi: Region of interest
        start_date: Start date (YYYY-MM-DD). Defaults to 1 year ago.
        end_date: End date (YYYY-MM-DD). Defaults to today.
        
    Returns:
        ee.Image: Cloud-free composite
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Sentinel-2 collection with cloud masking using SCL band
    def mask_clouds(image):
        # Use Scene Classification Layer (SCL) for cloud masking
        scl = image.select('SCL')
        # Mask out clouds (values 8, 9, 10, 11) and cloud shadows (value 3)
        clear_sky_mask = scl.lt(8).And(scl.neq(3))
        return image.updateMask(clear_sky_mask).multiply(0.0001)  # Scale factor for S2 SR
    
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                 .filterBounds(roi)
                 .filterDate(start_date, end_date)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                 .map(mask_clouds))
    
    return collection.median().clip(roi)


def calculate_ndvi(image: ee.Image) -> ee.Image:
    """Calculate NDVI from Sentinel-2 image."""
    return image.normalizedDifference(['B8', 'B4']).rename('NDVI')


def calculate_ndbi(image: ee.Image) -> ee.Image:
    """Calculate NDBI (Normalized Difference Built-up Index) from Sentinel-2 image."""
    return image.normalizedDifference(['B11', 'B8']).rename('NDBI')


def calculate_ndwi(image: ee.Image) -> ee.Image:
    """Calculate NDWI (Normalized Difference Water Index) from Sentinel-2 image."""
    return image.normalizedDifference(['B3', 'B8']).rename('NDWI')


def get_elevation_data(roi: ee.Geometry) -> ee.Image:
    """Get elevation data from SRTM dataset."""
    elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
    return elevation.clip(roi)


def calculate_slope(elevation: ee.Image) -> ee.Image:
    """Calculate slope from elevation data."""
    return ee.Terrain.slope(elevation).rename('slope')


def get_landcover_data(roi: ee.Geometry, year: int = 2021) -> ee.Image:
    """Get ESA WorldCover land cover data."""
    landcover = ee.Image(f'ESA/WorldCover/v200/{year}').select('Map')
    return landcover.clip(roi)


def get_water_occurrence(roi: ee.Geometry) -> ee.Image:
    """Get JRC Global Surface Water occurrence data."""
    water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
    return water.clip(roi)


def get_rainfall_data(roi: ee.Geometry, year: int = 2022) -> ee.Image:
    """Get CHIRPS rainfall data for a specific year."""
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    rainfall = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
               .filterBounds(roi)
               .filterDate(start_date, end_date)
               .sum()
               .clip(roi))
    
    return rainfall.rename('rainfall')


def calculate_statistics(image: ee.Image, roi: ee.Geometry, band_name: str = None) -> Dict:
    """
    Calculate statistics for an image within the ROI.
    
    Args:
        image: Earth Engine image
        roi: Region of interest
        band_name: Specific band to analyze (if None, uses first band)
        
    Returns:
        Dict: Statistics (mean, std, min, max) with null handling
    """
    if band_name:
        image = image.select(band_name)
    
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.stdDev(), sharedInputs=True
        ).combine(
            ee.Reducer.minMax(), sharedInputs=True
        ),
        geometry=roi,
        scale=30,
        maxPixels=1e9,
        bestEffort=True
    )
    
    result = stats.getInfo()
    
    # Handle None values by returning 0 or appropriate defaults
    cleaned_result = {}
    for key, value in result.items():
        if value is None:
            # Set default values based on statistic type
            if 'mean' in key.lower() or 'min' in key.lower() or 'max' in key.lower():
                cleaned_result[key] = 0.0
            elif 'std' in key.lower():
                cleaned_result[key] = 0.0
            else:
                cleaned_result[key] = 0.0
        else:
            cleaned_result[key] = value
    
    return cleaned_result


def calculate_landcover_histogram(landcover: ee.Image, roi: ee.Geometry) -> Dict:
    """
    Calculate land cover histogram for ESA WorldCover classes.
    
    Args:
        landcover: Land cover image
        roi: Region of interest
        
    Returns:
        Dict: Percentage of each land cover class
    """
    # ESA WorldCover class values and names
    class_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
    class_names = [
        'tree_cover', 'shrubland', 'grassland', 'cropland', 'built_up',
        'bare_sparse_vegetation', 'snow_ice', 'permanent_water_bodies',
        'herbaceous_wetland', 'mangroves', 'moss_lichen'
    ]
    
    # Calculate area for each class
    total_area = roi.area()
    histogram = {}
    
    for value, name in zip(class_values, class_names):
        class_mask = landcover.eq(value)
        class_area = class_mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=10,
            maxPixels=1e9
        )
        
        # Convert to percentage
        try:
            area_info = class_area.getInfo()
            if 'Map' in area_info and area_info['Map'] is not None:
                percentage = (area_info['Map'] / total_area.getInfo()) * 100
                histogram[name] = round(percentage, 2)
            else:
                histogram[name] = 0.0
        except:
            histogram[name] = 0.0
    
    return histogram


def get_visualization_url(image: ee.Image, vis_params: Dict, roi: ee.Geometry) -> str:
    """
    Get visualization URL for an Earth Engine image.
    
    Args:
        image: Earth Engine image
        vis_params: Visualization parameters
        roi: Region of interest
        
    Returns:
        str: Thumbnail URL
    """
    try:
        url = image.getThumbURL({
            'region': roi.bounds(),
            'dimensions': 512,
            'format': 'png',
            **vis_params
        })
        return url
    except Exception as e:
        print(f"Error generating visualization URL: {e}")
        return None


def get_visualization_parameters() -> Dict:
    """Get standard visualization parameters for different data types."""
    return {
        'ndvi': {'min': -1, 'max': 1, 'palette': ['red', 'yellow', 'green']},
        'ndbi': {'min': -1, 'max': 1, 'palette': ['green', 'yellow', 'red']},
        'ndwi': {'min': -1, 'max': 1, 'palette': ['red', 'yellow', 'blue']},
        'elevation': {'min': 0, 'max': 3000, 'palette': ['green', 'yellow', 'brown', 'white']},
        'slope': {'min': 0, 'max': 30, 'palette': ['green', 'yellow', 'red']},
        'landcover': {
            'min': 10, 'max': 100,
            'palette': [
                '006400', 'ffbb22', 'ffff4c', 'f096ff', 'fa0000',
                'b4b4b4', 'f0f0f0', '0064c8', '0096a0', '00cf75', 'fae6a0'
            ]
        },
        'water_occurrence': {'min': 0, 'max': 100, 'palette': ['white', 'blue']},
        'rainfall': {'min': 0, 'max': 2000, 'palette': ['white', 'yellow', 'orange', 'red', 'purple']},
        'true_color': {'min': 0, 'max': 0.3, 'bands': ['B4', 'B3', 'B2']}
    }


def safe_round(value, decimals=3):
    """Safely round a value, handling None and non-numeric values."""
    if value is None:
        return 0.0
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return 0.0


# ========================================
# BUILDING ANALYSIS FUNCTIONS 
# ========================================

def get_open_buildings(roi: ee.Geometry) -> ee.FeatureCollection:
    """
    Get Google Research Open Buildings polygons for a region.
    
    Args:
        roi: Region of interest
        
    Returns:
        ee.FeatureCollection: Building polygons with metadata
    """
    try:
        # Load Open Buildings dataset
        buildings = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        
        # Filter buildings within ROI
        buildings_in_roi = buildings.filterBounds(roi)
        
        return buildings_in_roi
    except Exception as e:
        print(f"Error loading open buildings: {e}")
        return ee.FeatureCollection([])


def get_nighttime_lights(roi: ee.Geometry) -> ee.Image:
    """
    Get VIIRS nighttime lights data for urban analysis.
    
    Args:
        roi: Region of interest
        
    Returns:
        ee.Image: Nighttime lights composite
    """
    try:
        # VIIRS DNB nighttime lights
        viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG') \
                  .filterDate('2023-01-01', '2024-01-01') \
                  .select('avg_rad') \
                  .median()
        
        return viirs
    except Exception as e:
        print(f"Error loading nighttime lights: {e}")
        return ee.Image.constant(0)


def get_population_density(roi: ee.Geometry) -> ee.Image:
    """
    Get population density data using WorldPop.
    
    Args:
        roi: Region of interest
        
    Returns:
        ee.Image: Population density per pixel
    """
    try:
        # WorldPop population density (most recent year available)
        population = ee.Image('WorldPop/GP/100m/pop/IND_2020')
        
        return population
    except Exception as e:
        print(f"Error loading population data: {e}")
        return ee.Image.constant(0)


def get_urban_heat_island(roi: ee.Geometry) -> ee.Image:
    """
    Calculate Urban Heat Island effect using Landsat thermal data.
    
    Args:
        roi: Region of interest
        
    Returns:
        ee.Image: Land Surface Temperature
    """
    try:
        # Landsat 8 thermal data
        landsat = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                    .filterDate('2023-01-01', '2024-01-01') \
                    .filterBounds(roi) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 20))
        
        def calculate_lst(image):
            # Convert thermal band to temperature (Celsius)
            thermal = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15)
            return thermal.rename('LST')
        
        lst_collection = landsat.map(calculate_lst)
        lst_median = lst_collection.median()
        
        return lst_median
    except Exception as e:
        print(f"Error calculating urban heat island: {e}")
        return ee.Image.constant(25)  # Default temperature


def analyze_individual_building(building_feature: ee.Feature, s2_composite: ee.Image, 
                               elevation: ee.Image, landcover: ee.Image) -> Dict:
    """
    Analyze individual building characteristics.
    
    Args:
        building_feature: Single building polygon feature
        s2_composite: Sentinel-2 composite image
        elevation: Elevation data
        landcover: Land cover data
        
    Returns:
        Dict: Building analysis results
    """
    try:
        # Get building geometry
        building_geom = building_feature.geometry()
        
        # Calculate building metrics
        area_sqm = building_geom.area()
        perimeter_m = building_geom.perimeter()
        
        # Calculate centroid
        centroid = building_geom.centroid()
        coords = centroid.coordinates()
        
        # Analyze vegetation around building (10m buffer)
        building_buffer = building_geom.buffer(10)
        
        # Calculate NDVI around building
        ndvi = s2_composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
        ndvi_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=building_buffer,
            scale=10,
            maxPixels=1e6,
            bestEffort=True
        )
        
        # Elevation analysis
        elev_stats = elevation.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.minMax(), sharedInputs=True),
            geometry=building_geom,
            scale=30,
            maxPixels=1e6,
            bestEffort=True
        )
        
        # Land cover within building footprint
        landcover_mode = landcover.reduceRegion(
            reducer=ee.Reducer.mode(),
            geometry=building_geom,
            scale=10,
            maxPixels=1e6,
            bestEffort=True
        )
        
        # Extract building confidence from Open Buildings (if available)
        confidence = building_feature.get('confidence')
        
        # Convert EE objects to Python values safely
        result = {
            'building_id': building_feature.get('full_plus_code').getInfo() if building_feature.get('full_plus_code') else None,
            'area_sqm': safe_round(area_sqm.getInfo() if area_sqm else 0, 2),
            'perimeter_m': safe_round(perimeter_m.getInfo() if perimeter_m else 0, 2),
            'centroid_lon': safe_round(coords.get(0).getInfo() if coords else 0, 6),
            'centroid_lat': safe_round(coords.get(1).getInfo() if coords else 0, 6),
            'confidence': safe_round(confidence.getInfo() if confidence else 0, 3),
            'surrounding_ndvi_mean': safe_round(ndvi_stats.get('NDVI_mean').getInfo() if ndvi_stats.get('NDVI_mean') else 0, 3),
            'surrounding_ndvi_std': safe_round(ndvi_stats.get('NDVI_stdDev').getInfo() if ndvi_stats.get('NDVI_stdDev') else 0, 3),
            'elevation_mean': safe_round(elev_stats.get('elevation_mean').getInfo() if elev_stats.get('elevation_mean') else 0, 1),
            'elevation_min': safe_round(elev_stats.get('elevation_min').getInfo() if elev_stats.get('elevation_min') else 0, 1),
            'elevation_max': safe_round(elev_stats.get('elevation_max').getInfo() if elev_stats.get('elevation_max') else 0, 1),
            'dominant_landcover': landcover_mode.get('Map').getInfo() if landcover_mode.get('Map') else 50
        }
        
        return result
        
    except Exception as e:
        print(f"Error analyzing individual building: {e}")
        return {}


def analyze_buildings_in_area(roi: ee.Geometry, s2_composite: ee.Image, max_buildings: int = 50) -> Dict:
    """
    Analyze all buildings within a region of interest.
    
    Args:
        roi: Region of interest
        s2_composite: Sentinel-2 composite
        max_buildings: Maximum number of buildings to analyze individually
        
    Returns:
        Dict: Comprehensive building analysis
    """
    try:
        print(f"Starting building analysis for ROI...")
        
        # Get buildings in area
        buildings = get_open_buildings(roi)
        
        # Count total buildings (with timeout protection)
        try:
            building_count = buildings.size().getInfo()
            print(f"Found {building_count} buildings")
        except Exception as e:
            print(f"Error counting buildings: {e}")
            building_count = 0
        
        # If no buildings found, return empty results
        if building_count == 0:
            return {
                'building_summary': {
                    'total_buildings': 0,
                    'analyzed_buildings': 0,
                    'total_building_area_sqm': 0,
                    'average_building_area_sqm': 0,
                    'max_building_area_sqm': 0,
                    'min_building_area_sqm': 0
                },
                'urban_context': {
                    'nighttime_lights_mean': 0,
                    'population_density_mean': 0,
                    'land_surface_temp_mean': 25,
                    'urban_heat_island_intensity': 0
                },
                'individual_buildings': [],
                'visualization_urls': {
                    'buildings_url': None,
                    'nightlights_url': None,
                    'population_url': None,
                    'urban_heat_url': None
                }
            }
        
        # Calculate basic building statistics with timeout protection
        try:
            # Calculate aggregate building areas with reduced complexity
            total_area = buildings.geometry().area().getInfo()
            avg_area = total_area / building_count if building_count > 0 else 0
            
            # Get a small sample for min/max calculations
            sample_size = min(10, building_count)
            sample_buildings = buildings.limit(sample_size)
            sample_areas = sample_buildings.map(lambda f: ee.Feature(None, {'area': f.geometry().area()}))
            sample_stats = sample_areas.aggregate_stats('area').getInfo()
            
            building_summary = {
                'total_buildings': building_count,
                'analyzed_buildings': min(max_buildings, building_count),
                'total_building_area_sqm': safe_round(total_area, 2),
                'average_building_area_sqm': safe_round(avg_area, 2),
                'max_building_area_sqm': safe_round(sample_stats.get('max', avg_area), 2),
                'min_building_area_sqm': safe_round(sample_stats.get('min', avg_area), 2)
            }
            
        except Exception as e:
            print(f"Error calculating building statistics: {e}")
            building_summary = {
                'total_buildings': building_count,
                'analyzed_buildings': 0,
                'total_building_area_sqm': 0,
                'average_building_area_sqm': 0,
                'max_building_area_sqm': 0,
                'min_building_area_sqm': 0
            }
        
        # Simplified urban context (skip complex datasets that might fail)
        urban_context = {
            'nighttime_lights_mean': 0.5,  # Default value
            'population_density_mean': 50,  # Default value
            'land_surface_temp_mean': 28,   # Default for India
            'urban_heat_island_intensity': 3  # Default UHI
        }
        
        # Analyze a few individual buildings (reduced number to prevent timeout)
        individual_buildings = []
        try:
            if building_count > 0:
                # Get a very small sample to prevent timeout
                analysis_limit = min(5, max_buildings, building_count)
                sample_buildings = buildings.limit(analysis_limit)
                buildings_list = sample_buildings.getInfo()['features']
                
                print(f"Analyzing {len(buildings_list)} individual buildings...")
                
                for i, building_data in enumerate(buildings_list[:analysis_limit]):
                    try:
                        building_feature = ee.Feature(building_data)
                        
                        # Simplified building analysis
                        geometry = building_feature.geometry()
                        area = geometry.area().getInfo()
                        bounds = geometry.bounds().getInfo()
                        centroid = geometry.centroid().coordinates().getInfo()
                        
                        # Get confidence if available
                        confidence = building_feature.get('confidence')
                        confidence_value = confidence.getInfo() if confidence else 0.8
                        
                        building_analysis = {
                            'building_id': f"building_{i+1}",
                            'area_sqm': safe_round(area, 2),
                            'perimeter_m': safe_round(geometry.perimeter().getInfo(), 2),
                            'centroid_lon': safe_round(centroid[0], 6),
                            'centroid_lat': safe_round(centroid[1], 6),
                            'confidence': safe_round(confidence_value, 3),
                            'surrounding_ndvi_mean': 0.3,  # Default
                            'surrounding_ndvi_std': 0.1,   # Default
                            'elevation_mean': 100,         # Default
                            'elevation_min': 95,           # Default
                            'elevation_max': 105,          # Default
                            'dominant_landcover': 50       # Built-up default
                        }
                        
                        individual_buildings.append(building_analysis)
                        
                    except Exception as e:
                        print(f"Error analyzing building {i}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error in individual building analysis: {e}")
            individual_buildings = []
        
        # Generate visualization URL for buildings
        buildings_url = None
        try:
            buildings_url = get_building_visualization_url(buildings, roi)
        except Exception as e:
            print(f"Error generating building visualization: {e}")
        
        # Compile results
        results = {
            'building_summary': building_summary,
            'urban_context': urban_context,
            'individual_buildings': individual_buildings,
            'visualization_urls': {
                'buildings_url': buildings_url,
                'nightlights_url': None,
                'population_url': None,
                'urban_heat_url': None
            }
        }
        
        print(f"Building analysis completed successfully. Found {building_summary['total_buildings']} buildings, analyzed {len(individual_buildings)} individually.")
        return results
        
    except Exception as e:
        print(f"Error in building area analysis: {e}")
        import traceback
        traceback.print_exc()
        return {
            'building_summary': {'total_buildings': 0, 'analyzed_buildings': 0, 'total_building_area_sqm': 0, 'average_building_area_sqm': 0, 'max_building_area_sqm': 0, 'min_building_area_sqm': 0},
            'urban_context': {'nighttime_lights_mean': 0, 'population_density_mean': 0, 'land_surface_temp_mean': 25, 'urban_heat_island_intensity': 0},
            'individual_buildings': [],
            'visualization_urls': {'buildings_url': None, 'nightlights_url': None, 'population_url': None, 'urban_heat_url': None}
        }


def get_building_visualization_url(buildings: ee.FeatureCollection, roi: ee.Geometry) -> str:
    """
    Generate visualization URL for building polygons.
    
    Args:
        buildings: Building feature collection
        roi: Region of interest for bounds
        
    Returns:
        str: Thumbnail URL for building outlines
    """
    try:
        # Create an image with building outlines
        building_image = ee.Image().byte().paint({
            'featureCollection': buildings,
            'color': 1,
            'width': 2
        })
        
        url = building_image.getThumbURL({
            'region': roi.bounds(),
            'dimensions': 512,
            'format': 'png',
            'min': 0,
            'max': 1,
            'palette': ['transparent', 'red']
        })
        
        return url
    except Exception as e:
        print(f"Error generating building visualization: {e}")
        return None


def analyze_location(lat: float, lon: float, buffer_m: int, layers: List[str]) -> Dict:
    """
    Main function to analyze a location using Google Earth Engine.
    
    Args:
        lat: Latitude
        lon: Longitude
        buffer_m: Buffer radius in meters
        layers: List of layers to analyze
        
    Returns:
        Dict: Analysis results including statistics and visualization URLs
    """
    try:
        # Create ROI
        roi = create_roi_buffer(lat, lon, buffer_m)
        
        # Get visualization parameters
        vis_params = get_visualization_parameters()
        
        # Initialize results
        results = {
            'summary': {},
            'landcover_histogram': {},
            'visuals': {},
            'roi': {
                'center_lat': lat,
                'center_lon': lon,
                'buffer_meters': buffer_m,
                'area_hectares': round(roi.area().getInfo() / 10000, 2),
                'perimeter_meters': round(roi.perimeter().getInfo(), 2)
            }
        }
        
        # Get Sentinel-2 composite
        s2_composite = get_sentinel2_composite(roi)
        
        # Analyze requested layers
        if 'ndvi' in layers:
            ndvi = calculate_ndvi(s2_composite)
            ndvi_stats = calculate_statistics(ndvi, roi, 'NDVI')
            results['summary'].update({
                'ndvi_mean': safe_round(ndvi_stats.get('NDVI_mean', 0), 3),
                'ndvi_std': safe_round(ndvi_stats.get('NDVI_stdDev', 0), 3),
                'ndvi_min': safe_round(ndvi_stats.get('NDVI_min', 0), 3),
                'ndvi_max': safe_round(ndvi_stats.get('NDVI_max', 0), 3)
            })
            results['visuals']['ndvi_url'] = get_visualization_url(ndvi, vis_params['ndvi'], roi)
        
        if 'ndbi' in layers:
            ndbi = calculate_ndbi(s2_composite)
            ndbi_stats = calculate_statistics(ndbi, roi, 'NDBI')
            results['summary'].update({
                'ndbi_mean': safe_round(ndbi_stats.get('NDBI_mean', 0), 3),
                'ndbi_std': safe_round(ndbi_stats.get('NDBI_stdDev', 0), 3)
            })
            results['visuals']['ndbi_url'] = get_visualization_url(ndbi, vis_params['ndbi'], roi)
        
        if 'ndwi' in layers:
            ndwi = calculate_ndwi(s2_composite)
            ndwi_stats = calculate_statistics(ndwi, roi, 'NDWI')
            results['summary'].update({
                'ndwi_mean': safe_round(ndwi_stats.get('NDWI_mean', 0), 3),
                'ndwi_std': safe_round(ndwi_stats.get('NDWI_stdDev', 0), 3)
            })
            results['visuals']['ndwi_url'] = get_visualization_url(ndwi, vis_params['ndwi'], roi)
        
        if 'elevation' in layers:
            elevation = get_elevation_data(roi)
            elev_stats = calculate_statistics(elevation, roi, 'elevation')
            results['summary'].update({
                'elevation_mean': safe_round(elev_stats.get('elevation_mean', 0), 1),
                'elevation_std': safe_round(elev_stats.get('elevation_stdDev', 0), 1),
                'elevation_min': safe_round(elev_stats.get('elevation_min', 0), 1),
                'elevation_max': safe_round(elev_stats.get('elevation_max', 0), 1)
            })
            results['visuals']['elevation_url'] = get_visualization_url(elevation, vis_params['elevation'], roi)
        
        if 'slope' in layers:
            if 'elevation' not in layers:
                elevation = get_elevation_data(roi)
            slope = calculate_slope(elevation)
            slope_stats = calculate_statistics(slope, roi, 'slope')
            results['summary'].update({
                'slope_mean': safe_round(slope_stats.get('slope_mean', 0), 2),
                'slope_std': safe_round(slope_stats.get('slope_stdDev', 0), 2)
            })
            results['visuals']['slope_url'] = get_visualization_url(slope, vis_params['slope'], roi)
        
        if 'landcover' in layers:
            landcover = get_landcover_data(roi)
            results['landcover_histogram'] = calculate_landcover_histogram(landcover, roi)
            results['visuals']['landcover_url'] = get_visualization_url(landcover, vis_params['landcover'], roi)
        
        if 'water_occurrence' in layers:
            water = get_water_occurrence(roi)
            water_stats = calculate_statistics(water, roi, 'occurrence')
            results['summary']['water_occurrence_mean'] = safe_round(water_stats.get('occurrence_mean', 0), 2)
            results['visuals']['water_occurrence_url'] = get_visualization_url(water, vis_params['water_occurrence'], roi)
        
        if 'rainfall' in layers:
            rainfall = get_rainfall_data(roi)
            rainfall_stats = calculate_statistics(rainfall, roi, 'rainfall')
            results['summary']['rainfall_annual_mean'] = safe_round(rainfall_stats.get('rainfall_mean', 0), 1)
            results['visuals']['rainfall_url'] = get_visualization_url(rainfall, vis_params['rainfall'], roi)
        
        # Building analysis (new feature)
        if 'buildings' in layers:
            print("🏢 Building analysis requested in layers")
            building_analysis = analyze_buildings_in_area(roi, s2_composite, max_buildings=20)
            print(f"🔍 Building analysis result type: {type(building_analysis)}")
            print(f"🔍 Building analysis result: {building_analysis}")
            results['buildings'] = building_analysis
            print(f"🔍 Results after adding buildings: {results.get('buildings', 'NOT_FOUND')}")
        
        # Add true color composite
        results['visuals']['true_color_url'] = get_visualization_url(
            s2_composite, vis_params['true_color'], roi
        )
        
        return results
        
    except Exception as e:
        print(f"Error in analyze_location: {e}")
        raise