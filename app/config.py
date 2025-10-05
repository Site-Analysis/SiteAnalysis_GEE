"""
Configuration module for Google Earth Engine FastAPI application.
Handles environment variables and service account authentication.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import ee
from google.oauth2 import service_account
import json

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the application."""
    
    # Google Earth Engine Service Account Configuration
    GEE_SERVICE_ACCOUNT_EMAIL: str = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", "")
    GEE_SERVICE_ACCOUNT_KEY_PATH: str = os.getenv(
        "GEE_SERVICE_ACCOUNT_KEY_PATH", 
        "gee-sa.json"
    )
    
    # Alternatively, use service account key as JSON string (for deployment)
    GEE_SERVICE_ACCOUNT_KEY_JSON: Optional[str] = os.getenv("GEE_SERVICE_ACCOUNT_KEY_JSON")
    
    # Application settings
    PROJECT_NAME: str = "GEE FastAPI Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Backend service for India-focused geospatial analysis using Google Earth Engine"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # Default buffer for analysis (meters)
    DEFAULT_BUFFER_M: int = 750
    
    # India bounding box for data filtering
    INDIA_BOUNDS = [68.0, 6.0, 97.0, 37.0]  # [west, south, east, north]


def get_gee_credentials():
    """
    Get Google Earth Engine credentials from service account.
    
    Returns:
        google.oauth2.service_account.Credentials: GEE credentials
    """
    if Config.GEE_SERVICE_ACCOUNT_KEY_JSON:
        # Use JSON string from environment variable (for deployment)
        try:
            key_data = json.loads(Config.GEE_SERVICE_ACCOUNT_KEY_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                key_data,
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            return credentials
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GEE_SERVICE_ACCOUNT_KEY_JSON: {e}")
    
    elif os.path.exists(Config.GEE_SERVICE_ACCOUNT_KEY_PATH):
        # Use JSON file path
        credentials = service_account.Credentials.from_service_account_file(
            Config.GEE_SERVICE_ACCOUNT_KEY_PATH,
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        return credentials
    
    else:
        raise FileNotFoundError(
            f"Service account key file not found at: {Config.GEE_SERVICE_ACCOUNT_KEY_PATH}. "
            "Please ensure the file exists or set GEE_SERVICE_ACCOUNT_KEY_JSON environment variable."
        )


def initialize_earth_engine():
    """
    Initialize Google Earth Engine with service account credentials.
    
    Raises:
        Exception: If initialization fails
    """
    try:
        credentials = get_gee_credentials()
        ee.Initialize(credentials)
        print("✅ Google Earth Engine initialized successfully")
        
        # Test the connection with a known dataset
        test_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").limit(1)
        test_size = test_collection.size()
        print(f"✅ GEE connection test successful. Can access Sentinel-2 Harmonized collection.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to initialize Google Earth Engine: {error_msg}")
        
        if "not registered to use Earth Engine" in error_msg:
            print("🔧 SOLUTION: Register your project with Earth Engine:")
            print("   1. Visit: https://code.earthengine.google.com/register")
            print("   2. Sign in and complete the registration form")
            print("   3. Wait for approval (usually takes a few hours)")
            print("📝 The API will start but Earth Engine endpoints will return errors until registration is complete.")
        else:
            print("📖 Please check your service account configuration and try again.")
            
        # Don't raise the exception - let the server start anyway
        return False
    
    return True


# Configuration instance
config = Config()