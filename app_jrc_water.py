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
    title="JRC Global Surface Water Analysis API",
    description="API for accessing JRC Global Surface Water dataset - water occurrence, seasonality, and change detection",
    version="1.0.0"
)

# Helper functions for region handling (including GAUL integration)
def _get_district_bounds_from_gaul(district_name: str, state_name: Optional[str] = None) -> Optional[ee.Geometry]:
    """Get district bounds from FAO GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        district_filter = ee.Filter.stringContains('ADM2_NAME', district_name)
        
        if state_name:
            state_filter = ee.Filter.stringContains('ADM1_NAME', state_name)
            combined_filter = ee.Filter.And(district_filter, state_filter)
        else:
            combined_filter = district_filter
        
        matched_districts = india_boundaries.filter(combined_filter)
        count = matched_districts.size().getInfo()
        if count == 0:
            return None
        
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
        
        state_boundaries = india_boundaries.filter(
            ee.Filter.stringContains('ADM1_NAME', state_name)
        )
        
        count = state_boundaries.size().getInfo()
        if count == 0:
            return None
        
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

# Transition class mapping for water change
TRANSITION_CLASSES = {
    0: "No data",
    1: "Permanent water",
    2: "New permanent water",
    3: "Lost permanent water",
    4: "Seasonal water",
    5: "New seasonal water",
    6: "Lost seasonal water",
    7: "Seasonal to permanent water",
    8: "Permanent to seasonal water",
    9: "Ephemeral permanent water",
    10: "Ephemeral seasonal water"
}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "JRC Global Surface Water Analysis API",
        "description": "Access JRC Global Surface Water dataset for water occurrence, seasonality, and change detection",
        "dataset": "JRC/GSW1_4/GlobalSurfaceWater",
        "pixel_size": "30 meters",
        "temporal_coverage": "1984-2021",
        "available_bands": {
            "water_occurrence": ["occurrence"],
            "water_change": ["change_abs", "change_norm"],
            "water_dynamics": ["seasonality", "recurrence", "transition", "max_extent"]
        },
        "band_descriptions": {
            "occurrence": "Frequency of water presence (0-100%)",
            "change_abs": "Absolute change 1984-1999 vs 2000-2021 (-100 to 100%)",
            "change_norm": "Normalized change (-100 to 100%)",
            "seasonality": "Number of months water is present (0-12)",
            "recurrence": "Frequency water returns year to year (0-100%)",
            "transition": "Categorical change classification",
            "max_extent": "Binary: anywhere water ever detected"
        },
        "endpoints": [
            "/jrc-health",
            "/jrc-water-occurrence",
            "/jrc-water-change", 
            "/jrc-water-seasonality",
            "/jrc-water-dynamics",
            "/jrc-transition-analysis",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/jrc-health")
async def health_check():
    """Check if Earth Engine and JRC Global Surface Water dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test JRC Global Surface Water dataset access
        gsw_dataset = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        
        # Get available bands
        band_names = gsw_dataset.bandNames().getInfo()
        
        # Test India area coverage with a small sample
        india_bounds = ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])
        india_sample = gsw_dataset.clip(india_bounds)
        
        # Get a small sample to verify data exists
        sample_stats = india_sample.select('occurrence').reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=ee.Geometry.Point([77.5, 13.0]),  # Bangalore area
            scale=1000,
            maxPixels=1e6
        ).getInfo()
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_result": test_result,
            "dataset": "JRC/GSW1_4/GlobalSurfaceWater",
            "available_bands": band_names,
            "pixel_size": "30 meters",
            "temporal_coverage": "1984-2021",
            "india_coverage": "Available",
            "sample_occurrence_range": {
                "min": sample_stats.get('occurrence_min', 'N/A'),
                "max": sample_stats.get('occurrence_max', 'N/A')
            },
            "band_count": len(band_names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/jrc-water-occurrence")
async def get_water_occurrence(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate water occurrence map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get water occurrence analysis for specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load JRC Global Surface Water dataset
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        occurrence = gsw.select('occurrence').clip(bounds)
        
        # Calculate statistics
        occurrence_stats = occurrence.reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True).combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=bounds,
            scale=100,  # Coarser scale for large regions
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Calculate water coverage statistics
        water_pixels = occurrence.gte(10)  # Pixels with >10% water occurrence
        water_coverage = water_pixels.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Calculate total pixels for percentage
        total_pixels = occurrence.mask(occurrence.gte(0)).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        water_pixel_count = water_coverage.get('occurrence', 0)
        total_pixel_count = total_pixels.get('occurrence', 1)
        water_coverage_percent = (water_pixel_count / total_pixel_count * 100) if total_pixel_count > 0 else 0
        
        response_data = {
            "success": True,
            "region": region,
            "dataset": "JRC/GSW1_4/GlobalSurfaceWater",
            "analysis_type": "Water Occurrence (1984-2021)",
            "occurrence_statistics": {
                "min_occurrence": occurrence_stats.get('occurrence_min', 'N/A'),
                "max_occurrence": occurrence_stats.get('occurrence_max', 'N/A'),
                "mean_occurrence": occurrence_stats.get('occurrence_mean', 'N/A'),
                "std_dev": occurrence_stats.get('occurrence_stdDev', 'N/A')
            },
            "water_coverage": {
                "pixels_with_water": water_pixel_count,
                "total_pixels": total_pixel_count,
                "water_coverage_percent": round(water_coverage_percent, 2)
            },
            "interpretation": {
                "occurrence_meaning": "Percentage of time water was present (0-100%)",
                "water_threshold": "Pixels with >10% occurrence considered water areas",
                "temporal_coverage": "Analysis covers 1984-2021 period"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_water_occurrence_map(occurrence, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing water occurrence: {str(e)}")

@app.get("/jrc-water-change")
async def get_water_change(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    change_type: str = Query("both", description="Change type: absolute, normalized, or both"),
    include_map: bool = Query(True, description="Generate water change map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get water change analysis comparing 1984-1999 vs 2000-2021."""
    try:
        # Define region bounds
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load JRC Global Surface Water dataset
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        
        change_data = {}
        
        # Analyze absolute change
        if change_type in ["absolute", "both"]:
            change_abs = gsw.select('change_abs').clip(bounds)
            
            abs_stats = change_abs.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            change_data["absolute_change"] = {
                "min_change": abs_stats.get('change_abs_min', 'N/A'),
                "max_change": abs_stats.get('change_abs_max', 'N/A'),
                "mean_change": abs_stats.get('change_abs_mean', 'N/A'),
                "interpretation": "Negative = water loss, Positive = water gain (%)"
            }
        
        # Analyze normalized change
        if change_type in ["normalized", "both"]:
            change_norm = gsw.select('change_norm').clip(bounds)
            
            norm_stats = change_norm.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            change_data["normalized_change"] = {
                "min_change": norm_stats.get('change_norm_min', 'N/A'),
                "max_change": norm_stats.get('change_norm_max', 'N/A'),
                "mean_change": norm_stats.get('change_norm_mean', 'N/A'),
                "interpretation": "Normalized change: (epoch1-epoch2)/(epoch1+epoch2) * 100"
            }
        
        response_data = {
            "success": True,
            "region": region,
            "analysis_type": f"Water Change Analysis ({change_type})",
            "comparison_periods": {
                "epoch_1": "1984-1999",
                "epoch_2": "2000-2021"
            },
            "change_analysis": change_data,
            "dataset": "JRC/GSW1_4/GlobalSurfaceWater"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_water_change_map(gsw, region, zoom_level, bounds, change_type)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing water change: {str(e)}")

@app.get("/jrc-water-seasonality")
async def get_water_seasonality(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate seasonality map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get water seasonality analysis - number of months water is present."""
    try:
        # Define region bounds
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load seasonality data
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        seasonality = gsw.select('seasonality').clip(bounds)
        
        # Calculate seasonality statistics
        seasonality_stats = seasonality.reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True).combine(ee.Reducer.mode(), sharedInputs=True),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Count pixels by seasonality class
        seasonality_histogram = seasonality.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=bounds,
            scale=200,  # Coarser for histogram
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Process histogram data
        histogram_data = seasonality_histogram.get('seasonality', {})
        seasonality_distribution = {}
        
        for months, count in histogram_data.items():
            if months != "null":  # Skip null values
                months_int = int(float(months))
                if 0 <= months_int <= 12:
                    seasonality_distribution[f"{months_int}_months"] = count
        
        response_data = {
            "success": True,
            "region": region,
            "analysis_type": "Water Seasonality Analysis",
            "seasonality_statistics": {
                "min_months": seasonality_stats.get('seasonality_min', 'N/A'),
                "max_months": seasonality_stats.get('seasonality_max', 'N/A'),
                "mean_months": seasonality_stats.get('seasonality_mean', 'N/A'),
                "mode_months": seasonality_stats.get('seasonality_mode', 'N/A')
            },
            "seasonality_distribution": seasonality_distribution,
            "interpretation": {
                "0_months": "No water detected",
                "1-3_months": "Highly seasonal water",
                "4-8_months": "Moderately seasonal water", 
                "9-11_months": "Nearly permanent water",
                "12_months": "Permanent water throughout year"
            },
            "dataset": "JRC/GSW1_4/GlobalSurfaceWater"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_seasonality_map(seasonality, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing water seasonality: {str(e)}")

@app.get("/jrc-transition-analysis")
async def get_transition_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate transition map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get water transition analysis - categorical change classification."""
    try:
        # Define region bounds
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load transition data
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        transition = gsw.select('transition').clip(bounds)
        
        # Get transition class distribution
        transition_histogram = transition.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=bounds,
            scale=200,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Process histogram data with class names
        histogram_data = transition_histogram.get('transition', {})
        transition_distribution = {}
        
        for class_value, count in histogram_data.items():
            if class_value != "null":
                class_int = int(float(class_value))
                if class_int in TRANSITION_CLASSES:
                    class_name = TRANSITION_CLASSES[class_int]
                    transition_distribution[class_name] = {
                        "class_value": class_int,
                        "pixel_count": count
                    }
        
        # Calculate percentages
        total_pixels = sum([data["pixel_count"] for data in transition_distribution.values()])
        for class_name, data in transition_distribution.items():
            if total_pixels > 0:
                data["percentage"] = round((data["pixel_count"] / total_pixels) * 100, 2)
            else:
                data["percentage"] = 0
        
        response_data = {
            "success": True,
            "region": region,
            "analysis_type": "Water Transition Analysis",
            "transition_distribution": transition_distribution,
            "total_pixels_analyzed": total_pixels,
            "transition_classes_legend": TRANSITION_CLASSES,
            "interpretation": {
                "permanent_water": "Classes 1, 2, 7: Stable or new permanent water",
                "seasonal_water": "Classes 4, 5, 8: Seasonal water patterns",
                "water_loss": "Classes 3, 6: Areas where water was lost",
                "ephemeral": "Classes 9, 10: Temporary/ephemeral water"
            },
            "dataset": "JRC/GSW1_4/GlobalSurfaceWater"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_transition_map(transition, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing water transitions: {str(e)}")

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
            "search_endpoint": "/gaul-search?search_term=district_name"
        },
        "custom_region_usage": {
            "description": "For custom regions, provide west, south, east, north coordinates",
            "example": "?region=custom&west=77.0&south=12.5&east=78.0&north=13.5",
            "coordinate_system": "WGS84 (longitude, latitude)"
        }
    }

# Map generation functions
async def _generate_water_occurrence_map(
    occurrence_image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with water occurrence data."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Water occurrence visualization
        occurrence_vis = {
            'min': 0,
            'max': 100,
            'palette': ['white', 'lightblue', 'blue', 'darkblue']
        }
        
        m.add_layer(occurrence_image, occurrence_vis, f'Water Occurrence - {region}')
        
        # Add legend
        legend_dict = {
            'No Water (0%)': 'white',
            'Low Occurrence (1-25%)': 'lightblue', 
            'Medium Occurrence (26-75%)': 'blue',
            'High Occurrence (76-100%)': 'darkblue'
        }
        m.add_legend(legend_dict=legend_dict, title="Water Occurrence (%)")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jrc_water_occurrence_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "JRC Global Surface Water - Occurrence"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_water_change_map(
    gsw_image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry,
    change_type: str
) -> Dict[str, Any]:
    """Generate interactive map with water change data."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        if change_type in ["absolute", "both"]:
            change_abs_vis = {
                'min': -50,
                'max': 50,
                'palette': ['red', 'orange', 'white', 'lightblue', 'blue']
            }
            m.add_layer(gsw_image.select('change_abs'), change_abs_vis, f'Absolute Change - {region}')
        
        if change_type in ["normalized", "both"]:
            change_norm_vis = {
                'min': -100,
                'max': 100,
                'palette': ['darkred', 'red', 'white', 'lightgreen', 'darkgreen']
            }
            m.add_layer(gsw_image.select('change_norm'), change_norm_vis, f'Normalized Change - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jrc_water_change_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "change_type": change_type
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_seasonality_map(
    seasonality_image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with water seasonality data."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        seasonality_vis = {
            'min': 0,
            'max': 12,
            'palette': ['white', 'yellow', 'orange', 'red', 'purple', 'blue']
        }
        
        m.add_layer(seasonality_image, seasonality_vis, f'Water Seasonality - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jrc_water_seasonality_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_transition_map(
    transition_image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive map with water transition data."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Custom palette for transition classes
        transition_vis = {
            'min': 0,
            'max': 10,
            'palette': ['black', 'blue', 'cyan', 'red', 'green', 'lightgreen', 
                       'orange', 'purple', 'pink', 'yellow', 'gray']
        }
        
        m.add_layer(transition_image, transition_vis, f'Water Transitions - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jrc_water_transitions_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)