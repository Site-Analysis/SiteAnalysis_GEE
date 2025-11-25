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
            "landcover", "water_occurrence", "rainfall", "buildings", "administrative", "vegetation",
            "flood", "hydrology", "flood_risk", "llai"
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


# Administrative Boundary Models
class AdministrativeUnit(BaseModel):
    """Individual administrative unit information."""
    country: str = Field(..., description="Country name")
    state_province: str = Field(..., description="State or province name")
    district_county: str = Field(..., description="District or county name")
    country_code: Optional[str] = Field(None, description="Country code")
    state_code: Optional[str] = Field(None, description="State/province code")
    district_code: Optional[str] = Field(None, description="District/county code")
    area_within_roi_ha: float = Field(..., description="Area within region of interest in hectares")


class AdministrativeHierarchy(BaseModel):
    """Administrative hierarchy for the primary location."""
    country: str = Field(..., description="Primary country")
    state_province: str = Field(..., description="Primary state/province")
    district_county: str = Field(..., description="Primary district/county")
    full_path: str = Field(..., description="Full administrative path")


class AdministrativeSummary(BaseModel):
    """Summary of administrative boundaries analysis."""
    total_units: int = Field(..., description="Total administrative units found")
    countries_count: int = Field(0, description="Number of countries")
    states_count: int = Field(0, description="Number of states/provinces")
    districts_count: int = Field(0, description="Number of districts/counties")
    countries: List[str] = Field(default_factory=list, description="List of countries")
    states_provinces: List[str] = Field(default_factory=list, description="List of states/provinces")
    districts_counties: List[str] = Field(default_factory=list, description="List of districts/counties")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")


class AdministrativeData(BaseModel):
    """Complete administrative boundaries analysis results."""
    administrative_summary: AdministrativeSummary
    administrative_units: List[AdministrativeUnit] = Field(default_factory=list)
    administrative_hierarchy: Optional[AdministrativeHierarchy] = None
    admin_boundaries_url: Optional[str] = Field(None, description="Administrative boundaries visualization URL")



class EarthEngineData(BaseModel):
    """Earth Engine analysis results."""
    summary: EarthEngineSummary
    landcover_histogram: LandcoverHistogram
    visuals: EarthEngineVisuals
    roi: RoiInfo
    buildings: Optional[BuildingAnalysis] = Field(None, description="Building analysis results")
    administrative: Optional[AdministrativeData] = Field(None, description="Administrative boundaries analysis")
    vegetation: Optional[Dict[str, Any]] = Field(None, description="Comprehensive vegetation analysis results")
    flood_analysis: Optional[Dict[str, Any]] = Field(None, description="Comprehensive flood and hydrology analysis")


class FloodRiskScore(BaseModel):
    """Flood risk scoring model."""
    overall_score: float = Field(..., ge=0, le=100, description="Overall flood risk score (0-100)")
    risk_category: str = Field(..., description="Risk category: Very Low, Low, Moderate, High, Very High")
    risk_color: str = Field(..., description="Color code for risk visualization")
    elevation_risk: float = Field(..., description="Elevation component score")
    hydrology_risk: float = Field(..., description="Hydrology component score")
    historical_risk: float = Field(..., description="Historical flood component score")
    llai_risk: float = Field(..., description="Low-Lying Area Index component score")


class ElevationAnalysis(BaseModel):
    """Elevation and terrain analysis model."""
    mean_elevation_m: float = Field(..., description="Mean elevation in meters")
    min_elevation_m: float = Field(..., description="Minimum elevation in meters")
    max_elevation_m: float = Field(..., description="Maximum elevation in meters")
    elevation_range_m: float = Field(..., description="Elevation range in meters")
    elevation_std_dev: float = Field(..., description="Standard deviation of elevation")
    mean_slope_degrees: float = Field(..., description="Mean slope in degrees")
    max_slope_degrees: float = Field(..., description="Maximum slope in degrees")
    low_lying_area_percentage: float = Field(..., description="Percentage of low-lying area")
    terrain_classification: str = Field(..., description="Terrain type classification")
    data_source: str = Field(..., description="DEM data source used")


class HydrologyAnalysis(BaseModel):
    """Hydrology and drainage analysis model."""
    mean_flow_accumulation: float = Field(..., description="Mean flow accumulation value")
    max_flow_accumulation: float = Field(..., description="Maximum flow accumulation")
    high_flow_area_percentage: float = Field(..., description="Percentage with high flow accumulation")
    nearest_river_distance_m: float = Field(..., description="Distance to nearest river in meters")
    water_occurrence_percentage: float = Field(..., description="Historical water occurrence percentage")
    max_water_occurrence: float = Field(..., description="Maximum water occurrence")
    drainage_density: str = Field(..., description="Drainage density classification")
    river_proximity_risk: str = Field(..., description="Flood risk from river proximity")
    data_source: str = Field(..., description="Hydrology data sources")


class FloodHistory(BaseModel):
    """Historical flood analysis model."""
    historical_flood_events: int = Field(..., description="Number of recorded flood events")
    flooded_area_indicator: float = Field(..., description="Historical flooding indicator")
    water_recurrence_months: float = Field(..., description="Mean water recurrence in months")
    max_water_recurrence: float = Field(..., description="Maximum water recurrence")
    annual_rainfall_mm: float = Field(..., description="Annual rainfall in mm")
    max_daily_rainfall_mm: float = Field(..., description="Maximum daily rainfall in mm")
    mean_daily_rainfall_mm: float = Field(..., description="Mean daily rainfall in mm")
    flood_risk_category: str = Field(..., description="Historical flood risk category")
    flood_risk_score: float = Field(..., description="Historical flood risk score")
    data_source: str = Field(..., description="Flood history data sources")


class LowLyingAreaIndex(BaseModel):
    """Low-Lying Area Index (LLAI) model."""
    llai_mean: float = Field(..., description="Mean LLAI value (0-1)")
    llai_min: float = Field(..., description="Minimum LLAI value")
    llai_max: float = Field(..., description="Maximum LLAI value")
    llai_std_dev: float = Field(..., description="LLAI standard deviation")
    risk_distribution: Dict[str, float] = Field(..., description="Distribution across risk categories")
    primary_risk_category: str = Field(..., description="Primary risk category")
    data_source: str = Field(..., description="LLAI data sources")


class FloodAnalysis(BaseModel):
    """Comprehensive flood analysis model."""
    risk_score: FloodRiskScore = Field(..., description="Overall flood risk assessment")
    elevation: ElevationAnalysis = Field(..., description="Elevation and terrain analysis")
    hydrology: HydrologyAnalysis = Field(..., description="Hydrology and drainage analysis")
    flood_history: FloodHistory = Field(..., description="Historical flood analysis")
    llai: LowLyingAreaIndex = Field(..., description="Low-Lying Area Index analysis")
    recommendations: List[str] = Field(..., description="Flood mitigation recommendations")
    visualization_urls: Optional[Dict[str, str]] = Field(None, description="Visualization map URLs")


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