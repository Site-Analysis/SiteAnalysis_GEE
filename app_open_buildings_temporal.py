from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
import ee
import geemap
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

# Load environment variables and initialize Earth Engine
load_dotenv()
try:
    ee.Initialize()
    print("Earth Engine initialized successfully!")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")
    raise

app = FastAPI(
    title="Google Open Buildings Temporal Analysis API",
    description="API for accessing Google Research Open Buildings Temporal dataset with building heights, presence, and fractional counts",
    version="1.0.0"
)

# Helper functions for region handling (borrowed from VIIRS app)
def _get_district_bounds_from_gaul(district_name: str, state_name: Optional[str] = None) -> Optional[ee.Geometry]:
    """Get district bounds from FAO GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Filter by district name
        district_filter = ee.Filter.stringContains('ADM2_NAME', district_name)
        
        # Add state filter if provided for more precision
        if state_name:
            state_filter = ee.Filter.stringContains('ADM1_NAME', state_name)
            combined_filter = ee.Filter.And(district_filter, state_filter)
        else:
            combined_filter = district_filter
        
        matched_districts = india_boundaries.filter(combined_filter)
        
        # Check if any districts found
        count = matched_districts.size().getInfo()
        if count == 0:
            return None
        
        # Get bounds of the matched district(s)
        bounds = matched_districts.geometry().bounds()
        return bounds
        
    except Exception as e:
        print(f"Error getting district bounds: {e}")
        return None

def _get_state_bounds_from_gaul(state_name: str) -> Optional[ee.Geometry]:
    """Get state bounds from FAO GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Filter by state name
        state_boundaries = india_boundaries.filter(
            ee.Filter.stringContains('ADM1_NAME', state_name)
        )
        
        # Check if any states found
        count = state_boundaries.size().getInfo()
        if count == 0:
            return None
        
        # Get bounds of the matched state
        bounds = state_boundaries.geometry().bounds()
        return bounds
        
    except Exception as e:
        print(f"Error getting state bounds: {e}")
        return None

def _get_region_bounds(region: str, west: Optional[float], south: Optional[float], 
                      east: Optional[float], north: Optional[float], 
                      state_name: Optional[str] = None) -> ee.Geometry:
    """Get region bounds, supporting custom coordinates, predefined regions, and GAUL districts/states."""
    # If custom coordinates provided, use them
    if all(coord is not None for coord in [west, south, east, north]):
        return ee.Geometry.Rectangle([west, south, east, north])
    
    # Use predefined regions first
    predefined_regions = {
        "india": [68.0, 6.0, 97.0, 37.0],
        "mumbai": [72.7, 18.8, 73.2, 19.3],
        "delhi": [76.8, 28.4, 77.5, 28.9],
        "bangalore": [77.4, 12.8, 77.8, 13.2],
        "kolkata": [88.2, 22.4, 88.5, 22.7],
        "chennai": [80.1, 12.8, 80.3, 13.2],
        "hyderabad": [78.3, 17.3, 78.6, 17.5],
        "pune": [73.7, 18.4, 73.9, 18.6],
        "ahmedabad": [72.4, 23.0, 72.7, 23.1],
        "jaipur": [75.7, 26.8, 75.9, 27.0]
    }
    
    region_key = region.lower()
    if region_key in predefined_regions:
        coords = predefined_regions[region_key]
        return ee.Geometry.Rectangle(coords)
    
    # Try to find district in GAUL dataset
    district_bounds = _get_district_bounds_from_gaul(region, state_name)
    if district_bounds is not None:
        return district_bounds
    
    # Try to find state in GAUL dataset
    state_bounds = _get_state_bounds_from_gaul(region)
    if state_bounds is not None:
        return state_bounds
    
    # Default to India if nothing found
    print(f"Region '{region}' not found in predefined cities or GAUL dataset. Using India bounds.")
    return ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])

