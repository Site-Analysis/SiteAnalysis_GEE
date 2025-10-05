"""
Pydantic models for request/response schemas.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class Coordinates(BaseModel):
    """Coordinates model for lat/lon pairs."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    long: float = Field(..., ge=-180, le=180, description="Longitude")


class LocationRequest(BaseModel):
    """Request model for location analysis."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    buffer_m: int = Field(default=750, ge=100, le=5000, description="Buffer radius in meters")
    layers: List[str] = Field(
        default=["ndvi", "elevation", "slope", "landcover"],
        description="List of layers to analyze"
    )
    
    @validator('layers')
    def validate_layers(cls, v):
        """Validate that requested layers are supported."""
        supported_layers = [
            "ndvi", "ndbi", "ndwi", "elevation", "slope", 
            "landcover", "water_occurrence", "rainfall", "buildings"
        ]
        for layer in v:
            if layer not in supported_layers:
                raise ValueError(f"Unsupported layer: {layer}. Supported layers: {supported_layers}")
        return v


# Response model structures
class BhuvanData(BaseModel):
    """Placeholder for Bhuvan data integration."""
    pass


class KgisData(BaseModel):
    """Placeholder for KGIS data integration."""
    pass


class OsmData(BaseModel):
    """Placeholder for OpenStreetMap data integration."""
    pass


class OwmData(BaseModel):
    """Placeholder for OpenWeatherMap data integration."""
    pass


class EarthEngineSummary(BaseModel):
    """Summary statistics from Earth Engine analysis."""
    ndvi_mean: Optional[float] = None
    ndvi_std: Optional[float] = None
    ndvi_min: Optional[float] = None
    ndvi_max: Optional[float] = None
    
    ndbi_mean: Optional[float] = None
    ndbi_std: Optional[float] = None
    
    ndwi_mean: Optional[float] = None
    ndwi_std: Optional[float] = None
    
    elevation_mean: Optional[float] = None
    elevation_std: Optional[float] = None
    elevation_min: Optional[float] = None
    elevation_max: Optional[float] = None
    
    slope_mean: Optional[float] = None
    slope_std: Optional[float] = None
    
    water_occurrence_mean: Optional[float] = None
    rainfall_annual_mean: Optional[float] = None


class LandcoverHistogram(BaseModel):
    """Histogram of land cover types."""
    tree_cover: Optional[float] = Field(None, description="Percentage of tree cover")
    shrubland: Optional[float] = Field(None, description="Percentage of shrubland")
    grassland: Optional[float] = Field(None, description="Percentage of grassland")
    cropland: Optional[float] = Field(None, description="Percentage of cropland")
    built_up: Optional[float] = Field(None, description="Percentage of built-up area")
    bare_sparse_vegetation: Optional[float] = Field(None, description="Percentage of bare/sparse vegetation")
    snow_ice: Optional[float] = Field(None, description="Percentage of snow/ice")
    permanent_water_bodies: Optional[float] = Field(None, description="Percentage of permanent water bodies")
    herbaceous_wetland: Optional[float] = Field(None, description="Percentage of herbaceous wetland")
    mangroves: Optional[float] = Field(None, description="Percentage of mangroves")
    moss_lichen: Optional[float] = Field(None, description="Percentage of moss/lichen")


class EarthEngineVisuals(BaseModel):
    """URLs for Earth Engine visualization images."""
    ndvi_url: Optional[str] = None
    ndbi_url: Optional[str] = None
    ndwi_url: Optional[str] = None
    elevation_url: Optional[str] = None
    slope_url: Optional[str] = None
    landcover_url: Optional[str] = None
    water_occurrence_url: Optional[str] = None
    rainfall_url: Optional[str] = None
    true_color_url: Optional[str] = None


# Building Analysis Models
class IndividualBuilding(BaseModel):
    """Individual building analysis results."""
    building_id: Optional[str] = Field(None, description="Unique building identifier")
    area_sqm: float = Field(..., description="Building area in square meters")
    perimeter_m: float = Field(..., description="Building perimeter in meters")
    centroid_lon: float = Field(..., description="Building centroid longitude")
    centroid_lat: float = Field(..., description="Building centroid latitude")
    confidence: float = Field(..., description="Building detection confidence (0-1)")
    surrounding_ndvi_mean: float = Field(..., description="Average NDVI around building")
    surrounding_ndvi_std: float = Field(..., description="NDVI standard deviation around building")
    elevation_mean: float = Field(..., description="Average elevation of building")
    elevation_min: float = Field(..., description="Minimum elevation of building")
    elevation_max: float = Field(..., description="Maximum elevation of building")
    dominant_landcover: int = Field(..., description="Dominant land cover class within building")


class BuildingSummary(BaseModel):
    """Summary statistics for buildings in the area."""
    total_buildings: int = Field(..., description="Total number of buildings detected")
    analyzed_buildings: int = Field(..., description="Number of buildings analyzed in detail")
    total_building_area_sqm: float = Field(..., description="Total area covered by buildings")
    average_building_area_sqm: float = Field(..., description="Average building size")
    max_building_area_sqm: float = Field(..., description="Largest building size")
    min_building_area_sqm: float = Field(..., description="Smallest building size")


class UrbanContext(BaseModel):
    """Urban context analysis around buildings."""
    nighttime_lights_mean: float = Field(..., description="Average nighttime light intensity")
    population_density_mean: float = Field(..., description="Average population density per pixel")
    land_surface_temp_mean: float = Field(..., description="Average land surface temperature (°C)")
    urban_heat_island_intensity: float = Field(..., description="Urban heat island effect intensity")


class BuildingVisuals(BaseModel):
    """Visualization URLs for building analysis."""
    buildings_url: Optional[str] = Field(None, description="Building polygon outlines")
    nightlights_url: Optional[str] = Field(None, description="Nighttime lights visualization")
    population_url: Optional[str] = Field(None, description="Population density visualization")
    urban_heat_url: Optional[str] = Field(None, description="Urban heat island visualization")


class BuildingAnalysis(BaseModel):
    """Complete building analysis results."""
    building_summary: BuildingSummary
    urban_context: UrbanContext
    individual_buildings: List[IndividualBuilding]
    visualization_urls: BuildingVisuals


class RoiInfo(BaseModel):
    """Region of Interest information."""
    center_lat: float
    center_lon: float
    buffer_meters: int
    area_hectares: float
    perimeter_meters: float


class EarthEngineData(BaseModel):
    """Earth Engine analysis results."""
    summary: EarthEngineSummary
    landcover_histogram: LandcoverHistogram
    visuals: EarthEngineVisuals
    roi: RoiInfo
    buildings: Optional[BuildingAnalysis] = Field(None, description="Building analysis results")


class ReportSection(BaseModel):
    """Generic report section."""
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None


class Report(BaseModel):
    """Analysis report structure."""
    section_1: Optional[ReportSection] = None
    section_2: Optional[ReportSection] = None
    section_3: Optional[ReportSection] = None


class LocationResponse(BaseModel):
    """Complete response model for location analysis."""
    coordinates: List[Coordinates]
    bhuvan: BhuvanData = BhuvanData()
    kgis: KgisData = KgisData()
    osm: OsmData = OsmData()
    owm: OwmData = OwmData()
    earth_engine: EarthEngineData
    report: Report = Report()


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


# Type aliases for backward compatibility
LocationAnalysisRequest = LocationRequest
LocationAnalysisResponse = LocationResponse