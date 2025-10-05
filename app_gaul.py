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
    title="India Administrative Boundaries API - FAO GAUL",
    description="API for accessing India's administrative boundaries using FAO GAUL dataset with ADM2 (district/municipality) level data",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "India Administrative Boundaries API - FAO GAUL Dataset",
        "description": "Access India's administrative boundaries including ADM2 (district/municipality) level",
        "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2",
        "admin_levels": {
            "ADM0": "Country level (India)",
            "ADM1": "State/Province level", 
            "ADM2": "District/Municipality level"
        },
        "endpoints": [
            "/gaul-health",
            "/gaul-check-levels",
            "/gaul-boundaries", 
            "/gaul-states",
            "/gaul-districts",
            "/gaul-state-districts/{state_name}",
            "/gaul-quick-search",
            "/docs"
        ]
    }

@app.get("/gaul-health")
async def health_check():
    """Check if Earth Engine and FAO GAUL dataset are accessible."""
    try:
        # Test Earth Engine connection
        test_result = ee.Number(10).getInfo()
        
        # Test FAO GAUL dataset access
        gaul_dataset = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        dataset_size = gaul_dataset.size().getInfo()
        
        # Test India data specifically
        india_data = gaul_dataset.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        india_count = india_data.size().getInfo()
        
        return {
            "status": "healthy",
            "earth_engine": "connected", 
            "test_result": test_result,
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2",
            "total_global_features": dataset_size,
            "india_features": india_count,
            "india_available": india_count > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/gaul-check-levels")
async def check_available_levels():
    """Check what administrative levels are available for India in FAO GAUL dataset."""
    try:
        # Load FAO GAUL dataset
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        
        # Filter for India
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        total_count = india_boundaries.size().getInfo()
        
        if total_count == 0:
            return {
                "success": False,
                "message": "No data found for India in FAO GAUL dataset",
                "suggestion": "Check if country name should be 'India' or try alternative filters"
            }
        
        # Get sample feature to check available properties
        sample_feature = india_boundaries.first().getInfo()
        available_properties = list(sample_feature['properties'].keys())
        
        # Get unique values for key fields
        adm0_names = india_boundaries.aggregate_array('ADM0_NAME').distinct().getInfo()
        adm1_count = india_boundaries.aggregate_array('ADM1_NAME').distinct().size().getInfo()
        adm2_count = india_boundaries.aggregate_array('ADM2_NAME').distinct().size().getInfo()
        
        return {
            "success": True,
            "country": "India",
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2",
            "total_features": total_count,
            "unique_states_provinces": adm1_count,
            "unique_districts_municipalities": adm2_count,
            "country_names_found": adm0_names,
            "available_properties": available_properties,
            "sample_feature": sample_feature['properties'],
            "analysis": {
                "has_country_data": len(adm0_names) > 0,
                "has_state_data": adm1_count > 0,
                "has_district_data": adm2_count > 0,
                "data_completeness": "Full ADM0/ADM1/ADM2 hierarchy available" if adm2_count > 0 else "Limited data"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking levels: {str(e)}")

@app.get("/gaul-boundaries")
async def get_gaul_boundaries(
    admin_level: str = Query("ADM2", description="Admin level: ADM0 (country), ADM1 (state), ADM2 (district)"),
    include_map: bool = Query(False, description="Generate interactive map"),
    limit: int = Query(50, description="Limit number of boundaries returned", le=200),
    state_filter: Optional[str] = Query(None, description="Filter by specific state/province name")
):
    """Get India administrative boundaries from FAO GAUL dataset."""
    try:
        # Load FAO GAUL dataset
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        
        # Filter for India
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Apply state filter if provided
        if state_filter:
            india_boundaries = india_boundaries.filter(
                ee.Filter.stringContains('ADM1_NAME', state_filter)
            )
        
        total_count = india_boundaries.size().getInfo()
        
        if total_count == 0:
            return {
                "success": False,
                "message": f"No boundaries found for India" + (f" in state '{state_filter}'" if state_filter else ""),
                "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
            }
        
        # Limit results for performance
        limited_boundaries = india_boundaries.limit(limit)
        
        if not include_map:
            # Fast response - properties only
            boundary_list = limited_boundaries.getInfo()
            
            processed_boundaries = []
            for feature in boundary_list['features']:
                props = feature['properties']
                
                boundary_info = {
                    "country": props.get('ADM0_NAME', 'Unknown'),
                    "country_code": props.get('ADM0_CODE', 'Unknown'),
                    "state": props.get('ADM1_NAME', 'Unknown'),
                    "state_code": props.get('ADM1_CODE', 'Unknown'),
                    "district": props.get('ADM2_NAME', 'Unknown'),
                    "district_code": props.get('ADM2_CODE', 'Unknown'),
                    "status": props.get('STATUS', 'Unknown'),
                    "creation_year": props.get('STR2_YEAR', 'Unknown'),
                    "expiry_year": props.get('EXP2_YEAR', 'Unknown')
                }
                
                # Add the requested admin level as primary name
                if admin_level == "ADM0":
                    boundary_info["name"] = boundary_info["country"]
                elif admin_level == "ADM1":
                    boundary_info["name"] = boundary_info["state"]
                else:  # ADM2
                    boundary_info["name"] = boundary_info["district"]
                
                processed_boundaries.append(boundary_info)
            
            # Sort by name
            processed_boundaries.sort(key=lambda x: x["name"])
            
            return {
                "success": True,
                "admin_level": admin_level,
                "country": "India",
                "state_filter": state_filter,
                "total_available": total_count,
                "showing": len(processed_boundaries),
                "boundaries": processed_boundaries,
                "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
            }
        
        # Generate map
        map_result = await _generate_gaul_map(limited_boundaries, admin_level, state_filter)
        
        return {
            "success": True,
            "admin_level": admin_level,
            "country": "India", 
            "total_available": total_count,
            "showing": min(limit, total_count),
            "map_info": map_result,
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching boundaries: {str(e)}")

@app.get("/gaul-states")
async def get_gaul_states(
    include_map: bool = Query(False, description="Generate interactive map")
):
    """Get list of all Indian states/provinces from FAO GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Get unique states with their codes
        states_data = india_boundaries.select(['ADM1_NAME', 'ADM1_CODE']).distinct(['ADM1_NAME'])
        states_list = states_data.getInfo()
        
        states_info = []
        for feature in states_list['features']:
            props = feature['properties']
            states_info.append({
                "state_name": props['ADM1_NAME'],
                "state_code": props['ADM1_CODE']
            })
        
        # Sort alphabetically
        states_info.sort(key=lambda x: x['state_name'])
        
        response_data = {
            "success": True,
            "country": "India",
            "total_states": len(states_info),
            "states": states_info,
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
        }
        
        if include_map:
            # Create map with state boundaries
            state_boundaries = india_boundaries.distinct(['ADM1_NAME'])
            map_result = await _generate_gaul_map(state_boundaries, "ADM1", None)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching states: {str(e)}")

@app.get("/gaul-districts")
async def get_gaul_districts(
    state_name: Optional[str] = Query(None, description="Filter districts by state name"),
    limit: int = Query(100, description="Limit number of districts returned", le=500),
    include_map: bool = Query(False, description="Generate interactive map")
):
    """Get list of districts/municipalities from FAO GAUL dataset."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Filter by state if provided
        if state_name:
            india_boundaries = india_boundaries.filter(
                ee.Filter.stringContains('ADM1_NAME', state_name)
            )
        
        # Limit for performance
        limited_boundaries = india_boundaries.limit(limit)
        districts_list = limited_boundaries.getInfo()
        
        districts_info = []
        for feature in districts_list['features']:
            props = feature['properties']
            districts_info.append({
                "district_name": props.get('ADM2_NAME', 'Unknown'),
                "district_code": props.get('ADM2_CODE', 'Unknown'),
                "state_name": props.get('ADM1_NAME', 'Unknown'),
                "state_code": props.get('ADM1_CODE', 'Unknown'),
                "creation_year": props.get('STR2_YEAR', 'Unknown'),
                "status": props.get('STATUS', 'Unknown')
            })
        
        # Sort by district name
        districts_info.sort(key=lambda x: x['district_name'])
        
        response_data = {
            "success": True,
            "country": "India",
            "state_filter": state_name,
            "total_districts": len(districts_info),
            "districts": districts_info,
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
        }
        
        if include_map:
            map_result = await _generate_gaul_map(limited_boundaries, "ADM2", state_name)
            response_data["map_info"] = map_result
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching districts: {str(e)}")

@app.get("/gaul-state-districts/{state_name}")
async def get_districts_by_state(
    state_name: str,
    include_map: bool = Query(True, description="Generate interactive map for this state")
):
    """Get all districts within a specific Indian state."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        # Filter for specific state (case-insensitive)
        state_boundaries = india_boundaries.filter(
            ee.Filter.stringContains('ADM1_NAME', state_name)
        )
        
        districts_list = state_boundaries.getInfo()
        
        if not districts_list['features']:
            # Get available states for suggestion
            all_states = india_boundaries.select(['ADM1_NAME']).distinct(['ADM1_NAME']).getInfo()
            available_states = [f['properties']['ADM1_NAME'] for f in all_states['features']]
            raise HTTPException(
                status_code=404,
                detail=f"State '{state_name}' not found. Available states: {', '.join(sorted(available_states))}"
            )
        
        # Process districts data
        districts_info = []
        state_info = None
        
        for feature in districts_list['features']:
            props = feature['properties']
            
            # Get state info from first feature
            if not state_info:
                state_info = {
                    "state_name": props.get('ADM1_NAME', 'Unknown'),
                    "state_code": props.get('ADM1_CODE', 'Unknown'),
                    "country": props.get('ADM0_NAME', 'India')
                }
            
            districts_info.append({
                "district_name": props.get('ADM2_NAME', 'Unknown'),
                "district_code": props.get('ADM2_CODE', 'Unknown'),
                "creation_year": props.get('STR2_YEAR', 'Unknown'),
                "expiry_year": props.get('EXP2_YEAR', 'Unknown'),
                "status": props.get('STATUS', 'Unknown')
            })
        
        # Sort by district name
        districts_info.sort(key=lambda x: x['district_name'])
        
        response_data = {
            "success": True,
            "state_info": state_info,
            "total_districts": len(districts_info),
            "districts": districts_info,
            "dataset": "FAO/GAUL_SIMPLIFIED_500m/2015/level2"
        }
        
        if include_map:
            map_result = await _generate_gaul_map(state_boundaries, "ADM2", state_name)
            response_data["map_info"] = map_result
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching state districts: {str(e)}")

@app.get("/gaul-quick-search")
async def quick_search(
    search_term: str = Query(..., description="Search for state or district name"),
    search_level: str = Query("both", description="Search level: state, district, or both")
):
    """Quick search for states or districts by name."""
    try:
        gaul_boundaries = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2')
        india_boundaries = gaul_boundaries.filter(ee.Filter.eq('ADM0_NAME', 'India'))
        
        results = {
            "search_term": search_term,
            "states": [],
            "districts": []
        }
        
        # Search states
        if search_level in ["state", "both"]:
            state_matches = india_boundaries.filter(
                ee.Filter.stringContains('ADM1_NAME', search_term)
            ).select(['ADM1_NAME', 'ADM1_CODE']).distinct(['ADM1_NAME'])
            
            state_list = state_matches.getInfo()
            for feature in state_list['features']:
                props = feature['properties']
                results["states"].append({
                    "name": props['ADM1_NAME'],
                    "code": props['ADM1_CODE'],
                    "type": "state"
                })
        
        # Search districts
        if search_level in ["district", "both"]:
            district_matches = india_boundaries.filter(
                ee.Filter.stringContains('ADM2_NAME', search_term)
            ).limit(20)  # Limit for performance
            
            district_list = district_matches.getInfo()
            for feature in district_list['features']:
                props = feature['properties']
                results["districts"].append({
                    "name": props['ADM2_NAME'],
                    "code": props['ADM2_CODE'],
                    "state": props['ADM1_NAME'],
                    "type": "district"
                })
        
        return {
            "success": True,
            "search_results": results,
            "total_matches": len(results["states"]) + len(results["districts"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

async def _generate_gaul_map(
    boundaries_fc: ee.FeatureCollection,
    admin_level: str,
    focus_area: str = None
) -> Dict[str, Any]:
    """Generate interactive map with FAO GAUL boundaries."""
    try:
        # Create map
        m = geemap.Map()
        
        # Center on India or specific area
        if focus_area:
            m.center_object(boundaries_fc, zoom=7)
        else:
            m.set_center(78.9629, 20.5937, 5)  # India center
        
        # Style boundaries
        boundary_style = {
            'color': 'blue',
            'width': 1,
            'fillColor': '0000FF22'  # Light blue fill
        }
        
        # Add boundaries to map
        layer_name = f"India {admin_level} - FAO GAUL"
        if focus_area:
            layer_name += f" ({focus_area})"
        
        m.add_layer(boundaries_fc.style(**boundary_style), {}, layer_name)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gaul_{admin_level.lower()}"
        if focus_area:
            filename += f"_{focus_area.lower().replace(' ', '_')}"
        filename += f"_{timestamp}.html"
        
        # Save map
        m.to_html(filename=filename)
        
        return {
            "map_generated": True,
            "filename": filename,
            "admin_level": admin_level,
            "focus_area": focus_area or "India",
            "dataset": "FAO GAUL",
            "message": f"Map saved as {filename}"
        }
        
    except Exception as e:
        return {
            "map_generated": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)