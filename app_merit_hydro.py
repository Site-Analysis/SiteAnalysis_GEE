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
    title="MERIT Hydro Dataset API",
    description="API for accessing MERIT Hydro hydrological data - elevation, flow direction, river width, and drainage analysis",
    version="1.0.0"
)

# Helper functions for region handling (inherited from VIIRS app)
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

# Flow direction mapping
FLOW_DIRECTION_MAPPING = {
    1: "East",
    2: "Southeast", 
    4: "South",
    8: "Southwest",
    16: "West",
    32: "Northwest",
    64: "North",
    128: "Northeast",
    0: "River mouth",
    -1: "Inland depression"
}

# Water classification
WATER_CLASSIFICATION = {
    0: "Land",
    1: "Permanent water"
}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "MERIT Hydro Dataset API",
        "description": "Access MERIT Hydro hydrological data including elevation, flow direction, river width, and drainage analysis",
        "dataset": "MERIT/Hydro/v1_0_1",
        "pixel_size": "92.77 meters",
        "coverage": "Global",
        "available_bands": {
            "elevation": {"band": "elv", "units": "meters", "description": "Elevation"},
            "flow_direction": {"band": "dir", "units": "categorical", "description": "Flow Direction (Local Drainage Direction)"},
            "river_width": {"band": "wth", "units": "meters", "description": "River channel width"},
            "water_classification": {"band": "wat", "units": "categorical", "description": "Land and permanent water"},
            "upstream_area": {"band": "upa", "units": "km²", "description": "Upstream drainage area"},
            "upstream_pixels": {"band": "upg", "units": "count", "description": "Upstream drainage pixels"},
            "height_above_drainage": {"band": "hnd", "units": "meters", "description": "Height above nearest drainage"},
            "river_width_viz": {"band": "viswth", "units": "visualization", "description": "River channel width visualization"}
        },
        "endpoints": [
            "/merit-health",
            "/merit-elevation-analysis", 
            "/merit-flow-analysis",
            "/merit-river-analysis",
            "/merit-drainage-analysis",
            "/merit-comprehensive-analysis",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/merit-health")
async def health_check():
    """Check if Earth Engine and MERIT Hydro dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test MERIT Hydro dataset access
        merit_dataset = ee.Image('MERIT/Hydro/v1_0_1')
        
        # Get available bands
        band_names = merit_dataset.bandNames().getInfo()
        
        # Test India area coverage
        india_bounds = ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])
        india_image = merit_dataset.clip(india_bounds)
        
        # Get sample elevation data
        sample_elv = merit_dataset.select('elv').reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=india_bounds,
            scale=1000,
            maxPixels=1e6,
            bestEffort=True
        ).getInfo()
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_result": test_result,
            "dataset": "MERIT/Hydro/v1_0_1", 
            "available_bands": band_names,
            "pixel_size": "92.77 meters",
            "india_coverage": "Available",
            "band_count": len(band_names),
            "sample_elevation_range": {
                "min_elevation_m": sample_elv.get('elv_min', 'N/A'),
                "max_elevation_m": sample_elv.get('elv_max', 'N/A')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/merit-elevation-analysis")
async def get_elevation_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate elevation map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get elevation analysis for specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load MERIT Hydro dataset
        merit_image = ee.Image('MERIT/Hydro/v1_0_1').clip(bounds)
        
        # Analyze elevation
        elevation_band = merit_image.select('elv')
        
        # Get elevation statistics
        elv_stats = elevation_band.reduceRegion(
            reducer=ee.Reducer.minMax().combine(
                ee.Reducer.mean().combine(
                    ee.Reducer.stdDev().combine(
                        ee.Reducer.percentile([25, 50, 75]), sharedInputs=True
                    ), sharedInputs=True
                ), sharedInputs=True
            ),
            geometry=bounds,
            scale=200,  # Slightly coarser than native resolution for performance
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Also get height above drainage stats
        hnd_stats = merit_image.select('hnd').reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=bounds,
            scale=200,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        response_data = {
            "success": True,
            "region": region,
            "elevation_statistics": {
                "min_elevation_m": elv_stats.get('elv_min', 'N/A'),
                "max_elevation_m": elv_stats.get('elv_max', 'N/A'),
                "mean_elevation_m": elv_stats.get('elv_mean', 'N/A'),
                "std_dev_m": elv_stats.get('elv_stdDev', 'N/A'),
                "percentiles": {
                    "25th_percentile_m": elv_stats.get('elv_p25', 'N/A'),
                    "median_elevation_m": elv_stats.get('elv_p50', 'N/A'),
                    "75th_percentile_m": elv_stats.get('elv_p75', 'N/A')
                }
            },
            "height_above_drainage": {
                "min_hnd_m": hnd_stats.get('hnd_min', 'N/A'),
                "max_hnd_m": hnd_stats.get('hnd_max', 'N/A'), 
                "mean_hnd_m": hnd_stats.get('hnd_mean', 'N/A')
            },
            "dataset_info": {
                "pixel_size": "92.77 meters",
                "vertical_accuracy": "10cm increments",
                "datum": "EGM96 geoid"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_elevation_map(merit_image, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing elevation: {str(e)}")

@app.get("/merit-flow-analysis")
async def get_flow_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate flow direction map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get flow direction analysis for specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load MERIT Hydro dataset
        merit_image = ee.Image('MERIT/Hydro/v1_0_1').clip(bounds)
        
        # Analyze flow directions
        flow_band = merit_image.select('dir')
        
        # Count pixels by flow direction
        flow_direction_counts = {}
        
        for direction_value, direction_name in FLOW_DIRECTION_MAPPING.items():
            mask = flow_band.eq(direction_value)
            pixel_count = mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=200,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
            flow_direction_counts[direction_name] = pixel_count.get('dir', 0)
        
        # Calculate total pixels
        total_pixels = sum(flow_direction_counts.values())
        
        # Calculate percentages
        flow_percentages = {}
        if total_pixels > 0:
            for direction, count in flow_direction_counts.items():
                flow_percentages[direction] = round((count / total_pixels) * 100, 2)
        
        # Get water classification
        water_band = merit_image.select('wat')
        water_stats = {}
        
        for water_value, water_name in WATER_CLASSIFICATION.items():
            mask = water_band.eq(water_value)
            pixel_count = mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=200,
                maxPixels=1e7,
                bestEffort=True
            ).getInfo()
            
            water_stats[water_name] = pixel_count.get('wat', 0)
        
        response_data = {
            "success": True,
            "region": region,
            "flow_direction_analysis": {
                "pixel_counts": flow_direction_counts,
                "percentages": flow_percentages,
                "total_analyzed_pixels": total_pixels
            },
            "water_classification": water_stats,
            "flow_direction_legend": FLOW_DIRECTION_MAPPING,
            "dataset_info": {
                "pixel_size": "92.77 meters",
                "flow_algorithm": "D8 flow direction"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_flow_map(merit_image, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing flow direction: {str(e)}")

@app.get("/merit-river-analysis")
async def get_river_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate river width map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get river channel width analysis for specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load MERIT Hydro dataset
        merit_image = ee.Image('MERIT/Hydro/v1_0_1').clip(bounds)
        
        # Analyze river channel width
        river_width_band = merit_image.select('wth')
        
        # Mask out non-river areas (width > 0)
        river_mask = river_width_band.gt(0)
        
        # Get river width statistics
        river_stats = river_width_band.updateMask(river_mask).reduceRegion(
            reducer=ee.Reducer.minMax().combine(
                ee.Reducer.mean().combine(
                    ee.Reducer.percentile([25, 50, 75, 90, 95]), sharedInputs=True
                ), sharedInputs=True
            ),
            geometry=bounds,
            scale=200,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Count river pixels vs land pixels
        total_pixels = merit_image.select('wat').reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=bounds,
            scale=200,
            maxPixels=1e7,
            bestEffort=True
        ).getInfo().get('wat', 0)
        
        river_pixels = river_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=200,
            maxPixels=1e7,
            bestEffort=True
        ).getInfo().get('wth', 0)
        
        response_data = {
            "success": True,
            "region": region,
            "river_analysis": {
                "river_width_statistics": {
                    "min_width_m": river_stats.get('wth_min', 'N/A'),
                    "max_width_m": river_stats.get('wth_max', 'N/A'),
                    "mean_width_m": river_stats.get('wth_mean', 'N/A'),
                    "percentiles": {
                        "25th_percentile_m": river_stats.get('wth_p25', 'N/A'),
                        "median_width_m": river_stats.get('wth_p50', 'N/A'),
                        "75th_percentile_m": river_stats.get('wth_p75', 'N/A'),
                        "90th_percentile_m": river_stats.get('wth_p90', 'N/A'),
                        "95th_percentile_m": river_stats.get('wth_p95', 'N/A')
                    }
                },
                "coverage_statistics": {
                    "total_pixels": total_pixels,
                    "river_pixels": river_pixels,
                    "river_coverage_percent": round((river_pixels / total_pixels) * 100, 2) if total_pixels > 0 else 0
                }
            },
            "methodology": "River width calculated using method from Yamazaki et al. 2012, WRR",
            "dataset_info": {
                "pixel_size": "92.77 meters",
                "width_algorithm": "Yamazaki et al. 2012 method"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_river_map(merit_image, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing rivers: {str(e)}")

@app.get("/merit-drainage-analysis")
async def get_drainage_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate drainage analysis map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get upstream drainage area analysis for specified region."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load MERIT Hydro dataset
        merit_image = ee.Image('MERIT/Hydro/v1_0_1').clip(bounds)
        
        # Analyze upstream drainage area
        drainage_area_band = merit_image.select('upa')  # km²
        drainage_pixels_band = merit_image.select('upg')  # pixel count
        
        # Get drainage area statistics
        drainage_stats = drainage_area_band.reduceRegion(
            reducer=ee.Reducer.minMax().combine(
                ee.Reducer.mean().combine(
                    ee.Reducer.percentile([50, 75, 90, 95, 99]), sharedInputs=True
                ), sharedInputs=True
            ),
            geometry=bounds,
            scale=200,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Get drainage pixel statistics
        pixel_stats = drainage_pixels_band.reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=bounds,
            scale=200,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Classify drainage areas
        drainage_classes = {
            "small_catchments": drainage_area_band.lte(10).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bounds, scale=200, maxPixels=1e7, bestEffort=True
            ).getInfo().get('upa', 0),
            "medium_catchments": drainage_area_band.gt(10).And(drainage_area_band.lte(100)).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bounds, scale=200, maxPixels=1e7, bestEffort=True
            ).getInfo().get('upa', 0),
            "large_catchments": drainage_area_band.gt(100).And(drainage_area_band.lte(1000)).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bounds, scale=200, maxPixels=1e7, bestEffort=True
            ).getInfo().get('upa', 0),
            "major_basins": drainage_area_band.gt(1000).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bounds, scale=200, maxPixels=1e7, bestEffort=True
            ).getInfo().get('upa', 0)
        }
        
        response_data = {
            "success": True,
            "region": region,
            "drainage_analysis": {
                "upstream_area_statistics_km2": {
                    "min_drainage_area": drainage_stats.get('upa_min', 'N/A'),
                    "max_drainage_area": drainage_stats.get('upa_max', 'N/A'),
                    "mean_drainage_area": drainage_stats.get('upa_mean', 'N/A'),
                    "percentiles": {
                        "median_area_km2": drainage_stats.get('upa_p50', 'N/A'),
                        "75th_percentile_km2": drainage_stats.get('upa_p75', 'N/A'),
                        "90th_percentile_km2": drainage_stats.get('upa_p90', 'N/A'),
                        "95th_percentile_km2": drainage_stats.get('upa_p95', 'N/A'),
                        "99th_percentile_km2": drainage_stats.get('upa_p99', 'N/A')
                    }
                },
                "upstream_pixel_statistics": {
                    "min_upstream_pixels": pixel_stats.get('upg_min', 'N/A'),
                    "max_upstream_pixels": pixel_stats.get('upg_max', 'N/A'),
                    "mean_upstream_pixels": pixel_stats.get('upg_mean', 'N/A')
                },
                "catchment_classification": {
                    "small_catchments_pixels": drainage_classes["small_catchments"],
                    "medium_catchments_pixels": drainage_classes["medium_catchments"], 
                    "large_catchments_pixels": drainage_classes["large_catchments"],
                    "major_basins_pixels": drainage_classes["major_basins"]
                }
            },
            "classification_legend": {
                "small_catchments": "≤ 10 km²",
                "medium_catchments": "10-100 km²", 
                "large_catchments": "100-1000 km²",
                "major_basins": "> 1000 km²"
            },
            "dataset_info": {
                "pixel_size": "92.77 meters",
                "area_units": "square kilometers"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_drainage_map(merit_image, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing drainage: {str(e)}")

@app.get("/merit-comprehensive-analysis")
async def get_comprehensive_analysis(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    include_map: bool = Query(True, description="Generate comprehensive analysis map"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get comprehensive hydrological analysis combining all MERIT Hydro bands."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load MERIT Hydro dataset
        merit_image = ee.Image('MERIT/Hydro/v1_0_1').clip(bounds)
        
        # Comprehensive analysis of all bands
        all_bands = ['elv', 'dir', 'wth', 'wat', 'upa', 'upg', 'hnd', 'viswth']
        
        comprehensive_stats = {}
        
        for band in all_bands:
            if band in ['elv', 'wth', 'upa', 'upg', 'hnd']:  # Continuous variables
                stats = merit_image.select(band).reduceRegion(
                    reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                    geometry=bounds,
                    scale=300,  # Coarser scale for comprehensive analysis
                    maxPixels=1e7,
                    bestEffort=True
                ).getInfo()
                
                comprehensive_stats[band] = {
                    "min": stats.get(f'{band}_min', 'N/A'),
                    "max": stats.get(f'{band}_max', 'N/A'),
                    "mean": stats.get(f'{band}_mean', 'N/A')
                }
        
        # Water body percentage
        water_band = merit_image.select('wat')
        water_pixels = water_band.eq(1).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=300,
            maxPixels=1e6,
            bestEffort=True
        ).getInfo().get('wat', 0)
        
        total_pixels = water_band.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=bounds,
            scale=300,
            maxPixels=1e6,
            bestEffort=True
        ).getInfo().get('wat', 0)
        
        water_percentage = round((water_pixels / total_pixels) * 100, 2) if total_pixels > 0 else 0
        
        response_data = {
            "success": True,
            "region": region,
            "comprehensive_analysis": {
                "elevation": {
                    "min_m": comprehensive_stats.get('elv', {}).get('min', 'N/A'),
                    "max_m": comprehensive_stats.get('elv', {}).get('max', 'N/A'),
                    "mean_m": comprehensive_stats.get('elv', {}).get('mean', 'N/A')
                },
                "river_width": {
                    "min_m": comprehensive_stats.get('wth', {}).get('min', 'N/A'),
                    "max_m": comprehensive_stats.get('wth', {}).get('max', 'N/A'),
                    "mean_m": comprehensive_stats.get('wth', {}).get('mean', 'N/A')
                },
                "upstream_drainage_area": {
                    "min_km2": comprehensive_stats.get('upa', {}).get('min', 'N/A'),
                    "max_km2": comprehensive_stats.get('upa', {}).get('max', 'N/A'),
                    "mean_km2": comprehensive_stats.get('upa', {}).get('mean', 'N/A')
                },
                "height_above_drainage": {
                    "min_m": comprehensive_stats.get('hnd', {}).get('min', 'N/A'),
                    "max_m": comprehensive_stats.get('hnd', {}).get('max', 'N/A'),
                    "mean_m": comprehensive_stats.get('hnd', {}).get('mean', 'N/A')
                },
                "water_coverage": {
                    "water_pixels": water_pixels,
                    "total_pixels": total_pixels,
                    "water_percentage": water_percentage
                }
            },
            "analysis_summary": {
                "terrain_relief_m": (comprehensive_stats.get('elv', {}).get('max', 0) or 0) - (comprehensive_stats.get('elv', {}).get('min', 0) or 0) if comprehensive_stats.get('elv', {}).get('max') and comprehensive_stats.get('elv', {}).get('min') else 'N/A',
                "hydrological_complexity": "High" if water_percentage > 5 else "Medium" if water_percentage > 1 else "Low",
                "dataset_coverage": "Complete"
            },
            "dataset_info": {
                "pixel_size": "92.77 meters",
                "bands_analyzed": all_bands,
                "coordinate_system": "WGS84",
                "vertical_datum": "EGM96 geoid"
            }
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_comprehensive_map(merit_image, region, zoom_level, bounds)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in comprehensive analysis: {str(e)}")

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
async def _generate_elevation_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive elevation map."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add elevation layer
        elv_vis = {
            'min': 0, 'max': 3000,
            'palette': ['blue', 'green', 'yellow', 'orange', 'red', 'white']
        }
        m.add_layer(image.select('elv'), elv_vis, f'Elevation - {region}')
        
        # Add height above drainage
        hnd_vis = {
            'min': 0, 'max': 100,
            'palette': ['navy', 'blue', 'cyan', 'yellow', 'red']
        }
        m.add_layer(image.select('hnd'), hnd_vis, f'Height Above Drainage - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merit_elevation_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "MERIT Hydro",
            "layers": ["Elevation", "Height Above Drainage"]
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_flow_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive flow direction map."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add flow direction layer
        flow_vis = {
            'min': 0, 'max': 128,
            'palette': ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'magenta']
        }
        m.add_layer(image.select('dir'), flow_vis, f'Flow Direction - {region}')
        
        # Add water classification
        water_vis = {
            'min': 0, 'max': 1,
            'palette': ['brown', 'blue']
        }
        m.add_layer(image.select('wat'), water_vis, f'Water Bodies - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merit_flow_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "MERIT Hydro",
            "layers": ["Flow Direction", "Water Bodies"]
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_river_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive river width map."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add river width layer
        river_vis = {
            'min': 0, 'max': 500,
            'palette': ['white', 'lightblue', 'blue', 'darkblue', 'navy']
        }
        m.add_layer(image.select('wth'), river_vis, f'River Width - {region}')
        
        # Add visualization layer
        m.add_layer(image.select('viswth'), river_vis, f'River Width Visualization - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merit_rivers_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "MERIT Hydro",
            "layers": ["River Width", "River Width Visualization"]
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_drainage_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate interactive drainage analysis map."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add drainage area layer
        drainage_vis = {
            'min': 0, 'max': 1000,
            'palette': ['white', 'yellow', 'orange', 'red', 'darkred']
        }
        m.add_layer(image.select('upa'), drainage_vis, f'Upstream Drainage Area - {region}')
        
        # Add upstream pixels layer
        pixel_vis = {
            'min': 0, 'max': 10000,
            'palette': ['lightblue', 'blue', 'darkblue', 'purple', 'black']
        }
        m.add_layer(image.select('upg'), pixel_vis, f'Upstream Pixels - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merit_drainage_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "MERIT Hydro",
            "layers": ["Upstream Drainage Area", "Upstream Pixels"]
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_comprehensive_map(
    image: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry
) -> Dict[str, Any]:
    """Generate comprehensive hydrological analysis map."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Add elevation as base layer
        elv_vis = {
            'min': 0, 'max': 2000,
            'palette': ['blue', 'green', 'yellow', 'orange', 'red']
        }
        m.add_layer(image.select('elv'), elv_vis, f'Elevation - {region}')
        
        # Add river network
        river_vis = {
            'min': 0, 'max': 200,
            'palette': ['transparent', 'lightblue', 'blue', 'darkblue']
        }
        m.add_layer(image.select('wth').updateMask(image.select('wth').gt(0)), 
                   river_vis, f'River Network - {region}')
        
        # Add drainage basins
        drainage_vis = {
            'min': 0, 'max': 500,
            'palette': ['white', 'yellow', 'orange', 'red'],
            'opacity': 0.7
        }
        m.add_layer(image.select('upa'), drainage_vis, f'Drainage Basins - {region}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merit_comprehensive_{region}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "region": region,
            "dataset": "MERIT Hydro",
            "layers": ["Elevation", "River Network", "Drainage Basins"]
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)