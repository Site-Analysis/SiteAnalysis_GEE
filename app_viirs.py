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
    title="NASA VIIRS Vegetation Analysis API",
    description="API for accessing NASA VIIRS VNP13A1 vegetation indices and reflectance data for India",
    version="1.0.0"
)

# Helper functions for region handling including GAUL district lookup
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
        zoom_level = 10  # Predefined cities
    else:
        # Assume it's a district or state from GAUL - use moderate zoom
        zoom_level = 8
    
    return {"bounds": bounds, "zoom": zoom_level}

# Pixel reliability class mapping
PIXEL_RELIABILITY_CLASSES = {
    0: "Excellent",
    1: "Good", 
    2: "Acceptable",
    3: "Marginal",
    4: "Pass",
    5: "Questionable",
    6: "Poor",
    7: "Cloud Shadow",
    8: "Snow/Ice",
    9: "Cloud",
    10: "Estimated",
    11: "LTAVG (taken from database)"
}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "NASA VIIRS Vegetation Analysis API",
        "description": "Access NASA VIIRS VNP13A1 vegetation indices and reflectance data",
        "dataset": "NASA/VIIRS/002/VNP13A1",
        "pixel_size": "500 meters",
        "temporal_resolution": "16-day composites",
        "available_bands": {
            "vegetation_indices": ["EVI", "EVI2", "NDVI"],
            "reflectance_bands": ["NIR_reflectance", "red_reflectance", "green_reflectance", "blue_reflectance", "SWIR1_reflectance", "SWIR2_reflectance", "SWIR3_reflectance"],
            "quality_bands": ["VI_Quality", "pixel_reliability"],
            "metadata_bands": ["composite_day_of_the_year", "relative_azimuth_angle", "sun_zenith_angle", "view_zenith_angle"]
        },
        "endpoints": [
            "/viirs-health",
            "/viirs-check-data",
            "/viirs-vegetation-indices",
            "/viirs-reflectance",
            "/viirs-quality-analysis", 
            "/viirs-time-series",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/viirs-health")
async def health_check():
    """Check if Earth Engine and NASA VIIRS dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test VIIRS dataset access
        viirs_dataset = ee.ImageCollection('NASA/VIIRS/002/VNP13A1')
        
        # Get latest available image
        latest_image = viirs_dataset.sort('system:time_start', False).first()
        latest_date = ee.Date(latest_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        
        # Check India area coverage
        india_bounds = ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])  # India bounding box
        india_image = latest_image.clip(india_bounds)
        
        # Get available bands
        band_names = latest_image.bandNames().getInfo()
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_result": test_result,
            "dataset": "NASA/VIIRS/002/VNP13A1",
            "latest_image_date": latest_date,
            "available_bands": band_names,
            "pixel_size": "500 meters",
            "india_coverage": "Available",
            "band_count": len(band_names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/viirs-check-data")
async def check_viirs_data(
    start_date: str = Query("2023-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("india", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Check VIIRS data availability for specified time period and region."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load VIIRS collection
        viirs_collection = ee.ImageCollection('NASA/VIIRS/002/VNP13A1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        # Get collection statistics
        image_count = viirs_collection.size().getInfo()
        
        if image_count == 0:
            return {
                "success": False,
                "message": f"No VIIRS images found for {region} between {start_date} and {end_date}",
                "suggestion": "Try expanding date range or different region"
            }
        
        # Get first and last image dates
        first_image = viirs_collection.sort('system:time_start').first()
        last_image = viirs_collection.sort('system:time_start', False).first()
        
        first_date = ee.Date(first_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        last_date = ee.Date(last_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        
        # Get sample image properties
        sample_image = viirs_collection.first()
        band_names = sample_image.bandNames().getInfo()
        
        # Check data quality from a sample - FIXED: Handle large regions
        try:
            sample_pixel_reliability = sample_image.select('pixel_reliability').reduceRegion(
                reducer=ee.Reducer.mode(),
                geometry=bounds,
                scale=1000,  # Increased scale to reduce pixel count
                maxPixels=1e8,  # Increased to 100 million pixels
                bestEffort=True  # Allow Earth Engine to optimize scale
            ).getInfo()
        except Exception as reduce_error:
            # If still too many pixels, sample a smaller representative area
            print(f"Large region detected, using centroid sampling: {reduce_error}")
            centroid = bounds.centroid()
            sample_area = centroid.buffer(5000)  # 5km radius sample area
            
            sample_pixel_reliability = sample_image.select('pixel_reliability').reduceRegion(
                reducer=ee.Reducer.mode(),
                geometry=sample_area,
                scale=500,
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
            "sample_pixel_reliability": sample_pixel_reliability.get('pixel_reliability', 'N/A'),
            "temporal_frequency": "16-day composites",
            "spatial_resolution": "500 meters",
            "note": "Sample pixel reliability from representative area within region"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking data: {str(e)}")

@app.get("/viirs-vegetation-indices")
async def get_vegetation_indices(
    start_date: str = Query("2023-06-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-08-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    indices: str = Query("NDVI,EVI", description="Comma-separated indices: NDVI, EVI, EVI2"),
    include_map: bool = Query(True, description="Generate vegetation index map"),
    quality_filter: bool = Query(True, description="Filter by pixel quality (excellent to acceptable)"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get vegetation indices analysis for specified region and time period."""
    try:
        # Parse indices
        selected_indices = [idx.strip() for idx in indices.split(',')]
        valid_indices = ['NDVI', 'EVI', 'EVI2']
        
        for idx in selected_indices:
            if idx not in valid_indices:
                raise HTTPException(status_code=400, detail=f"Invalid index '{idx}'. Valid indices: {valid_indices}")
        
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load and filter VIIRS collection
        viirs_collection = ee.ImageCollection('NASA/VIIRS/002/VNP13A1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        # Apply quality filtering if requested
        if quality_filter:
            # Filter for excellent, good, and acceptable pixels (0, 1, 2)
            viirs_collection = viirs_collection.map(
                lambda image: image.updateMask(image.select('pixel_reliability').lte(2))
            )
        
        image_count = viirs_collection.size().getInfo()
        
        if image_count == 0:
            return {
                "success": False,
                "message": f"No quality VIIRS images found for {region} in specified period"
            }
        
        # Create median composite
        composite_image = viirs_collection.median().clip(bounds)
        
        # Calculate statistics for each index
        index_stats = {}
        for index in selected_indices:
            index_band = composite_image.select(index)
            
            # Get statistics
            stats = index_band.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=500,
                maxPixels=1e6
            ).getInfo()
            
            index_stats[index] = {
                "min": stats.get(f'{index}_min', 'N/A'),
                "max": stats.get(f'{index}_max', 'N/A'), 
                "mean": stats.get(f'{index}_mean', 'N/A')
            }
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "images_used": image_count,
            "vegetation_indices": index_stats,
            "quality_filtered": quality_filter,
            "composite_type": "median"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_viirs_map(composite_image, selected_indices, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing vegetation indices: {str(e)}")

@app.get("/viirs-reflectance")
async def get_reflectance_data(
    start_date: str = Query("2023-06-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-08-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    bands: str = Query("red_reflectance,NIR_reflectance", description="Comma-separated bands"),
    include_map: bool = Query(True, description="Generate reflectance map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get reflectance band analysis for specified region."""
    try:
        # Parse bands
        selected_bands = [band.strip() for band in bands.split(',')]
        valid_bands = ['red_reflectance', 'green_reflectance', 'blue_reflectance', 'NIR_reflectance', 
                      'SWIR1_reflectance', 'SWIR2_reflectance', 'SWIR3_reflectance']
        
        for band in selected_bands:
            if band not in valid_bands:
                raise HTTPException(status_code=400, detail=f"Invalid band '{band}'. Valid bands: {valid_bands}")
        
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load VIIRS collection
        viirs_collection = ee.ImageCollection('NASA/VIIRS/002/VNP13A1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        # Quality filter
        viirs_collection = viirs_collection.map(
            lambda image: image.updateMask(image.select('pixel_reliability').lte(2))
        )
        
        image_count = viirs_collection.size().getInfo()
        
        if image_count == 0:
            return {"success": False, "message": "No quality images found"}
        
        # Create composite
        composite_image = viirs_collection.median().clip(bounds)
        
        # Calculate reflectance statistics
        band_stats = {}
        for band in selected_bands:
            band_data = composite_image.select(band)
            
            stats = band_data.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=500,
                maxPixels=1e6
            ).getInfo()
            
            band_stats[band] = {
                "min": stats.get(f'{band}_min', 'N/A'),
                "max": stats.get(f'{band}_max', 'N/A'),
                "mean": stats.get(f'{band}_mean', 'N/A')
            }
        
        response_data = {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "images_used": image_count,
            "reflectance_stats": band_stats,
            "units": "Reflectance values (0-1 range typical)"
        }
        
        # Generate map
        if include_map:
            map_result = await _generate_reflectance_map(composite_image, selected_bands, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing reflectance: {str(e)}")

@app.get("/viirs-quality-analysis")
async def analyze_data_quality(
    start_date: str = Query("2023-06-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-08-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze pixel reliability and VI quality for the region."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load VIIRS collection
        viirs_collection = ee.ImageCollection('NASA/VIIRS/002/VNP13A1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds)
        
        image_count = viirs_collection.size().getInfo()
        
        if image_count == 0:
            return {"success": False, "message": "No images found"}
        
        # Get median composite
        composite = viirs_collection.median().clip(bounds)
        
        # Analyze pixel reliability distribution
        pixel_reliability = composite.select('pixel_reliability')
        
        # Count pixels by reliability class
        reliability_stats = {}
        for class_value, class_name in PIXEL_RELIABILITY_CLASSES.items():
            mask = pixel_reliability.eq(class_value)
            pixel_count = mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=500,
                maxPixels=1e6
            ).getInfo()
            
            reliability_stats[class_name] = pixel_count.get('pixel_reliability', 0)
        
        # Calculate quality percentages
        total_pixels = sum(reliability_stats.values())
        quality_percentages = {}
        
        if total_pixels > 0:
            for class_name, count in reliability_stats.items():
                quality_percentages[class_name] = round((count / total_pixels) * 100, 2)
        
        return {
            "success": True,
            "region": region,
            "date_range": f"{start_date} to {end_date}",
            "images_analyzed": image_count,
            "pixel_reliability_counts": reliability_stats,
            "quality_percentages": quality_percentages,
            "total_pixels_analyzed": total_pixels,
            "data_quality_summary": {
                "excellent_good_acceptable": sum([reliability_stats.get("Excellent", 0), 
                                                reliability_stats.get("Good", 0), 
                                                reliability_stats.get("Acceptable", 0)]),
                "cloud_affected": reliability_stats.get("Cloud", 0) + reliability_stats.get("Cloud Shadow", 0),
                "poor_quality": reliability_stats.get("Poor", 0) + reliability_stats.get("Questionable", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing quality: {str(e)}")

@app.get("/viirs-time-series")
async def get_time_series(
    start_date: str = Query("2023-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-12-31", description="End date (YYYY-MM-DD)"),
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    index: str = Query("NDVI", description="Vegetation index: NDVI, EVI, or EVI2"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get time series data for vegetation index over specified period."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load collection
        viirs_collection = ee.ImageCollection('NASA/VIIRS/002/VNP13A1') \
            .filterDate(start_date, end_date) \
            .filterBounds(bounds) \
            .select(index)
        
        # Quality filter
        viirs_collection = viirs_collection.map(
            lambda image: image.updateMask(
                ee.Image(image).select('pixel_reliability', 'pixel_reliability').lte(2)
            )
        )
        
        # Get time series values
        def get_image_stats(image):
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=bounds,
                scale=500,
                maxPixels=1e6
            )
            date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
            return ee.Feature(None, {
                'date': date,
                f'{index}_mean': stats.get(index)
            })
        
        time_series = viirs_collection.map(get_image_stats).getInfo()
        
        # Process results
        dates = []
        values = []
        
        for feature in time_series['features']:
            props = feature['properties']
            if props[f'{index}_mean'] is not None:
                dates.append(props['date'])
                values.append(props[f'{index}_mean'])
        
        return {
            "success": True,
            "region": region,
            "vegetation_index": index,
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
            }
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

async def _generate_viirs_map(
    image: ee.Image,
    indices: List[str],
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with VIIRS vegetation indices."""
    try:
        m = geemap.Map()
        
        # Center map on region
        m.center_object(bounds, zoom_level)
        
        # Add vegetation index layers
        for index in indices:
            if index == "NDVI":
                vis_params = {'min': -0.2, 'max': 1.0, 'palette': ['red', 'yellow', 'green']}
            elif index in ["EVI", "EVI2"]:
                vis_params = {'min': -0.2, 'max': 1.0, 'palette': ['brown', 'yellow', 'green']}
            
            m.add_layer(image.select(index), vis_params, f'{index} - {region}')
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"viirs_{region}_{'_'.join(indices)}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "indices": indices,
            "region": region,
            "dataset": "NASA VIIRS VNP13A1"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_reflectance_map(
    image: ee.Image,
    bands: List[str],
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with VIIRS reflectance bands."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add reflectance layers
        for band in bands:
            vis_params = {'min': 0, 'max': 0.3, 'palette': ['black', 'blue', 'green', 'yellow', 'red']}
            m.add_layer(image.select(band), vis_params, f'{band} - {region}')
        
        # If we have RGB bands, create true color composite
        if all(band in bands for band in ['red_reflectance', 'green_reflectance', 'blue_reflectance']):
            rgb_vis = {
                'bands': ['red_reflectance', 'green_reflectance', 'blue_reflectance'],
                'min': 0, 'max': 0.3
            }
            m.add_layer(image.select(['red_reflectance', 'green_reflectance', 'blue_reflectance']), 
                       rgb_vis, f'RGB Composite - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"viirs_reflectance_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "bands": bands,
            "region": region
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)