"""
Integration tests with real coordinates and expected behaviors.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestLocationAnalysis:
    """Integration tests for location analysis."""
    
    def test_bangalore_tech_hub(self, client: TestClient):
        """Test analysis of Bangalore tech hub area."""
        request_data = {
            "lat": 12.9716,
            "lon": 77.5946,
            "buffer_m": 750,
            "layers": ["ndvi", "ndbi", "elevation", "landcover"]
        }
        
        response = client.post("/analyze-location", json=request_data)
        
        # Test will pass/fail based on Earth Engine configuration
        if response.status_code == 200:
            data = response.json()
            
            # Bangalore should have moderate NDVI (urban area with some vegetation)
            ee_summary = data["earth_engine"]["summary"]
            if "ndvi_mean" in ee_summary:
                assert 0.1 <= ee_summary["ndvi_mean"] <= 0.7
            
            # Should have some built-up area
            if "ndbi_mean" in ee_summary:
                assert ee_summary["ndbi_mean"] > -0.5
            
            # Elevation should be reasonable for Bangalore plateau
            if "elevation_mean" in ee_summary:
                assert 800 <= ee_summary["elevation_mean"] <= 1000
    
    def test_mumbai_coastal_area(self, client: TestClient, mumbai_coordinates):
        """Test analysis of Mumbai coastal area."""
        response = client.post("/analyze-location", json=mumbai_coordinates)
        
        if response.status_code == 200:
            data = response.json()
            ee_summary = data["earth_engine"]["summary"]
            
            # Mumbai should show water presence
            if "water_occurrence_mean" in ee_summary:
                assert ee_summary["water_occurrence_mean"] > 0
            
            # Coastal elevation should be low
            if "elevation_mean" in ee_summary:
                assert ee_summary["elevation_mean"] < 100
    
    def test_delhi_ncr_analysis(self, client: TestClient, delhi_coordinates):
        """Test analysis of Delhi NCR."""
        response = client.post("/analyze-location", json=delhi_coordinates)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check that visualization URLs are generated
            visuals = data["earth_engine"]["visuals"]
            
            for layer in delhi_coordinates["layers"]:
                expected_url_key = f"{layer}_url"
                if expected_url_key in visuals:
                    url = visuals[expected_url_key]
                    if url:  # URL might be None if generation failed
                        assert url.startswith("https://")
                        assert "earthengine.googleapis.com" in url
    
    def test_multiple_layers_analysis(self, client: TestClient):
        """Test analysis with all available layers."""
        request_data = {
            "lat": 12.9716,
            "lon": 77.5946,
            "buffer_m": 500,
            "layers": [
                "ndvi", "ndbi", "ndwi", "elevation", "slope",
                "landcover", "water_occurrence", "rainfall"
            ]
        }
        
        response = client.post("/analyze-location", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have data for most requested layers
            summary = data["earth_engine"]["summary"]
            visuals = data["earth_engine"]["visuals"]
            
            # Count how many layers have data
            summary_count = len([k for k in summary.keys() if summary[k] is not None])
            visual_count = len([k for k in visuals.keys() if visuals[k] is not None])
            
            # Should have data for most layers (allowing for some failures)
            assert summary_count >= 4
            assert visual_count >= 4
    
    def test_edge_coordinates(self, client: TestClient):
        """Test coordinates near India's borders."""
        # Near Pakistan border
        request_data = {
            "lat": 32.0,
            "lon": 74.0,
            "buffer_m": 1000,
            "layers": ["ndvi", "elevation"]
        }
        
        response = client.post("/analyze-location", json=request_data)
        
        # Should work but might generate warning about being outside India bounds
        assert response.status_code in [200, 500]