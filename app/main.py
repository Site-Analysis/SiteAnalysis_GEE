"""
FastAPI application for Google Earth Engine geospatial analysis.
India-focused backend service for location-based analysis.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime

from .config import config, initialize_earth_engine
from .models import (
    LocationRequest, LocationResponse, ErrorResponse,
    Coordinates, EarthEngineData, EarthEngineSummary,
    LandcoverHistogram, EarthEngineVisuals, RoiInfo
)
from .gee_utils import analyze_location
from .pdf_generator import PDFReportGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    print("🚀 Starting GEE FastAPI Backend...")
    try:
        initialize_earth_engine()
        print("✅ Application startup completed successfully")
    except Exception as e:
        print(f"❌ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down GEE FastAPI Backend...")


# Create FastAPI application
app = FastAPI(
    title=config.PROJECT_NAME,
    version=config.VERSION,
    description=config.DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint returning basic API information."""
    return {
        "message": "GEE FastAPI Backend",
        "version": config.VERSION,
        "description": config.DESCRIPTION,
        "status": "active",
        "endpoints": {
            "analyze_location": "/analyze-location",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Test Earth Engine connectivity
        import ee
        test_image = ee.Image("COPERNICUS/S2_SR/20230101T061241_20230101T061238_T43PGQ")
        image_id = test_image.get('system:id').getInfo()
        
        return {
            "status": "healthy",
            "earth_engine": "connected",
            "test_image_id": image_id,
            "timestamp": "2024-10-02T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Earth Engine connection failed: {str(e)}"
        )


@app.post("/analyze-location", response_model=LocationResponse, tags=["Analysis"])
async def analyze_location_endpoint(request: LocationRequest):
    """
    Analyze a geographic location using Google Earth Engine.
    
    This endpoint takes latitude, longitude coordinates and performs comprehensive
    geospatial analysis including vegetation indices, elevation, land cover, and
    other environmental indicators.
    
    Args:
        request: LocationRequest containing lat, lon, buffer_m, and layers
        
    Returns:
        LocationResponse: Complete analysis results with statistics and visualization URLs
        
    Raises:
        HTTPException: If analysis fails or coordinates are invalid
    """
    try:
        # Validate coordinates are within reasonable bounds for India
        if not (6.0 <= request.lat <= 37.0 and 68.0 <= request.lon <= 97.0):
            print(f"⚠️  Warning: Coordinates ({request.lat}, {request.lon}) are outside India bounds")
        
        print(f"🌍 Analyzing location: ({request.lat}, {request.lon}) with {request.buffer_m}m buffer")
        print(f"📊 Requested layers: {request.layers}")
        
        # Perform Earth Engine analysis
        gee_results = analyze_location(
            lat=request.lat,
            lon=request.lon,
            buffer_m=request.buffer_m,
            layers=request.layers
        )
        
        # Transform results into response model
        earth_engine_data = EarthEngineData(
            summary=EarthEngineSummary(**gee_results['summary']),
            landcover_histogram=LandcoverHistogram(**gee_results['landcover_histogram']),
            visuals=EarthEngineVisuals(**gee_results['visuals']),
            roi=RoiInfo(**gee_results['roi']),
            buildings=gee_results.get('buildings'),  # Add buildings data
            administrative=gee_results.get('administrative'),  # Add administrative data
            vegetation=gee_results.get('vegetation'),  # Add vegetation data
            flood_analysis=gee_results.get('flood')  # Add flood analysis data
        )
        
        # Create complete response
        response = LocationResponse(
            coordinates=[Coordinates(lat=request.lat, long=request.lon)],
            earth_engine=earth_engine_data
        )
        
        print(f"✅ Analysis completed successfully")
        return response
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        error_detail = f"Failed to analyze location ({request.lat}, {request.lon}): {str(e)}"
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.get("/supported-layers", tags=["Information"])
async def get_supported_layers():
    """Get list of supported analysis layers."""
    return {
        "supported_layers": [
            {
                "name": "ndvi",
                "description": "Normalized Difference Vegetation Index",
                "data_source": "Sentinel-2"
            },
            {
                "name": "ndbi",
                "description": "Normalized Difference Built-up Index",
                "data_source": "Sentinel-2"
            },
            {
                "name": "ndwi",
                "description": "Normalized Difference Water Index",
                "data_source": "Sentinel-2"
            },
            {
                "name": "elevation",
                "description": "Digital Elevation Model",
                "data_source": "SRTM GL1"
            },
            {
                "name": "slope",
                "description": "Terrain slope derived from elevation",
                "data_source": "SRTM GL1"
            },
            {
                "name": "landcover",
                "description": "Land cover classification",
                "data_source": "ESA WorldCover"
            },
            {
                "name": "water_occurrence",
                "description": "Surface water occurrence frequency",
                "data_source": "JRC Global Surface Water"
            },
            {
                "name": "rainfall",
                "description": "Annual precipitation",
                "data_source": "CHIRPS"
            },
            {
                "name": "buildings",
                "description": "Individual building analysis and urban context",
                "data_source": "Google Research Open Buildings v3"
            },
            {
                "name": "administrative",
                "description": "Administrative boundaries (countries, states, districts)",
                "data_source": "FAO GAUL Administrative Boundaries"
            },
            {
                "name": "vegetation",
                "description": "Comprehensive vegetation analysis with NDVI, EVI, SAVI indices and health metrics",
                "data_source": "Sentinel-2 + MODIS"
            },
            {
                "name": "flood",
                "description": "Comprehensive flood risk assessment with elevation, hydrology, and historical analysis",
                "data_source": "MERIT DEM, ALOS, Cloud-to-Street, JRC GSW, CHIRPS"
            },
            {
                "name": "hydrology",
                "description": "Hydrological analysis including flow accumulation, rivers, and drainage patterns",
                "data_source": "MERIT Hydro, HydroSHEDS, JRC Global Surface Water"
            },
            {
                "name": "flood_risk",
                "description": "Flood risk scoring with elevation, hydrology, historical events, and LLAI components",
                "data_source": "Multi-source composite analysis"
            },
            {
                "name": "llai",
                "description": "Low-Lying Area Index measuring flood susceptibility from terrain characteristics",
                "data_source": "MERIT DEM derived analysis"
            }
        ],
        "default_layers": ["ndvi", "elevation", "slope", "landcover"]
    }


@app.post("/analyze-polygon", tags=["Analysis"])
async def analyze_polygon_endpoint(request: dict):
    """
    Analyze a specific polygon area for building analysis.
    
    This endpoint takes polygon geometry and performs building analysis
    on the exact area defined by the polygon boundaries.
    
    Args:
        request: Dictionary containing geometry (GeoJSON Feature) and layer type
        
    Returns:
        Dict: Analysis results for the polygon area
    """
    try:
        print(f"🏢 Polygon building analysis requested")
        
        # Extract geometry and layer
        geometry_data = request.get('geometry')
        layer = request.get('layer', 'buildings')
        
        if not geometry_data:
            raise HTTPException(status_code=400, detail="No geometry provided")
        
        print(f"📐 Received geometry: {geometry_data.get('type')} with layer: {layer}")
        
        # Convert GeoJSON to Earth Engine geometry
        if geometry_data.get('type') == 'Feature':
            coordinates = geometry_data['geometry']['coordinates']
            geom_type = geometry_data['geometry']['type']
        else:
            coordinates = geometry_data['coordinates']
            geom_type = geometry_data['type']
        
        if geom_type == 'Polygon':
            import ee
            roi = ee.Geometry.Polygon(coordinates)
            print(f"✅ Created EE Polygon geometry")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported geometry type: {geom_type}")
        
        # Perform analysis on the exact polygon
        if layer == 'buildings':
            from .gee_utils import get_sentinel2_composite, analyze_buildings_in_area
            
            print("🔍 Analyzing buildings within polygon boundaries...")
            
            # Get basic composites for building context
            s2_composite = get_sentinel2_composite(roi, '2023-01-01', '2024-01-01')
            
            # Analyze buildings in the exact polygon area
            building_analysis = analyze_buildings_in_area(roi, s2_composite, max_buildings=50)
            
            # Calculate polygon area for reference
            polygon_area_hectares = roi.area().getInfo() / 10000
            
            return {
                "status": "success",
                "analysis_type": "polygon_buildings",
                "message": "Building analysis completed for polygon area",
                "polygon_area_hectares": round(polygon_area_hectares, 2),
                "earth_engine": {
                    "buildings": building_analysis,
                    "summary": {
                        "ndvi_mean": 0.3,  # Default values for polygon analysis
                        "elevation_mean": 100,
                        "slope_mean": 0
                    },
                    "landcover_histogram": {
                        "built_up": 80.0,  # Default estimate for building areas
                        "grassland": 10.0,
                        "tree_cover": 10.0
                    },
                    "visuals": {
                        "true_color_url": None,
                        "ndvi_url": None,
                        "elevation_url": None,
                        "landcover_url": None
                    },
                    "roi": {
                        "area_hectares": round(polygon_area_hectares, 2),
                        "center_lat": roi.centroid().coordinates().getInfo()[1],
                        "center_lon": roi.centroid().coordinates().getInfo()[0], 
                        "buffer_meters": 0,
                        "perimeter_meters": round(roi.perimeter().getInfo(), 2),
                        "analysis_type": "polygon"
                    }
                }
            }
        
        elif layer == 'administrative':
            from .gee_utils import analyze_administrative_boundaries, get_administrative_visualization
            
            print("🏛️ Analyzing administrative boundaries within polygon...")
            
            # Analyze administrative boundaries in the exact polygon area
            admin_analysis = analyze_administrative_boundaries(roi)
            
            # Add visualization URL for polygon-clipped boundaries
            admin_analysis['admin_boundaries_url'] = get_administrative_visualization(roi)
            
            # Calculate polygon area for reference
            polygon_area_hectares = roi.area().getInfo() / 10000
            
            return {
                "status": "success",
                "analysis_type": "polygon_administrative",
                "message": "Administrative boundaries analysis completed for polygon area",
                "polygon_area_hectares": round(polygon_area_hectares, 2),
                "earth_engine": {
                    "administrative": admin_analysis,
                    "summary": {
                        "ndvi_mean": 0.3,  # Default values for polygon analysis
                        "elevation_mean": 100,
                        "slope_mean": 0
                    },
                    "landcover_histogram": {
                        "built_up": 50.0,  # Default estimate
                        "grassland": 25.0,
                        "tree_cover": 25.0
                    },
                    "visuals": {
                        "true_color_url": None,
                        "ndvi_url": None,
                        "elevation_url": None,
                        "landcover_url": None
                    },
                    "roi": {
                        "area_hectares": round(polygon_area_hectares, 2),
                        "center_lat": roi.centroid().coordinates().getInfo()[1],
                        "center_lon": roi.centroid().coordinates().getInfo()[0], 
                        "buffer_meters": 0,
                        "perimeter_meters": round(roi.perimeter().getInfo(), 2),
                        "analysis_type": "polygon"
                    }
                }
            }
        
        elif layer == 'vegetation':
            from .gee_utils import analyze_viirs_vegetation, get_viirs_visualization_urls
            
            print("🌱 Analyzing VIIRS vegetation within polygon...")
            
            # Analyze VIIRS vegetation in the exact polygon area
            vegetation_analysis = analyze_viirs_vegetation(roi)
            
            # Add VIIRS visualization URLs for polygon-clipped area
            viirs_vis_urls = get_viirs_visualization_urls(roi)
            vegetation_analysis.update(viirs_vis_urls)
            
            # Calculate polygon area for reference
            polygon_area_hectares = roi.area().getInfo() / 10000
            
            return {
                "status": "success",
                "analysis_type": "polygon_vegetation",
                "message": "VIIRS vegetation analysis completed for polygon area",
                "polygon_area_hectares": round(polygon_area_hectares, 2),
                "earth_engine": {
                    "vegetation": vegetation_analysis,
                    "summary": {
                        "ndvi_mean": vegetation_analysis.get('viirs_ndvi_mean', 0.3),
                        "elevation_mean": 100,  # Default values
                        "slope_mean": 0
                    },
                    "landcover_histogram": {
                        "tree_cover": vegetation_analysis.get('vegetation_distribution', {}).get('dense_vegetation', 25.0),
                        "grassland": vegetation_analysis.get('vegetation_distribution', {}).get('moderate_vegetation', 25.0),
                        "shrubland": vegetation_analysis.get('vegetation_distribution', {}).get('low_vegetation', 25.0),
                        "bare_sparse_vegetation": vegetation_analysis.get('vegetation_distribution', {}).get('non_vegetated', 25.0)
                    },
                    "visuals": {
                        "true_color_url": None,
                        "ndvi_url": vegetation_analysis.get('viirs_ndvi_url'),
                        "elevation_url": None,
                        "landcover_url": None
                    },
                    "roi": {
                        "area_hectares": round(polygon_area_hectares, 2),
                        "center_lat": roi.centroid().coordinates().getInfo()[1],
                        "center_lon": roi.centroid().coordinates().getInfo()[0], 
                        "buffer_meters": 0,
                        "perimeter_meters": round(roi.perimeter().getInfo(), 2),
                        "analysis_type": "polygon"
                    }
                }
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Analysis type '{layer}' not yet supported for polygons. Supported: buildings, administrative, vegetation")
    
    except Exception as e:
        print(f"❌ Error in polygon analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Polygon analysis failed: {str(e)}"
        )


@app.post("/generate-report")
async def generate_report(request: dict):
    """
    Generate a comprehensive PDF report for the analysis results.
    
    Args:
        request: Complete analysis data including all layers
        
    Returns:
        StreamingResponse: PDF file for download
    """
    try:
        print(f"📄 Generating PDF report...")
        print(f"📊 Request data keys: {list(request.keys())}")
        print(f"📊 Latitude: {request.get('latitude')}")
        print(f"📊 Longitude: {request.get('longitude')}")
        print(f"📊 Vegetation data: {request.get('vegetation', 'None')}")
        print(f"📊 Buildings data: {request.get('buildings', 'None')}")
        print(f"📊 Administrative data: {request.get('administrative', 'None')}")
        
        # Add analysis date if not present
        if 'analysis_date' not in request:
            request['analysis_date'] = datetime.now().strftime('%B %d, %Y')
        
        # Initialize PDF generator
        pdf_gen = PDFReportGenerator()
        
        # Generate PDF
        pdf_buffer = pdf_gen.generate_report(request)
        
        # Create filename
        location_str = f"{request.get('latitude', 'unknown')}_{request.get('longitude', 'unknown')}"
        filename = f"GEE_Analysis_Report_{location_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        print(f"✅ PDF report generated successfully: {filename}")
        
        # Return PDF as streaming response
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except Exception as e:
        print(f"❌ Error generating PDF report: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors."""
    print(f"❌ Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            error_code="INTERNAL_ERROR"
        ).dict()
    )


if __name__ == "__main__":
    # For development only
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )