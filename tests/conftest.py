"""
Test configuration and fixtures for the GEE FastAPI Backend.
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def bangalore_coordinates():
    """Bangalore coordinates for testing."""
    return {
        "lat": 12.9716,
        "lon": 77.5946,
        "buffer_m": 750,
        "layers": ["ndvi", "elevation", "slope", "landcover"]
    }


@pytest.fixture
def delhi_coordinates():
    """Delhi coordinates for testing."""
    return {
        "lat": 28.6139,
        "lon": 77.2090,
        "buffer_m": 500,
        "layers": ["ndvi", "ndbi", "elevation"]
    }


@pytest.fixture
def mumbai_coordinates():
    """Mumbai coordinates for testing."""
    return {
        "lat": 19.0760,
        "lon": 72.8777,
        "buffer_m": 1000,
        "layers": ["ndvi", "ndwi", "water_occurrence"]
    }