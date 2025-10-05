import ee
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    ee.Initialize()
    print("Earth Engine initialized successfully!")
    print(ee.Number(10).getInfo())
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")

# Working with MODIS Land Cover dataset
print("\n--- MODIS Land Cover Analysis ---")

# Load the MODIS Land Cover dataset
dataset = ee.ImageCollection('MODIS/061/MCD12C1')

# Get the most recent image
latest_image = dataset.sort('system:time_start', False).first()

print(f"Dataset ID: MODIS/061/MCD12C1")
print(f"Latest image date: {ee.Date(latest_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()}")
print(f"Available bands: {latest_image.bandNames().getInfo()}")

# Define an area of interest (example: Middle of Indian Ocean)
aoi = ee.Geometry.Rectangle([75.0, -15.0, 85.0, -5.0])

# Clip the image to your area of interest
clipped_image = latest_image.clip(aoi)

# Get land cover types in the area - CORRECTED BAND NAME
land_cover_band = clipped_image.select('Majority_Land_Cover_Type_1')

# Print some statistics
print(f"\nImage projection: {land_cover_band.projection().crs().getInfo()}")
print(f"Pixel resolution: {land_cover_band.projection().nominalScale().getInfo()} meters")

# Get unique land cover values in your area
# Note: This might take a moment for large areas
try:
    # Sample the image to get land cover statistics
    sample = land_cover_band.sample(
        region=aoi,
        scale=500,  # 500m resolution
        numPixels=1000,
        geometries=True
    )
    
    # Get the first few samples
    sample_list = sample.limit(10).getInfo()
    print(f"\nFirst 10 land cover samples:")
    for i, feature in enumerate(sample_list['features']):
        lc_value = feature['properties']['Majority_Land_Cover_Type_1']
        print(f"Sample {i+1}: Land Cover Type = {lc_value}")
        
except Exception as e:
    print(f"Sampling error (this is normal for large areas): {e}")

# Land cover type meanings (from MODIS documentation)
land_cover_types = {
    0: "Water Bodies",
    1: "Evergreen Needleleaf Forests",
    2: "Evergreen Broadleaf Forests", 
    3: "Deciduous Needleleaf Forests",
    4: "Deciduous Broadleaf Forests",
    5: "Mixed Forests",
    6: "Closed Shrublands",
    7: "Open Shrublands",
    8: "Woody Savannas",
    9: "Savannas",
    10: "Grasslands",
    11: "Permanent Wetlands",
    12: "Croplands",
    13: "Urban and Built-up Lands",
    14: "Cropland/Natural Vegetation Mosaics",
    15: "Permanent Snow and Ice",
    16: "Barren",
    17: "Unclassified"
}

print("\nLand Cover Type Legend:")
for code, description in land_cover_types.items():
    print(f"{code}: {description}")

# Export example (uncomment to use)
"""
# Export to Google Drive
task = ee.batch.Export.image.toDrive(
    image=land_cover_band,
    description='MODIS_Land_Cover_California',
    folder='EarthEngine',
    scale=500,
    region=aoi,
    maxPixels=1e9
)
task.start()
print(f"Export task started: {task.id}")
"""

print("\nScript completed successfully!")
