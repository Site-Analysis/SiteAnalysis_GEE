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
    title="UMD Hansen Global Forest Change API",
    description="API for accessing UMD Hansen Global Forest Change v1.12 dataset with forest cover, loss/gain, and Landsat composites",
    version="1.0.0"
)

# Helper functions for region handling (including GAUL integration from previous work)
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

# Forest loss year mapping
LOSS_YEAR_MAPPING = {
    0: "No loss",
    1: "2001", 2: "2002", 3: "2003", 4: "2004", 5: "2005", 
    6: "2006", 7: "2007", 8: "2008", 9: "2009", 10: "2010",
    11: "2011", 12: "2012", 13: "2013", 14: "2014", 15: "2015",
    16: "2016", 17: "2017", 18: "2018", 19: "2019", 20: "2020",
    21: "2021", 22: "2022", 23: "2023", 24: "2024"
}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "UMD Hansen Global Forest Change API",
        "description": "Access Global Forest Change data (2000-2024) with forest cover, loss/gain analysis, and Landsat composites",
        "dataset": "UMD/hansen/global_forest_change_2024_v1_12",
        "pixel_size": "30 meters (approximately)",
        "time_period": "2000-2024",
        "available_bands": {
            "forest_analysis": ["treecover2000", "loss", "gain", "lossyear"],
            "landsat_first_year": ["first_b30", "first_b40", "first_b50", "first_b70"],
            "landsat_last_year": ["last_b30", "last_b40", "last_b50", "last_b70"],
            "metadata": ["datamask"]
        },
        "endpoints": [
            "/hansen-health",
            "/hansen-forest-cover",
            "/hansen-forest-change", 
            "/hansen-loss-analysis",
            "/hansen-landsat-composites",
            "/hansen-forest-statistics",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/hansen-health")
async def health_check():
    """Check if Earth Engine and Hansen dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test Hansen dataset access
        hansen_dataset = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Check available bands
        band_names = hansen_dataset.bandNames().getInfo()
        
        # Test India area coverage
        india_bounds = ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])
        india_sample = hansen_dataset.select('treecover2000').clip(india_bounds)
        
        # Get a small sample to verify data
        sample_stats = india_sample.reduceRegion(
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
            "dataset": "UMD/hansen/global_forest_change_2024_v1_12",
            "available_bands": band_names,
            "band_count": len(band_names),
            "pixel_size": "~30 meters",
            "india_coverage": "Available",
            "sample_tree_cover_range": {
                "min": sample_stats.get('treecover2000_min', 'N/A'),
                "max": sample_stats.get('treecover2000_max', 'N/A')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/hansen-forest-cover")
async def get_forest_cover(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    min_tree_cover: int = Query(30, description="Minimum tree cover percentage (0-100)", ge=0, le=100),
    include_map: bool = Query(True, description="Generate forest cover map"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get forest cover analysis for year 2000."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load Hansen dataset
        hansen_image = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Get tree cover for year 2000
        tree_cover = hansen_image.select('treecover2000').clip(bounds)
        
        # Create forest mask based on minimum tree cover
        forest_mask = tree_cover.gte(min_tree_cover)
        
        # Calculate statistics
        tree_cover_stats = tree_cover.reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=bounds,
            scale=100,  # Coarser scale for large areas
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Calculate forest area
        forest_area_pixels = forest_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=30,  # Original resolution for area calculation
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Convert pixels to area (each pixel is ~900 m² at 30m resolution)
        forest_pixels = forest_area_pixels.get('treecover2000', 0)
        forest_area_km2 = forest_pixels * 900 / 1000000  # Convert to km²
        
        response_data = {
            "success": True,
            "region": region,
            "analysis_year": 2000,
            "min_tree_cover_threshold": min_tree_cover,
            "tree_cover_statistics": {
                "min_percent": tree_cover_stats.get('treecover2000_min', 'N/A'),
                "max_percent": tree_cover_stats.get('treecover2000_max', 'N/A'),
                "mean_percent": tree_cover_stats.get('treecover2000_mean', 'N/A')
            },
            "forest_area": {
                "forest_pixels": forest_pixels,
                "forest_area_km2": round(forest_area_km2, 2)
            },
            "dataset": "UMD Hansen Global Forest Change v1.12"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_hansen_map(tree_cover, forest_mask, region, zoom_level, bounds, "forest_cover")
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing forest cover: {str(e)}")

@app.get("/hansen-forest-change")
async def get_forest_change(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    include_map: bool = Query(True, description="Generate forest change map"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get forest loss and gain analysis."""
    try:
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load Hansen dataset
        hansen_image = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Get loss and gain bands
        loss_band = hansen_image.select('loss').clip(bounds)
        gain_band = hansen_image.select('gain').clip(bounds)
        tree_cover_2000 = hansen_image.select('treecover2000').clip(bounds)
        
        # Calculate loss area
        loss_area_pixels = loss_band.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=30,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Calculate gain area
        gain_area_pixels = gain_band.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=30,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Calculate total forest area in 2000
        forest_2000_stats = tree_cover_2000.gte(30).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=30,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Convert to areas
        loss_pixels = loss_area_pixels.get('loss', 0)
        gain_pixels = gain_area_pixels.get('gain', 0)
        forest_2000_pixels = forest_2000_stats.get('treecover2000', 0)
        
        loss_area_km2 = loss_pixels * 900 / 1000000
        gain_area_km2 = gain_pixels * 900 / 1000000
        forest_2000_area_km2 = forest_2000_pixels * 900 / 1000000
        
        # Calculate percentages
        loss_percentage = (loss_area_km2 / forest_2000_area_km2 * 100) if forest_2000_area_km2 > 0 else 0
        
        response_data = {
            "success": True,
            "region": region,
            "analysis_period": "2000-2024",
            "forest_change_analysis": {
                "initial_forest_2000": {
                    "area_km2": round(forest_2000_area_km2, 2),
                    "pixels": forest_2000_pixels
                },
                "forest_loss_2000_2024": {
                    "area_km2": round(loss_area_km2, 2),
                    "pixels": loss_pixels,
                    "percentage_of_2000_forest": round(loss_percentage, 2)
                },
                "forest_gain_2000_2012": {
                    "area_km2": round(gain_area_km2, 2),
                    "pixels": gain_pixels,
                    "note": "Gain data only available for 2000-2012 period"
                }
            },
            "dataset": "UMD Hansen Global Forest Change v1.12"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_hansen_map(loss_band, gain_band, region, zoom_level, bounds, "forest_change")
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing forest change: {str(e)}")

@app.get("/hansen-loss-analysis")
async def get_loss_by_year(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    start_year: int = Query(2001, description="Start year (2001-2024)", ge=2001, le=2024),
    end_year: int = Query(2024, description="End year (2001-2024)", ge=2001, le=2024),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get forest loss analysis by year."""
    try:
        if start_year > end_year:
            raise HTTPException(status_code=400, detail="Start year must be <= end year")
        
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load Hansen dataset
        hansen_image = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Get loss year band
        loss_year = hansen_image.select('lossyear').clip(bounds)
        
        # Calculate loss by year
        yearly_loss = {}
        total_loss_area = 0
        
        for year_code in range(start_year - 2000, end_year - 2000 + 1):
            year = year_code + 2000
            year_mask = loss_year.eq(year_code)
            
            year_loss_pixels = year_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=100,  # Coarser scale for performance
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            loss_pixels = year_loss_pixels.get('lossyear', 0)
            loss_area_km2 = loss_pixels * 10000 / 1000000  # 100m scale adjustment
            
            yearly_loss[str(year)] = {
                "pixels": loss_pixels,
                "area_km2": round(loss_area_km2, 3)
            }
            total_loss_area += loss_area_km2
        
        return {
            "success": True,
            "region": region,
            "analysis_period": f"{start_year}-{end_year}",
            "yearly_forest_loss": yearly_loss,
            "summary": {
                "total_loss_area_km2": round(total_loss_area, 2),
                "analysis_scale": "100 meters (for performance)"
            },
            "dataset": "UMD Hansen Global Forest Change v1.12"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing yearly loss: {str(e)}")

@app.get("/hansen-landsat-composites")
async def get_landsat_composites(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    composite_type: str = Query("first", description="Composite type: first (2000) or last (2024)", regex="^(first|last)$"),
    bands: str = Query("b30,b40,b50,b70", description="Comma-separated bands: b30 (red), b40 (NIR), b50 (SWIR1), b70 (SWIR2)"),
    include_map: bool = Query(True, description="Generate Landsat composite map"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get Landsat composite imagery analysis."""
    try:
        # Parse bands
        selected_bands = [band.strip() for band in bands.split(',')]
        valid_bands = ['b30', 'b40', 'b50', 'b70']
        
        for band in selected_bands:
            if band not in valid_bands:
                raise HTTPException(status_code=400, detail=f"Invalid band '{band}'. Valid bands: {valid_bands}")
        
        # Define region bounds and zoom level
        bounds_info = _get_region_bounds_with_zoom(region, west, south, east, north, state_name)
        bounds = bounds_info['bounds']
        zoom_level = bounds_info['zoom']
        
        # Load Hansen dataset
        hansen_image = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Select composite bands
        prefix = composite_type + "_"
        selected_band_names = [prefix + band for band in selected_bands]
        
        composite_image = hansen_image.select(selected_band_names).clip(bounds)
        
        # Calculate statistics for each band
        band_stats = {}
        for i, band in enumerate(selected_bands):
            full_band_name = selected_band_names[i]
            band_data = composite_image.select(full_band_name)
            
            stats = band_data.reduceRegion(
                reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
                geometry=bounds,
                scale=100,
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            band_info = {
                "min": stats.get(f'{full_band_name}_min', 'N/A'),
                "max": stats.get(f'{full_band_name}_max', 'N/A'),
                "mean": stats.get(f'{full_band_name}_mean', 'N/A')
            }
            
            # Add band description
            if band == 'b30':
                band_info["description"] = "Red (0.63-0.69µm)"
            elif band == 'b40':
                band_info["description"] = "NIR (0.77-0.90µm)"
            elif band == 'b50':
                band_info["description"] = "SWIR1 (1.55-1.75µm)"
            elif band == 'b70':
                band_info["description"] = "SWIR2 (2.09-2.35µm)"
            
            band_stats[band] = band_info
        
        composite_year = "2000" if composite_type == "first" else "2024"
        
        response_data = {
            "success": True,
            "region": region,
            "composite_type": composite_type,
            "composite_year": composite_year,
            "landsat_bands": band_stats,
            "band_descriptions": {
                "b30": "Landsat Red (0.63-0.69µm)",
                "b40": "Landsat NIR (0.77-0.90µm)", 
                "b50": "Landsat SWIR1 (1.55-1.75µm)",
                "b70": "Landsat SWIR2 (2.09-2.35µm)"
            },
            "dataset": "UMD Hansen Global Forest Change v1.12"
        }
        
        # Generate map if requested
        if include_map:
            map_result = await _generate_landsat_map(composite_image, selected_bands, region, zoom_level, bounds, composite_type)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing Landsat composites: {str(e)}")

@app.get("/hansen-forest-statistics")
async def get_forest_statistics(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get comprehensive forest statistics summary."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load Hansen dataset
        hansen_image = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # Get all relevant bands
        tree_cover = hansen_image.select('treecover2000').clip(bounds)
        loss = hansen_image.select('loss').clip(bounds)
        gain = hansen_image.select('gain').clip(bounds)
        
        # Calculate comprehensive statistics
        # Tree cover distribution
        tree_cover_histogram = tree_cover.reduceRegion(
            reducer=ee.Reducer.histogram(100, 100),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo()
        
        # Forest area by cover class
        forest_classes = {}
        for threshold in [10, 25, 50, 75]:
            forest_mask = tree_cover.gte(threshold)
            forest_pixels = forest_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=bounds,
                scale=100,
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            pixels = forest_pixels.get('treecover2000', 0)
            area_km2 = pixels * 10000 / 1000000  # 100m scale
            
            forest_classes[f"cover_gte_{threshold}%"] = {
                "pixels": pixels,
                "area_km2": round(area_km2, 2)
            }
        
        # Loss and gain totals
        loss_pixels = loss.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo().get('loss', 0)
        
        gain_pixels = gain.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bounds,
            scale=100,
            maxPixels=1e8,
            bestEffort=True
        ).getInfo().get('gain', 0)
        
        return {
            "success": True,
            "region": region,
            "forest_cover_classes": forest_classes,
            "forest_change_totals": {
                "loss_2000_2024": {
                    "pixels": loss_pixels,
                    "area_km2": round(loss_pixels * 10000 / 1000000, 2)
                },
                "gain_2000_2012": {
                    "pixels": gain_pixels,
                    "area_km2": round(gain_pixels * 10000 / 1000000, 2)
                }
            },
            "analysis_note": "Statistics calculated at 100m scale for performance",
            "dataset": "UMD Hansen Global Forest Change v1.12"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating forest statistics: {str(e)}")

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

async def _generate_hansen_map(
    primary_layer: ee.Image,
    secondary_layer: ee.Image,
    region: str,
    zoom_level: int,
    bounds: ee.Geometry,
    map_type: str
) -> Dict[str, Any]:
    """Generate interactive map with Hansen forest data."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        if map_type == "forest_cover":
            # Tree cover visualization
            tree_vis = {'min': 0, 'max': 100, 'palette': ['black', 'green']}
            m.add_layer(primary_layer, tree_vis, f'Tree Cover 2000 - {region}')
            
            # Forest mask overlay
            forest_vis = {'palette': ['darkgreen']}
            m.add_layer(secondary_layer.updateMask(secondary_layer), forest_vis, f'Forest Areas - {region}')
            
        elif map_type == "forest_change":
            # Loss in red
            loss_vis = {'palette': ['red']}
            m.add_layer(primary_layer.updateMask(primary_layer), loss_vis, f'Forest Loss 2000-2024 - {region}')
            
            # Gain in blue
            gain_vis = {'palette': ['blue']}
            m.add_layer(secondary_layer.updateMask(secondary_layer), gain_vis, f'Forest Gain 2000-2012 - {region}')
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hansen_{map_type}_{region.lower().replace(' ', '_')}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "map_type": map_type,
            "region": region,
            "dataset": "UMD Hansen Global Forest Change"
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

async def _generate_landsat_map(
    composite_image: ee.Image,
    bands: List[str],
    region: str,
    zoom_level: int,
    bounds: ee.Geometry,
    composite_type: str
) -> Dict[str, Any]:
    """Generate interactive map with Landsat composite imagery."""
    try:
        m = geemap.Map()
        m.center_object(bounds, zoom_level)
        
        # Create visualization for each band
        for band in bands:
            full_band_name = f"{composite_type}_{band}"
            vis_params = {'min': 0, 'max': 4000, 'palette': ['black', 'white']}
            
            if band == 'b30':  # Red
                vis_params['palette'] = ['black', 'red']
            elif band == 'b40':  # NIR
                vis_params['palette'] = ['black', 'darkred']
            elif band == 'b50':  # SWIR1
                vis_params['palette'] = ['black', 'orange']
            elif band == 'b70':  # SWIR2
                vis_params['palette'] = ['black', 'yellow']
            
            m.add_layer(composite_image.select(full_band_name), vis_params, f'{band.upper()} - {region}')
        
        # If we have RGB+NIR, create false color composite
        if all(band in bands for band in ['b40', 'b30', 'b50']):
            false_color_bands = [f"{composite_type}_b40", f"{composite_type}_b30", f"{composite_type}_b50"]
            false_color_vis = {'min': 0, 'max': 4000}
            m.add_layer(composite_image.select(false_color_bands), false_color_vis, f'False Color Composite - {region}')
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hansen_landsat_{composite_type}_{region.lower().replace(' ', '_')}_{timestamp}.html"
        
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "composite_type": composite_type,
            "bands": bands,
            "region": region
        }
        
    except Exception as e:
        return {"map_generated": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, reload=True)