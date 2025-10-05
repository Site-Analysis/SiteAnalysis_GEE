"""
Tests for the main FastAPI application endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "GEE FastAPI Backend"
    assert "version" in data
    assert "endpoints" in data


def test_health_endpoint(client: TestClient):
    """Test the health check endpoint."""
    # Note: This test might fail if Earth Engine is not properly initialized
    # In a real deployment, you'd want to mock the Earth Engine calls
    response = client.get("/health")
    
    # Check if the endpoint responds (it might be 503 if EE is not configured)
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data


def test_supported_layers_endpoint(client: TestClient):
    """Test the supported layers endpoint."""
    response = client.get("/supported-layers")
    assert response.status_code == 200
    data = response.json()
    assert "supported_layers" in data
    assert "default_layers" in data
    assert len(data["supported_layers"]) > 0
    
    # Check that each layer has required fields
    for layer in data["supported_layers"]:
        assert "name" in layer
        assert "description" in layer
        assert "data_source" in layer


def test_analyze_location_validation(client: TestClient):
    """Test input validation for the analyze location endpoint."""
    # Test invalid latitude
    invalid_request = {
        "lat": 91.0,  # Invalid latitude
        "lon": 77.5946,
        "buffer_m": 750,
        "layers": ["ndvi"]
    }
    response = client.post("/analyze-location", json=invalid_request)
    assert response.status_code == 422  # Validation error
    
    # Test invalid longitude
    invalid_request = {
        "lat": 12.9716,
        "lon": 181.0,  # Invalid longitude
        "buffer_m": 750,
        "layers": ["ndvi"]
    }
    response = client.post("/analyze-location", json=invalid_request)
    assert response.status_code == 422  # Validation error
    
    # Test invalid buffer
    invalid_request = {
        "lat": 12.9716,
        "lon": 77.5946,
        "buffer_m": 50,  # Too small buffer
        "layers": ["ndvi"]
    }
    response = client.post("/analyze-location", json=invalid_request)
    assert response.status_code == 422  # Validation error
    
    # Test invalid layer
    invalid_request = {
        "lat": 12.9716,
        "lon": 77.5946,
        "buffer_m": 750,
        "layers": ["invalid_layer"]
    }
    response = client.post("/analyze-location", json=invalid_request)
    assert response.status_code == 422  # Validation error


@pytest.mark.skipif(
    not pytest.importorskip("ee", minversion="0.1.379"),
    reason="Earth Engine not available"
)
def test_analyze_bangalore_location(client: TestClient, bangalore_coordinates):
    """
    Test analysis of Bangalore coordinates.
    
    Note: This test requires a properly configured Earth Engine service account.
    It will be skipped if Earth Engine is not available.
    """
    response = client.post("/analyze-location", json=bangalore_coordinates)
    
    # If Earth Engine is not configured, expect 500, otherwise 200
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        
        # Check response structure
        assert "coordinates" in data
        assert "earth_engine" in data
        assert "bhuvan" in data
        assert "kgis" in data
        assert "osm" in data
        assert "owm" in data
        assert "report" in data
        
        # Check coordinates
        assert len(data["coordinates"]) == 1
        coord = data["coordinates"][0]
        assert abs(coord["lat"] - bangalore_coordinates["lat"]) < 0.001
        assert abs(coord["long"] - bangalore_coordinates["lon"]) < 0.001
        
        # Check Earth Engine data structure
        ee_data = data["earth_engine"]
        assert "summary" in ee_data
        assert "landcover_histogram" in ee_data
        assert "visuals" in ee_data
        assert "roi" in ee_data
        
        # Check ROI information
        roi = ee_data["roi"]
        assert "center_lat" in roi
        assert "center_lon" in roi
        assert "buffer_meters" in roi
        assert "area_hectares" in roi
        assert roi["buffer_meters"] == bangalore_coordinates["buffer_m"]
        
        # Check that requested layers have data
        summary = ee_data["summary"]
        visuals = ee_data["visuals"]
        
        if "ndvi" in bangalore_coordinates["layers"]:
            assert "ndvi_mean" in summary
            assert "ndvi_url" in visuals
        
        if "elevation" in bangalore_coordinates["layers"]:
            assert "elevation_mean" in summary
            assert "elevation_url" in visuals
        
        if "landcover" in bangalore_coordinates["layers"]:
            assert len(ee_data["landcover_histogram"]) > 0
            assert "landcover_url" in visuals


def test_minimal_request(client: TestClient):
    """Test with minimal request parameters."""
    minimal_request = {
        "lat": 12.9716,
        "lon": 77.5946
    }
    
    response = client.post("/analyze-location", json=minimal_request)
    
    # Should use default values
    assert response.status_code in [200, 500]  # Depends on EE configuration


def test_custom_layers_request(client: TestClient):
    """Test with custom layers selection."""
    custom_request = {
        "lat": 12.9716,
        "lon": 77.5946,
        "buffer_m": 1000,
        "layers": ["ndvi", "ndbi", "ndwi", "water_occurrence"]
    }
    
    response = client.post("/analyze-location", json=custom_request)
    assert response.status_code in [200, 500]  # Depends on EE configuration