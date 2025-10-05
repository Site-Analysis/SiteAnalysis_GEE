import ee
import geemap
import os
from dotenv import load_dotenv

# Load environment variables and initialize Earth Engine
load_dotenv()
try:
    ee.Initialize()
    print("Earth Engine initialized successfully!")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")
    exit(1)

def mask_s2_clouds(image):
    """Masks clouds in a Sentinel-2 image using the QA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QA60')

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloud_bit_mask)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask).divide(10000)

print("Loading Sentinel-2 dataset with cloud masking...")
dataset = (
    ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
    .filterDate('2022-01-01', '2022-01-31')
    # Pre-filter to get less cloudy granules.
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .map(mask_s2_clouds)
)

print(f"Found {dataset.size().getInfo()} images in collection")
sentinel_image = dataset.median()
print("Created cloud-masked median composite image")

# Define RGB visualization parameters
rgb_vis = {
    'min': 0.0,
    'max': 0.3,
    'bands': ['B4', 'B3', 'B2'],
}

# Create a map and add the data as a layer (Portugal/Lisbon area - default location)
print("Creating interactive map...")
m = geemap.Map()
m.set_center(-9.1695, 38.6917, 12)  # Portugal/Lisbon coordinates from documentation
m.add_layer(sentinel_image, rgb_vis, 'RGB')
print("Added Sentinel-2 RGB layer to map")

# Save the map as HTML file for viewing in browser
output_file = 'portugal_sentinel2_map.html'
m.to_html(filename=output_file)
print(f"Map saved as {output_file}")
print(f"Open {output_file} in your web browser to view the interactive map!")

# Also try to open it automatically
try:
    import webbrowser
    webbrowser.open(output_file)
    print("Attempting to open map in default web browser...")
except Exception as e:
    print(f"Could not auto-open browser: {e}")