def _get_region_bounds_with_zoom(region: str, west: Optional[float], south: Optional[float], 
                                east: Optional[float], north: Optional[float], 
                                state_name: Optional[str] = None) -> Dict[str, Any]:
    """Get region bounds with appropriate zoom level."""
    bounds = _get_region_bounds(region, west, south, east, north, state_name)
    
    # Determine zoom level based on region type
    if region.lower() == "india":
        zoom_level = 5
    elif all(coord is not None for coord in [west, south, east, north]):
        zoom_level = 8  # Custom coordinates
    elif region.lower() in ["mumbai", "delhi", "bangalore", "kolkata", "chennai", "hyderabad", "pune", "ahmedabad", "jaipur"]:
        zoom_level = 12  # Predefined cities - higher zoom for buildings
    else:
        # Assume it's a district or state from GAUL - use moderate zoom
        zoom_level = 10
    
    return {"bounds": bounds, "zoom": zoom_level}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Google Open Buildings Temporal Analysis API",
        "description": "Access Google Research Open Buildings Temporal dataset with building data over time",
        "dataset": "GOOGLE/Research/open-buildings-temporal/v1",
        "pixel_size": "Variable resolution",
        "temporal_coverage": "Multi-temporal building data",
        "available_bands": {
            "building_fractional_count": "Source data for building counts (0-0.0216)",
            "building_height": "Building height relative to terrain (0-100m)", 
            "building_presence": "Model confidence for building presence (0-1)"
        },
        "endpoints": [
            "/temporal-health",
            "/temporal-check-data",
            "/temporal-building-analysis",
            "/temporal-height-analysis",
            "/temporal-presence-analysis", 
            "/temporal-count-analysis",
            "/temporal-time-series",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/temporal-health")
async def health_check():
    """Check if Earth Engine and Open Buildings Temporal dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test Open Buildings Temporal dataset access
        temporal_dataset = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1')
        
        # Get collection size and date range
        collection_size = temporal_dataset.size().getInfo()
        
        if collection_size > 0:
            # Get latest available image
            latest_image = temporal_dataset.sort('system:time_start', False).first()
            latest_date = ee.Date(latest_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            
            # Get first image
            first_image = temporal_dataset.sort('system:time_start').first()
            first_date = ee.Date(first_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            
            # Get available bands
            band_names = latest_image.bandNames().getInfo()
        else:
            latest_date = "No data"
            first_date = "No data"
            band_names = []
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_result": test_result,
            "dataset": "GOOGLE/Research/open-buildings-temporal/v1",
            "collection_size": collection_size,
            "date_range": f"{first_date} to {latest_date}" if collection_size > 0 else "No temporal data",
            "available_bands": band_names,
            "pixel_size": "Variable resolution (temporal dataset)",
            "band_count": len(band_names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/temporal-check-data")
async def check_temporal_data(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Check Open Buildings Temporal data availability for specified region and time period."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load Open Buildings Temporal collection
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        # Get collection statistics
        image_count = temporal_collection.size().getInfo()
        
        if image_count == 0:
            return {
                "success": False,
                "message": f"No Open Buildings Temporal images found for {region} between {start_date} and {end_date}",
                "suggestion": "Try expanding date range or different region"
            }
        
        # Get first and last image dates
        first_image = temporal_collection.sort('system:time_start').first()
        last_image = temporal_collection.sort('system:time_start', False).first()
        
        first_date = ee.Date(first_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        last_date = ee.Date(last_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        
        # Get sample image properties
        sample_image = temporal_collection.first()
        band_names = sample_image.bandNames().getInfo()
        
        # Sample building data from representative area with error handling
        try:
            building_stats = sample_image.select(['building_presence', 'building_height', 'building_fractional_count']).reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,  # Coarser scale for initial check
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
        except Exception as reduce_error:
            # Fallback to smaller sample area
            centroid = bounds.centroid()
            sample_area = centroid.buffer(2000)  # 2km buffer
            
            building_stats = sample_image.select(['building_presence', 'building_height']).reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=sample_area,
                scale=50,
                maxPixels=1e6,
                bestEffort=True
            ).getInfo()
        
        return {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "total_images": image_count,
            "actual_date_range": f"{first_date} to {last_date}",
            "available_bands": band_names,
            "sample_building_stats": building_stats,
            "temporal_resolution": "Multi-temporal dataset",
            "note": "Sample statistics from representative area within region"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking temporal data: {str(e)}")

@app.get("/temporal-building-analysis")
async def get_temporal_building_analysis(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate temporal building analysis map"),
    composite_method: str = Query("median", description="Composite method: median, mean, max"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get comprehensive temporal buildings analysis for specified region and time period."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load temporal buildings collection
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        image_count = temporal_collection.size().getInfo()
        
        if image_count == 0:
            return {"success": False, "message": "No temporal building data found for this region and time period"}
        
        # Create composite based on method
        if composite_method == "median":
            composite_image = temporal_collection.median()
        elif composite_method == "mean":
            composite_image = temporal_collection.mean()
        elif composite_method == "max":
            composite_image = temporal_collection.max()
        else:
            composite_image = temporal_collection.median()
        
        composite_image = composite_image.clip(bounds)
        
        # Calculate comprehensive building statistics with error handling
        all_bands = composite_image.select(['building_presence', 'building_height', 'building_fractional_count'])
        
        try:
            building_stats = all_bands.reduceRegion(
                reducer=ee.Reducer.minMax().combine(
                    ee.Reducer.mean().combine(
                        ee.Reducer.count(), sharedInputs=True
                    ), sharedInputs=True
                ),
                geometry=bounds,
                scale=50,  # Balance between detail and computation
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
        except Exception:
            # Fallback with coarser resolution
            building_stats = all_bands.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=200,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
        
        # Process statistics
        processed_stats = {
            "building_presence": {
                "min": building_stats.get('building_presence_min', 0),
                "max": building_stats.get('building_presence_max', 0),
                "mean": building_stats.get('building_presence_mean', 0),
                "count": building_stats.get('building_presence_count', 0),
                "description": "Model confidence for building presence (0-1, uncalibrated)"
            },
            "building_height": {
                "min": building_stats.get('building_height_min', 0),
                "max": building_stats.get('building_height_max', 0),
                "mean": building_stats.get('building_height_mean', 0),
                "count": building_stats.get('building_height_count', 0),
                "description": "Building height relative to terrain (0-100m)"
            },
            "building_fractional_count": {
                "min": building_stats.get('building_fractional_count_min', 0),
                "max": building_stats.get('building_fractional_count_max', 0),
                "mean": building_stats.get('building_fractional_count_mean', 0),
                "count": building_stats.get('building_fractional_count_count', 0),
                "description": "Fractional building count per pixel (0-0.0216)"
            }
        }
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "images_used": image_count,
            "composite_method": composite_method,
            "building_statistics": processed_stats,
            "dataset": "GOOGLE/Research/open-buildings-temporal/v1"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_temporal_buildings_map(composite_image, region, zoom_level, bounds, composite_method)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing temporal buildings: {str(e)}")

@app.get("/temporal-height-analysis")
async def get_temporal_height_analysis(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    height_threshold: float = Query(15.0, description="Minimum building height in meters"),
    include_map: bool = Query(True, description="Generate temporal building height map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze temporal building heights in the specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load temporal buildings data
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        if temporal_collection.size().getInfo() == 0:
            return {"success": False, "message": "No temporal building data found"}
        
        # Create height composite (use max to capture tallest buildings over time)
        height_composite = temporal_collection.select('building_height').max().clip(bounds)
        
        # Filter buildings above threshold
        tall_buildings = height_composite.gte(height_threshold)
        
        # Calculate height statistics with error handling
        try:
            height_stats = height_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(
                    ee.Reducer.mean().combine(
                        ee.Reducer.percentile([25, 50, 75, 90, 95]), sharedInputs=True
                    ), sharedInputs=True
                ),
                geometry=bounds,
                scale=50,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
            # Count tall buildings area
            tall_building_area = tall_buildings.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=50,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
        except Exception:
            # Simplified fallback
            height_stats = height_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e6,
                bestEffort=True
            ).getInfo()
            tall_building_area = {"building_height": 0}
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "height_threshold_meters": height_threshold,
            "height_statistics": {
                "min_height": height_stats.get('building_height_min', 0),
                "max_height": height_stats.get('building_height_max', 0),
                "mean_height": height_stats.get('building_height_mean', 0),
                "percentiles": {
                    "25th": height_stats.get('building_height_p25', 0),
                    "50th_median": height_stats.get('building_height_p50', 0),
                    "75th": height_stats.get('building_height_p75', 0),
                    "90th": height_stats.get('building_height_p90', 0),
                    "95th": height_stats.get('building_height_p95', 0)
                }
            },
            "tall_buildings_area_m2": tall_building_area.get('building_height', 0),
            "composite_method": "maximum (tallest over time period)",
            "units": "meters"
        }
        
        if include_map:
            map_result = await _generate_temporal_height_map(height_composite, tall_buildings, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing temporal building heights: {str(e)}")

@app.get("/temporal-presence-analysis")
async def get_temporal_presence_analysis(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    confidence_threshold: float = Query(0.8, description="Minimum building presence confidence (0-1)"),
    include_map: bool = Query(True, description="Generate temporal building presence map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze temporal building presence confidence in the specified region."""
    try:
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        if temporal_collection.size().getInfo() == 0:
            return {"success": False, "message": "No temporal building data found"}
        
        # Create presence composite (use max to capture highest confidence over time)
        presence_composite = temporal_collection.select('building_presence').max().clip(bounds)
        
        # Create high-confidence building mask
        high_confidence_buildings = presence_composite.gte(confidence_threshold)
        
        try:
            # Calculate presence statistics
            presence_stats = presence_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(
                    ee.Reducer.mean().combine(
                        ee.Reducer.percentile([10, 25, 50, 75, 90]), sharedInputs=True
                    ), sharedInputs=True
                ),
                geometry=bounds,
                scale=50,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
            # Calculate area of high-confidence buildings
            high_confidence_area = high_confidence_buildings.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=50,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
        except Exception:
            presence_stats = presence_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e6,
                bestEffort=True
            ).getInfo()
            high_confidence_area = {"building_presence": 0}
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "confidence_threshold": confidence_threshold,
            "presence_statistics": {
                "min_confidence": presence_stats.get('building_presence_min', 0),
                "max_confidence": presence_stats.get('building_presence_max', 0),
                "mean_confidence": presence_stats.get('building_presence_mean', 0),
                "percentiles": {
                    "10th": presence_stats.get('building_presence_p10', 0),
                    "25th": presence_stats.get('building_presence_p25', 0),
                    "50th_median": presence_stats.get('building_presence_p50', 0),
                    "75th": presence_stats.get('building_presence_p75', 0),
                    "90th": presence_stats.get('building_presence_p90', 0)
                }
            },
            "high_confidence_building_area_m2": high_confidence_area.get('building_presence', 0),
            "composite_method": "maximum (highest confidence over time period)",
            "note": "Confidence values are uncalibrated model outputs for relative ranking only"
        }
        
        if include_map:
            map_result = await _generate_temporal_presence_map(presence_composite, high_confidence_buildings, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing temporal building presence: {str(e)}")

@app.get("/temporal-count-analysis")
async def get_temporal_count_analysis(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate temporal building count map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze temporal building fractional counts in the specified region."""
    try:
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        if temporal_collection.size().getInfo() == 0:
            return {"success": False, "message": "No temporal building data found"}
        
        # Create fractional count composite (use mean for average building density over time)
        count_composite = temporal_collection.select('building_fractional_count').mean().clip(bounds)
        
        try:
            # Calculate fractional count statistics
            count_stats = count_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(
                    ee.Reducer.mean().combine(
                        ee.Reducer.sum().combine(
                            ee.Reducer.count(), sharedInputs=True
                        ), sharedInputs=True
                    ), sharedInputs=True
                ),
                geometry=bounds,
                scale=25,  # Higher resolution for count data
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
        except Exception:
            count_stats = count_composite.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
        
        # Estimate total building count from fractional counts
        total_fractional_count = count_stats.get('building_fractional_count_sum', 0)
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "count_statistics": {
                "min_fractional_count": count_stats.get('building_fractional_count_min', 0),
                "max_fractional_count": count_stats.get('building_fractional_count_max', 0),
                "mean_fractional_count": count_stats.get('building_fractional_count_mean', 0),
                "total_fractional_sum": total_fractional_count,
                "pixels_with_buildings": count_stats.get('building_fractional_count_count', 0)
            },
            "estimated_building_count": round(total_fractional_count) if total_fractional_count else 0,
            "composite_method": "mean (average density over time period)",
            "note": "Building counts derived from fractional count data - see dataset documentation for methodology"
        }
        
        if include_map:
            map_result = await _generate_temporal_count_map(count_composite, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing temporal building counts: {str(e)}")

@app.get("/temporal-time-series")
async def get_temporal_time_series(
    start_date: str = Query("2020-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    band: str = Query("building_presence", description="Band for time series: building_presence, building_height, or building_fractional_count"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get time series data for building metrics over specified period."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Validate band
        valid_bands = ['building_presence', 'building_height', 'building_fractional_count']
        if band not in valid_bands:
            raise HTTPException(status_code=400, detail=f"Invalid band '{band}'. Valid bands: {valid_bands}")
        
        # Load collection
        temporal_collection = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds) \
            .select(band)
        
        # Get time series values
        def get_image_stats(image):
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=bounds,
                scale=100,  # Coarser scale for time series
                maxPixels=1e6,
                bestEffort=True
            )
            date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
            return ee.Feature(None, {
                'date': date,
                f'{band}_mean': stats.get(band)
            })
        
        time_series = temporal_collection.map(get_image_stats).getInfo()
        
        # Process results
        dates = []
        values = []
        
        for feature in time_series['features']:
            props = feature['properties']
            if props[f'{band}_mean'] is not None:
                dates.append(props['date'])
                values.append(props[f'{band}_mean'])
        
        return {
            "success": True,
            "region": region,
            "building_band": band,
            "date_range": f"{start_date} to {end_date}",
            "data_points": len(dates),
            "time_series": {
                "dates": dates,
                "values": values
            },
            "statistics": {
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "mean": sum(values) / len(values) if values else None
            },
            "dataset": "GOOGLE/Research/open-buildings-temporal/v1"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating time series: {str(e)}")

@app.get("/gaul-search")
async def search_gaul_regions(
    search_term: str = Query(..., description="Search for district or state name"),
    search_type: str = Query("both", description="Search type: state, district, or both"),
    limit: int = Query(20, description="Limit number of results", le=100)
):
    """Search for districts or states in GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        results = {
            "search_term": search_term,
            "states": [],
            "districts": []
        }
        
        # Search states
        if search_type in ["state", "both"]:
            state_matches = india_boundaries.filter(
                ee.Filter.stringContains('ADM1_NAME', search_term)
            ).select(['ADM1_NAME', 'ADM1_CODE']).distinct(['ADM1_NAME']).limit(10)
            
            state_list = state_matches.getInfo()
            for feature in state_list['features']:
                props = feature['properties']
                results["states"].append({
                    "name": props['ADM1_NAME'],
                    "code": props['ADM1_CODE'],
                    "type": "state",
                    "usage_example": f"?region={props['ADM1_NAME']}"
                })
        
        # Search districts
        if search_type in ["district", "both"]:
            district_matches = india_boundaries.filter(
                ee.Filter.stringContains('ADM2_NAME', search_term)
            ).limit(limit)
            
            district_list = district_matches.getInfo()
            for feature in district_list['features']:
                props = feature['properties']
                results["districts"].append({
                    "name": props['ADM2_NAME'],
                    "code": props['ADM2_CODE'],
                    "state": props['ADM1_NAME'],
                    "type": "district",
                    "usage_example": f"?region={props['ADM2_NAME']}&state_name={props['ADM1_NAME']}"
                })
        
        return {
            "success": True,
            "search_results": results,
            "total_matches": len(results["states"]) + len(results["districts"]),
            "usage_note": "Use the name in the 'region' parameter. For districts, optionally add 'state_name' for better precision."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/available-regions")
async def get_available_regions():
    """Get list of predefined regions and instructions for custom regions."""
    predefined_regions = {
        "india": {"bounds": [68.0, 6.0, 97.0, 37.0], "description": "Entire India"},
        "mumbai": {"bounds": [72.7, 18.8, 73.2, 19.3], "description": "Mumbai metropolitan area"},
        "delhi": {"bounds": [76.8, 28.4, 77.5, 28.9], "description": "Delhi NCR"},
        "bangalore": {"bounds": [77.4, 12.8, 77.8, 13.2], "description": "Bangalore/Bengaluru city"},
        "kolkata": {"bounds": [88.2, 22.4, 88.5, 22.7], "description": "Kolkata metropolitan area"},
        "chennai": {"bounds": [80.1, 12.8, 80.3, 13.2], "description": "Chennai city"},
        "hyderabad": {"bounds": [78.3, 17.3, 78.6, 17.5], "description": "Hyderabad city"},
        "pune": {"bounds": [73.7, 18.4, 73.9, 18.6], "description": "Pune city"},
        "ahmedabad": {"bounds": [72.4, 23.0, 72.7, 23.1], "description": "Ahmedabad city"},
        "jaipur": {"bounds": [75.7, 26.8, 75.9, 27.0], "description": "Jaipur city"}
    }
    
    return {
        "success": True,
        "predefined_regions": predefined_regions,
        "gaul_integration": {
            "description": "All Indian districts and states from FAO GAUL dataset are supported",
            "usage": "Use any district/state name in 'region' parameter",
            "examples": [
                "?region=Ernakulam",
                "?region=Karnataka", 
                "?region=Tumkur&state_name=Karnataka (for disambiguation)"
            ],
            "search_endpoint": "/gaul-search?search_term=district_name",
            "note": "State name parameter helps disambiguate districts with same names in different states"
        },
        "custom_region_usage": {
            "description": "For custom regions, provide west, south, east, north coordinates",
            "example": "?region=custom&west=77.0&south=12.5&east=78.0&north=13.5",
            "coordinate_system": "WGS84 (longitude, latitude)",
            "note": "Custom coordinates override any region name"
        },
        "fallback_behavior": "If region not found in predefined cities or GAUL dataset, defaults to India bounds"
    }

# Map generation functions
async def _generate_temporal_buildings_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry,
    composite_method: str
) -> Dict[str, Any]:
    """Generate interactive map with temporal building analysis."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add building presence layer
        presence_vis = {'min': 0, 'max': 1, 'palette': ['white', 'lightblue', 'blue', 'darkblue']}
        m.add_layer(image.select('building_presence'), presence_vis, f'Building Presence ({composite_method}) - {region}')
        
        # Add building height layer
        height_vis = {'min': 0, 'max': 50, 'palette': ['green', 'yellow', 'orange', 'red']}
        m.add_layer(image.select('building_height'), height_vis, f'Building Height ({composite_method}) - {region}')
        
        # Add fractional count layer
        count_vis = {'min': 0, 'max': 0.01, 'palette': ['white', 'yellow', 'orange', 'red']}
        m.add_layer(image.select('building_fractional_count'), count_vis, f'Building Count ({composite_method}) - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temporal_buildings_{region.lower().replace(' ', '_')}_{composite_method}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "composite_method": composite_method,
            "dataset": "Google Open Buildings Temporal"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_temporal_height_map(
    height_band: ee.Image,
    tall_buildings: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with temporal building height analysis."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add height visualization
        height_vis = {'min': 0, 'max': 100, 'palette': ['green', 'yellow', 'orange', 'red', 'purple']}
        m.add_layer(height_band, height_vis, f'Temporal Building Heights - {region}')
        
        # Add tall buildings mask
        tall_vis = {'palette': ['red']}
        m.add_layer(tall_buildings.selfMask(), tall_vis, f'Tall Buildings (Temporal Max) - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temporal_building_heights_{region.lower().replace(' ', '_')}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "visualization": "Temporal building heights with tall building overlay"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_temporal_presence_map(
    presence_band: ee.Image,
    high_confidence: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with temporal building presence analysis."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add presence confidence
        presence_vis = {'min': 0, 'max': 1, 'palette': ['white', 'lightblue', 'blue', 'darkblue']}
        m.add_layer(presence_band, presence_vis, f'Temporal Building Confidence - {region}')
        
        # Add high confidence buildings
        confident_vis = {'palette': ['red']}
        m.add_layer(high_confidence.selfMask(), confident_vis, f'High Confidence Buildings (Temporal Max) - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temporal_building_presence_{region.lower().replace(' ', '_')}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "visualization": "Temporal building presence confidence with high-confidence overlay"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_temporal_count_map(
    count_band: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with temporal building count analysis."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add count visualization
        count_vis = {'min': 0, 'max': 0.01, 'palette': ['white', 'yellow', 'orange', 'red']}
        m.add_layer(count_band, count_vis, f'Temporal Building Fractional Count - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temporal_building_counts_{region.lower().replace(' ', '_')}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "visualization": "Temporal building fractional counts"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007, reload=True)