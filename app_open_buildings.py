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
    title="Google Research Open Buildings API",
    description="API for accessing Google Research Open Buildings dataset - building footprints with area and confidence data",
    version="1.0.0"
)

# Helper functions for region handling (borrowed from VIIRS)
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

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Google Research Open Buildings API",
        "description": "Access building footprints with area, confidence scores, and location data",
        "dataset": "GOOGLE/Research/open-buildings/v3/polygons",
        "coverage": "Global building footprints",
        "data_fields": {
            "area_in_meters": "Building area in square meters",
            "confidence": "Model confidence score [0.65-1.0]",
            "full_plus_code": "Plus Code at building centroid",
            "longitude_latitude": "Building centroid coordinates"
        },
        "endpoints": [
            "/buildings-health",
            "/buildings-check-coverage",
            "/buildings-area-analysis",
            "/buildings-confidence-analysis", 
            "/buildings-count-statistics",
            "/buildings-sample-data",
            "/gaul-search",
            "/available-regions",
            "/docs"
        ]
    }

@app.get("/buildings-health")
async def health_check():
    """Check if Earth Engine and Open Buildings dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test Open Buildings dataset access
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        
        # Test with a small area (Bangalore center)
        bangalore_center = ee.Geometry.Rectangle([77.58, 12.96, 77.62, 13.00])
        sample_buildings = buildings_collection.filterBounds(bangalore_center).limit(10)
        sample_count = sample_buildings.size().getInfo()
        
        # Get sample building data
        if sample_count > 0:
            sample_feature = sample_buildings.first().getInfo()
            sample_properties = sample_feature['properties']
        else:
            sample_properties = "No buildings found in test area"
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_result": test_result,
            "dataset": "GOOGLE/Research/open-buildings/v3/polygons",
            "sample_area": "Bangalore center",
            "sample_buildings_found": sample_count,
            "sample_properties": sample_properties,
            "available_fields": ["area_in_meters", "confidence", "full_plus_code", "longitude_latitude"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/buildings-check-coverage")
async def check_buildings_coverage(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)"),
    sample_size: int = Query(1000, description="Number of buildings to sample for analysis", le=5000)
):
    """Check Open Buildings dataset coverage for specified region."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load buildings collection
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        region_buildings = buildings_collection.filterBounds(bounds)
        
        # Get total building count (this might be expensive for large regions)
        try:
            total_buildings = region_buildings.size().getInfo()
        except Exception as count_error:
            print(f"Could not get exact count due to size: {count_error}")
            # Sample to estimate
            sample_buildings = region_buildings.limit(sample_size)
            sample_count = sample_buildings.size().getInfo()
            total_buildings = f">{sample_count} (estimated, region too large for exact count)"
        
        if isinstance(total_buildings, int) and total_buildings == 0:
            return {
                "success": False,
                "message": f"No buildings found in {region}",
                "suggestion": "Try a different region or check if this area has building data coverage"
            }
        
        # Get sample for analysis
        sample_buildings = region_buildings.limit(min(sample_size, 100))
        sample_list = sample_buildings.getInfo()
        
        if not sample_list['features']:
            return {
                "success": False, 
                "message": f"No building data available for {region}"
            }
        
        # Analyze sample properties
        areas = []
        confidences = []
        plus_codes = []
        
        for feature in sample_list['features']:
            props = feature['properties']
            if 'area_in_meters' in props and props['area_in_meters'] is not None:
                areas.append(props['area_in_meters'])
            if 'confidence' in props and props['confidence'] is not None:
                confidences.append(props['confidence'])
            if 'full_plus_code' in props and props['full_plus_code'] is not None:
                plus_codes.append(props['full_plus_code'])
        
        return {
            "success": True,
            "region": region,
            "total_buildings": total_buildings,
            "sample_analyzed": len(sample_list['features']),
            "coverage_analysis": {
                "has_area_data": len(areas),
                "has_confidence_data": len(confidences),
                "has_plus_codes": len(plus_codes),
                "area_range_sqm": {
                    "min": min(areas) if areas else None,
                    "max": max(areas) if areas else None,
                    "avg": sum(areas) / len(areas) if areas else None
                },
                "confidence_range": {
                    "min": min(confidences) if confidences else None,
                    "max": max(confidences) if confidences else None,
                    "avg": sum(confidences) / len(confidences) if confidences else None
                }
            },
            "sample_plus_codes": plus_codes[:5] if plus_codes else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking coverage: {str(e)}")

@app.get("/buildings-area-analysis")
async def analyze_building_areas(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    min_area: Optional[float] = Query(None, description="Minimum building area in square meters"),
    max_area: Optional[float] = Query(None, description="Maximum building area in square meters"),
    confidence_threshold: float = Query(0.7, description="Minimum confidence score", ge=0.65, le=1.0),
    sample_size: int = Query(2000, description="Number of buildings to analyze", le=10000),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze building areas in the specified region with filtering options."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load and filter buildings
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        region_buildings = buildings_collection.filterBounds(bounds)
        
        # Apply confidence filter
        filtered_buildings = region_buildings.filter(ee.Filter.gte('confidence', confidence_threshold))
        
        # Apply area filters if specified
        if min_area is not None:
            filtered_buildings = filtered_buildings.filter(ee.Filter.gte('area_in_meters', min_area))
        if max_area is not None:
            filtered_buildings = filtered_buildings.filter(ee.Filter.lte('area_in_meters', max_area))
        
        # Get sample for detailed analysis
        sample_buildings = filtered_buildings.limit(sample_size)
        buildings_list = sample_buildings.getInfo()
        
        if not buildings_list['features']:
            return {
                "success": False,
                "message": f"No buildings found matching criteria in {region}",
                "filters_applied": {
                    "confidence_threshold": confidence_threshold,
                    "min_area": min_area,
                    "max_area": max_area
                }
            }
        
        # Process building data
        areas = []
        confidences = []
        large_buildings = []  # > 1000 sqm
        small_buildings = []  # < 100 sqm
        
        for feature in buildings_list['features']:
            props = feature['properties']
            area = props.get('area_in_meters')
            confidence = props.get('confidence')
            
            if area is not None:
                areas.append(area)
                if area > 1000:
                    large_buildings.append({
                        "area": area,
                        "confidence": confidence,
                        "plus_code": props.get('full_plus_code')
                    })
                elif area < 100:
                    small_buildings.append({
                        "area": area,
                        "confidence": confidence,
                        "plus_code": props.get('full_plus_code')
                    })
            
            if confidence is not None:
                confidences.append(confidence)
        
        # Calculate statistics
        total_area = sum(areas)
        area_stats = {
            "total_buildings_analyzed": len(areas),
            "total_area_sqm": total_area,
            "total_area_hectares": total_area / 10000,
            "min_area_sqm": min(areas) if areas else None,
            "max_area_sqm": max(areas) if areas else None,
            "avg_area_sqm": total_area / len(areas) if areas else None,
            "median_area_sqm": sorted(areas)[len(areas)//2] if areas else None
        }
        
        # Categorize buildings by size
        size_categories = {
            "very_small": len([a for a in areas if a < 50]),
            "small": len([a for a in areas if 50 <= a < 100]),
            "medium": len([a for a in areas if 100 <= a < 500]),
            "large": len([a for a in areas if 500 <= a < 1000]),
            "very_large": len([a for a in areas if a >= 1000])
        }
        
        return {
            "success": True,
            "region": region,
            "filters_applied": {
                "confidence_threshold": confidence_threshold,
                "min_area": min_area,
                "max_area": max_area
            },
            "area_statistics": area_stats,
            "size_distribution": size_categories,
            "confidence_stats": {
                "min": min(confidences) if confidences else None,
                "max": max(confidences) if confidences else None,
                "avg": sum(confidences) / len(confidences) if confidences else None
            },
            "notable_buildings": {
                "largest_buildings": sorted(large_buildings, key=lambda x: x['area'], reverse=True)[:5],
                "smallest_buildings": sorted(small_buildings, key=lambda x: x['area'])[:5]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing building areas: {str(e)}")

@app.get("/buildings-confidence-analysis")
async def analyze_building_confidence(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    sample_size: int = Query(3000, description="Number of buildings to analyze", le=10000),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Analyze building detection confidence scores in the specified region."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load buildings
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        region_buildings = buildings_collection.filterBounds(bounds).limit(sample_size)
        
        buildings_list = region_buildings.getInfo()
        
        if not buildings_list['features']:
            return {
                "success": False,
                "message": f"No buildings found in {region}"
            }
        
        # Process confidence data
        confidences = []
        confidence_area_pairs = []
        
        for feature in buildings_list['features']:
            props = feature['properties']
            confidence = props.get('confidence')
            area = props.get('area_in_meters')
            
            if confidence is not None:
                confidences.append(confidence)
                if area is not None:
                    confidence_area_pairs.append((confidence, area))
        
        # Confidence distribution
        confidence_bins = {
            "very_high": len([c for c in confidences if c >= 0.9]),
            "high": len([c for c in confidences if 0.8 <= c < 0.9]),
            "medium": len([c for c in confidences if 0.75 <= c < 0.8]),
            "acceptable": len([c for c in confidences if 0.65 <= c < 0.75])
        }
        
        # Confidence vs Area analysis
        high_conf_large = len([pair for pair in confidence_area_pairs if pair[0] >= 0.9 and pair[1] >= 500])
        low_conf_small = len([pair for pair in confidence_area_pairs if pair[0] < 0.75 and pair[1] < 100])
        
        return {
            "success": True,
            "region": region,
            "buildings_analyzed": len(confidences),
            "confidence_statistics": {
                "min": min(confidences) if confidences else None,
                "max": max(confidences) if confidences else None,
                "average": sum(confidences) / len(confidences) if confidences else None,
                "median": sorted(confidences)[len(confidences)//2] if confidences else None
            },
            "confidence_distribution": confidence_bins,
            "quality_insights": {
                "high_confidence_large_buildings": high_conf_large,
                "low_confidence_small_buildings": low_conf_small,
                "total_high_confidence": confidence_bins["very_high"] + confidence_bins["high"],
                "detection_reliability": f"{((confidence_bins['very_high'] + confidence_bins['high']) / len(confidences) * 100):.1f}%" if confidences else "N/A"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing confidence: {str(e)}")

@app.get("/buildings-count-statistics")
async def get_building_count_statistics(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    grid_size: float = Query(0.01, description="Grid cell size in degrees for density analysis", gt=0, le=0.1),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get building count and density statistics for the specified region."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load buildings
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        region_buildings = buildings_collection.filterBounds(bounds)
        
        # Try to get total count (may fail for very large regions)
        try:
            total_count = region_buildings.size().getInfo()
            exact_count = True
        except Exception:
            # If too many buildings, estimate from sample
            sample_buildings = region_buildings.limit(10000)
            sample_count = sample_buildings.size().getInfo()
            total_count = f">{sample_count} (estimated)"
            exact_count = False
        
        # Get region area for density calculation
        region_area_sqkm = bounds.area().divide(1000000).getInfo()  # Convert to km²
        
        # Sample buildings for detailed analysis
        sample_buildings = region_buildings.limit(5000)
        buildings_list = sample_buildings.getInfo()
        
        # Calculate density if we have exact count
        buildings_per_sqkm = None
        if exact_count and isinstance(total_count, int):
            buildings_per_sqkm = total_count / region_area_sqkm if region_area_sqkm > 0 else None
        
        # Analyze sample for area-based statistics
        total_building_area = 0
        area_coverage_percent = None
        
        if buildings_list['features']:
            for feature in buildings_list['features']:
                area = feature['properties'].get('area_in_meters', 0)
                if area:
                    total_building_area += area
            
            # Estimate coverage percentage from sample
            sample_coverage = (total_building_area / (region_area_sqkm * 1000000)) * 100
            area_coverage_percent = f"{sample_coverage:.3f}% (from sample)"
        
        return {
            "success": True,
            "region": region,
            "region_info": {
                "area_sq_km": round(region_area_sqkm, 2),
                "area_sq_miles": round(region_area_sqkm * 0.386102, 2)
            },
            "building_statistics": {
                "total_buildings": total_count,
                "count_is_exact": exact_count,
                "buildings_per_sq_km": round(buildings_per_sqkm, 2) if buildings_per_sqkm else "Cannot calculate",
                "sample_analyzed": len(buildings_list['features']) if buildings_list['features'] else 0
            },
            "coverage_analysis": {
                "building_area_coverage": area_coverage_percent,
                "sample_total_building_area_sqm": total_building_area,
                "sample_total_building_area_hectares": round(total_building_area / 10000, 2)
            },
            "methodology_note": "Large regions use sampling for area estimates. Use smaller regions for exact counts."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating statistics: {str(e)}")

@app.get("/buildings-sample-data")
async def get_sample_buildings(
    region: str = Query("bangalore", description="Region: predefined city, district name, state name, or custom"),
    state_name: Optional[str] = Query(None, description="State name (for district disambiguation)"),
    sample_size: int = Query(10, description="Number of sample buildings to return", le=100),
    min_confidence: float = Query(0.8, description="Minimum confidence score", ge=0.65, le=1.0),
    west: Optional[float] = Query(None, description="Western boundary (for custom region)"),
    south: Optional[float] = Query(None, description="Southern boundary (for custom region)"),
    east: Optional[float] = Query(None, description="Eastern boundary (for custom region)"),
    north: Optional[float] = Query(None, description="Northern boundary (for custom region)")
):
    """Get sample building data with full properties for inspection."""
    try:
        # Define region bounds
        bounds = _get_region_bounds(region, west, south, east, north, state_name)
        
        # Load and filter buildings
        buildings_collection = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
        region_buildings = buildings_collection.filterBounds(bounds)
        
        # Apply confidence filter
        filtered_buildings = region_buildings.filter(ee.Filter.gte('confidence', min_confidence))
        
        # Get sample
        sample_buildings = filtered_buildings.limit(sample_size)
        buildings_list = sample_buildings.getInfo()
        
        if not buildings_list['features']:
            return {
                "success": False,
                "message": f"No buildings found with confidence >= {min_confidence} in {region}"
            }
        
        # Process sample data
        sample_data = []
        for i, feature in enumerate(buildings_list['features']):
            props = feature['properties']
            geometry = feature.get('geometry')
            
            # Extract centroid coordinates if available
            centroid_coords = None
            if geometry and geometry['type'] == 'Point':
                centroid_coords = geometry['coordinates']
            
            sample_data.append({
                "building_id": i + 1,
                "area_sqm": props.get('area_in_meters'),
                "area_sqft": round(props.get('area_in_meters', 0) * 10.764, 2) if props.get('area_in_meters') else None,
                "confidence": props.get('confidence'),
                "plus_code": props.get('full_plus_code'),
                "centroid_lon_lat": centroid_coords,
                "size_category": _categorize_building_size(props.get('area_in_meters', 0))
            })
        
        return {
            "success": True,
            "region": region,
            "filters_applied": {
                "min_confidence": min_confidence,
                "sample_size": sample_size
            },
            "buildings_found": len(sample_data),
            "sample_buildings": sample_data,
            "summary": {
                "avg_area_sqm": sum([b['area_sqm'] for b in sample_data if b['area_sqm']]) / len([b for b in sample_data if b['area_sqm']]) if sample_data else 0,
                "avg_confidence": sum([b['confidence'] for b in sample_data if b['confidence']]) / len([b for b in sample_data if b['confidence']]) if sample_data else 0,
                "size_distribution": _get_size_distribution(sample_data)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sample data: {str(e)}")

def _categorize_building_size(area_sqm: float) -> str:
    """Categorize building by size."""
    if area_sqm < 50:
        return "Very Small"
    elif area_sqm < 100:
        return "Small"
    elif area_sqm < 500:
        return "Medium"
    elif area_sqm < 1000:
        return "Large"
    else:
        return "Very Large"

def _get_size_distribution(buildings: List[Dict]) -> Dict[str, int]:
    """Get size distribution of buildings."""
    distribution = {"Very Small": 0, "Small": 0, "Medium": 0, "Large": 0, "Very Large": 0}
    for building in buildings:
        if building['area_sqm']:
            category = _categorize_building_size(building['area_sqm'])
            distribution[category] += 1
    return distribution

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, reload=True)