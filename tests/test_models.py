"""
Tests for Pydantic models and data validation.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    LocationRequest, LocationResponse, Coordinates,
    EarthEngineSummary, LandcoverHistogram, EarthEngineVisuals,
    RoiInfo, EarthEngineData
)


class TestLocationRequest:
    """Test LocationRequest model validation."""
    
    def test_valid_request(self):
        """Test valid location request."""
        request = LocationRequest(
            lat=12.9716,
            lon=77.5946,
            buffer_m=750,
            layers=["ndvi", "elevation"]
        )
        
        assert request.lat == 12.9716
        assert request.lon == 77.5946
        assert request.buffer_m == 750
        assert request.layers == ["ndvi", "elevation"]
    
    def test_default_values(self):
        """Test default values for optional fields."""
        request = LocationRequest(lat=12.9716, lon=77.5946)
        
        assert request.buffer_m == 750  # Default value
        assert "ndvi" in request.layers  # Default layers
        assert "elevation" in request.layers
    
    def test_invalid_latitude(self):
        """Test validation of invalid latitude."""
        with pytest.raises(ValidationError):
            LocationRequest(lat=91.0, lon=77.5946)
        
        with pytest.raises(ValidationError):
            LocationRequest(lat=-91.0, lon=77.5946)
    
    def test_invalid_longitude(self):
        """Test validation of invalid longitude."""
        with pytest.raises(ValidationError):
            LocationRequest(lat=12.9716, lon=181.0)
        
        with pytest.raises(ValidationError):
            LocationRequest(lat=12.9716, lon=-181.0)
    
    def test_invalid_buffer(self):
        """Test validation of invalid buffer size."""
        with pytest.raises(ValidationError):
            LocationRequest(lat=12.9716, lon=77.5946, buffer_m=50)  # Too small
        
        with pytest.raises(ValidationError):
            LocationRequest(lat=12.9716, lon=77.5946, buffer_m=10000)  # Too large
    
    def test_invalid_layers(self):
        """Test validation of invalid layers."""
        with pytest.raises(ValidationError):
            LocationRequest(
                lat=12.9716,
                lon=77.5946,
                layers=["invalid_layer"]
            )
        
        with pytest.raises(ValidationError):
            LocationRequest(
                lat=12.9716,
                lon=77.5946,
                layers=["ndvi", "invalid_layer", "elevation"]
            )
    
    def test_valid_layers(self):
        """Test all valid layer combinations."""
        valid_layers = [
            "ndvi", "ndbi", "ndwi", "elevation", "slope",
            "landcover", "water_occurrence", "rainfall"
        ]
        
        # Test individual layers
        for layer in valid_layers:
            request = LocationRequest(
                lat=12.9716,
                lon=77.5946,
                layers=[layer]
            )
            assert layer in request.layers
        
        # Test all layers together
        request = LocationRequest(
            lat=12.9716,
            lon=77.5946,
            layers=valid_layers
        )
        assert len(request.layers) == len(valid_layers)


class TestCoordinates:
    """Test Coordinates model."""
    
    def test_valid_coordinates(self):
        """Test valid coordinate creation."""
        coord = Coordinates(lat=12.9716, long=77.5946)
        assert coord.lat == 12.9716
        assert coord.long == 77.5946
    
    def test_coordinate_bounds(self):
        """Test coordinate boundary validation."""
        # Valid edge cases
        Coordinates(lat=90.0, long=180.0)
        Coordinates(lat=-90.0, long=-180.0)
        
        # Invalid cases
        with pytest.raises(ValidationError):
            Coordinates(lat=91.0, long=0.0)
        
        with pytest.raises(ValidationError):
            Coordinates(lat=0.0, long=181.0)


class TestEarthEngineSummary:
    """Test EarthEngineSummary model."""
    
    def test_optional_fields(self):
        """Test that all fields are optional."""
        summary = EarthEngineSummary()
        assert summary.ndvi_mean is None
        assert summary.elevation_mean is None
    
    def test_with_data(self):
        """Test summary with actual data."""
        summary = EarthEngineSummary(
            ndvi_mean=0.456,
            ndvi_std=0.123,
            elevation_mean=920.5,
            elevation_std=45.2
        )
        
        assert summary.ndvi_mean == 0.456
        assert summary.ndvi_std == 0.123
        assert summary.elevation_mean == 920.5
        assert summary.elevation_std == 45.2


class TestLandcoverHistogram:
    """Test LandcoverHistogram model."""
    
    def test_empty_histogram(self):
        """Test empty histogram."""
        histogram = LandcoverHistogram()
        assert histogram.tree_cover is None
        assert histogram.built_up is None
    
    def test_with_percentages(self):
        """Test histogram with percentage data."""
        histogram = LandcoverHistogram(
            tree_cover=25.5,
            built_up=45.2,
            cropland=20.1,
            grassland=9.2
        )
        
        assert histogram.tree_cover == 25.5
        assert histogram.built_up == 45.2
        assert histogram.cropland == 20.1
        assert histogram.grassland == 9.2


class TestEarthEngineVisuals:
    """Test EarthEngineVisuals model."""
    
    def test_empty_visuals(self):
        """Test empty visuals."""
        visuals = EarthEngineVisuals()
        assert visuals.ndvi_url is None
        assert visuals.elevation_url is None
    
    def test_with_urls(self):
        """Test visuals with URLs."""
        visuals = EarthEngineVisuals(
            ndvi_url="https://earthengine.googleapis.com/v1/projects/test/thumbnails/abc123",
            elevation_url="https://earthengine.googleapis.com/v1/projects/test/thumbnails/def456"
        )
        
        assert "earthengine.googleapis.com" in visuals.ndvi_url
        assert "earthengine.googleapis.com" in visuals.elevation_url


class TestRoiInfo:
    """Test RoiInfo model."""
    
    def test_roi_creation(self):
        """Test ROI info creation."""
        roi = RoiInfo(
            center_lat=12.9716,
            center_lon=77.5946,
            buffer_meters=750,
            area_hectares=17.67,
            perimeter_meters=942.48
        )
        
        assert roi.center_lat == 12.9716
        assert roi.center_lon == 77.5946
        assert roi.buffer_meters == 750
        assert roi.area_hectares == 17.67
        assert roi.perimeter_meters == 942.48


class TestCompleteResponse:
    """Test complete LocationResponse model."""
    
    def test_minimal_response(self):
        """Test response with minimal required data."""
        earth_engine_data = EarthEngineData(
            summary=EarthEngineSummary(),
            landcover_histogram=LandcoverHistogram(),
            visuals=EarthEngineVisuals(),
            roi=RoiInfo(
                center_lat=12.9716,
                center_lon=77.5946,
                buffer_meters=750,
                area_hectares=17.67,
                perimeter_meters=942.48
            )
        )
        
        response = LocationResponse(
            coordinates=[Coordinates(lat=12.9716, long=77.5946)],
            earth_engine=earth_engine_data
        )
        
        assert len(response.coordinates) == 1
        assert response.coordinates[0].lat == 12.9716
        assert response.earth_engine.roi.center_lat == 12.9716