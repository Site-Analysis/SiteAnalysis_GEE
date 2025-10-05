# Earth Engine FastAPI Suite

A comprehensive collection of FastAPI applications for accessing and analyzing various Google Earth Engine datasets focused on India. This suite provides REST APIs for administrative boundaries, vegetation analysis, hydrology, water surface monitoring, forest change detection, and building analysis.

## 🌍 Overview

This project contains **7 specialized FastAPI applications**, each designed to work with specific Earth Engine datasets. All applications support Indian administrative boundaries through FAO GAUL dataset integration, allowing users to query data by district/state names or custom coordinates.

---

## 📊 Available APIs

### 1. **Administrative Boundaries API** - `app_gaul.py`
**Port:** 8001 | **Dataset:** `FAO/GAUL_SIMPLIFIED_500m/2015/level2`

#### **Data Access:**
- ✅ **ADM0:** Country-level boundaries (India)
- ✅ **ADM1:** State/Province boundaries (~36 states/UTs)
- ✅ **ADM2:** District/Municipality boundaries (~700+ districts)

#### **Key Features:**
- Complete Indian administrative hierarchy
- District and state boundary extraction
- GeoJSON and properties-only responses
- Interactive map generation
- Boundary area calculations

#### **Available Data Fields:**
```json
{
  "ADM0_CODE": "Country code (115 for India)",
  "ADM0_NAME": "Country name",
  "ADM1_CODE": "State code", 
  "ADM1_NAME": "State name",
  "ADM2_CODE": "District code",
  "ADM2_NAME": "District name",
  "Shape_Area": "Boundary area",
  "EXP2_YEAR": "Expiry year",
  "STR2_YEAR": "Creation year"
}
```

#### **Key Endpoints:**
- `/gaul-boundaries` - Get administrative boundaries
- `/gaul-states` - List all Indian states
- `/gaul-districts` - Get district-level data
- `/gaul-state-districts/{state}` - Districts within specific state

---

### 2. **Vegetation Analysis API** - `app_viirs.py`
**Port:** 8002 | **Dataset:** `NASA/VIIRS/002/VNP13A1`

#### **Data Access:**
- ✅ **Temporal Range:** 16-day composites (2012-present)
- ✅ **Spatial Resolution:** 500 meters
- ✅ **Coverage:** Global (India focus)

#### **Available Vegetation Indices:**
```json
{
  "NDVI": "Normalized Difference Vegetation Index",
  "EVI": "Enhanced Vegetation Index (3-band)",
  "EVI2": "Enhanced Vegetation Index (2-band)"
}
```

#### **Reflectance Bands:**
```json
{
  "NIR_reflectance": "Near-infrared (846-885nm)",
  "red_reflectance": "Red band (600-680nm)", 
  "green_reflectance": "Green band (545-656nm)",
  "blue_reflectance": "Blue band (478-498nm)",
  "SWIR1_reflectance": "Shortwave IR (1230-1250nm)",
  "SWIR2_reflectance": "Shortwave IR (1580-1640nm)",
  "SWIR3_reflectance": "Shortwave IR (2225-2275nm)"
}
```

#### **Quality Assessment:**
- **VI_Quality:** Quality assessment bit-field
- **pixel_reliability:** 12-class reliability (0=Excellent, 11=LTAVG)
- **composite_day_of_the_year:** Julian day information

#### **Key Endpoints:**
- `/viirs-vegetation-indices` - NDVI/EVI analysis with maps
- `/viirs-time-series` - Temporal vegetation trends
- `/viirs-quality-analysis` - Data quality assessment
- `/viirs-reflectance` - Spectral band analysis

---

### 3. **Hydrology Analysis API** - `app_merit_hydro.py`
**Port:** 8003 | **Dataset:** `MERIT/Hydro/v1_0_1`

#### **Data Access:**
- ✅ **Spatial Resolution:** ~93 meters (3 arc-seconds)
- ✅ **Coverage:** Global hydrologically-corrected DEM

#### **Available Hydrological Data:**
```json
{
  "elv": "Elevation (meters above sea level)",
  "dir": "Flow Direction (8-direction coding)",
  "wth": "River channel width (meters)",
  "wat": "Land/permanent water classification (0/1)",
  "upa": "Upstream drainage area (km²)",
  "upg": "Upstream drainage pixels (count)",
  "hnd": "Height above nearest drainage (meters)",
  "viswth": "Visualization of river channel width"
}
```

#### **Flow Direction Encoding:**
- 1: East, 2: Southeast, 4: South, 8: Southwest
- 16: West, 32: Northwest, 64: North, 128: Northeast
- 0: River mouth, -1: Inland depression

#### **Key Endpoints:**
- `/hydro-elevation` - Elevation analysis with statistics
- `/hydro-flow-analysis` - Flow direction and drainage analysis
- `/hydro-rivers` - River network and channel width analysis
- `/hydro-drainage` - Upstream area and flow accumulation

---

### 4. **Water Surface Analysis API** - `app_jrc_water.py`  
**Port:** 8004 | **Dataset:** `JRC/GSW1_4/GlobalSurfaceWater`

#### **Data Access:**
- ✅ **Temporal Coverage:** 1984-2021 (37 years)
- ✅ **Spatial Resolution:** 30 meters
- ✅ **Update Frequency:** Annual

#### **Available Water Metrics:**
```json
{
  "occurrence": "Water presence frequency (0-100%)",
  "change_abs": "Absolute change 1984-1999 vs 2000-2021 (-100 to +100%)",
  "change_norm": "Normalized change in occurrence (-100 to +100%)", 
  "seasonality": "Months water is present (0-12)",
  "recurrence": "Frequency water returns year-to-year (0-100%)",
  "transition": "Categorical change classification",
  "max_extent": "Binary: anywhere water ever detected (0/1)"
}
```

#### **Water Change Categories:**
- Permanent water, New permanent water, Lost permanent water
- Seasonal water, New seasonal water, Lost seasonal water
- Seasonal to permanent, Permanent to seasonal

#### **Key Endpoints:**
- `/water-occurrence` - Water presence frequency analysis
- `/water-seasonality` - Seasonal water pattern analysis  
- `/water-change` - Water change detection (1984-2021)
- `/water-transitions` - Categorical water change analysis

---

### 5. **Forest Change Analysis API** - `app_hansen_forest.py`
**Port:** 8006 | **Dataset:** `UMD/hansen/global_forest_change_2024_v1_12`

#### **Data Access:**
- ✅ **Temporal Coverage:** 2000-2024 (24 years)
- ✅ **Spatial Resolution:** ~30 meters
- ✅ **Update Frequency:** Annual

#### **Available Forest Metrics:**
```json
{
  "treecover2000": "Tree canopy cover in year 2000 (0-100%)",
  "loss": "Forest loss during study period (binary)",
  "gain": "Forest gain 2000-2012 (binary)", 
  "lossyear": "Year of forest loss (0=no loss, 1-24=2001-2024)"
}
```

#### **Landsat Composite Bands:**
```json
{
  "first_b30": "Red band - first year (typically 2000)",
  "first_b40": "NIR band - first year", 
  "first_b50": "SWIR1 band - first year",
  "first_b70": "SWIR2 band - first year",
  "last_b30": "Red band - last year (typically 2024)",
  "last_b40": "NIR band - last year",
  "last_b50": "SWIR1 band - last year", 
  "last_b70": "SWIR2 band - last year"
}
```

#### **Key Endpoints:**
- `/forest-cover` - Tree cover analysis and statistics
- `/forest-change` - Forest loss/gain detection
- `/forest-loss-analysis` - Annual forest loss trends
- `/forest-composite` - Landsat composite imagery

---

### 6. **Building Footprints API** - `app_open_buildings.py`
**Port:** 8005 | **Dataset:** `GOOGLE/Research/open-buildings/v3/polygons`

#### **Data Access:**
- ✅ **Data Type:** Vector polygons (building footprints)
- ✅ **Coverage:** Global building footprints
- ✅ **Confidence Range:** 0.65-1.0

#### **Available Building Data:**
```json
{
  "area_in_meters": "Building area (square meters)",
  "confidence": "AI model confidence (0.65-1.0)", 
  "full_plus_code": "Plus Code at building centroid",
  "longitude_latitude": "Building centroid coordinates"
}
```

#### **Key Endpoints:**
- `/buildings-footprints` - Extract building polygons
- `/buildings-area-analysis` - Building area statistics
- `/buildings-confidence` - AI confidence analysis
- `/buildings-density` - Building density mapping

---

### 7. **Temporal Building Analysis API** - `app_open_buildings_temporal.py`
**Port:** 8007 | **Dataset:** `GOOGLE/Research/open-buildings-temporal/v1`

#### **Data Access:**
- ✅ **Data Type:** Raster imagery (temporal building metrics)
- ✅ **Temporal Coverage:** Multi-temporal (2016-2024)
- ✅ **Spatial Resolution:** Variable resolution

#### **Available Temporal Building Metrics:**
```json
{
  "building_fractional_count": "Building density per pixel (0-0.0216)",
  "building_height": "Height relative to terrain (0-100m)",
  "building_presence": "Model confidence for presence (0-1, uncalibrated)"
}
```

#### **Analysis Capabilities:**
- **Height Analysis:** Building height distribution and percentiles
- **Presence Analysis:** Confidence-based building detection
- **Count Analysis:** Building density estimation
- **Time Series:** Track building changes over time
- **Composite Methods:** Median, mean, max temporal aggregation

#### **Key Endpoints:**
- `/temporal-building-analysis` - Comprehensive building statistics
- `/temporal-height-analysis` - Building height analysis
- `/temporal-presence-analysis` - Building presence confidence
- `/temporal-count-analysis` - Building density analysis
- `/temporal-time-series` - Temporal building trends

---

## 🌐 Common Features Across All APIs

### **Region Support:**
1. **Predefined Cities:** Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur
2. **GAUL Integration:** Any Indian district or state name (700+ districts, 36+ states/UTs)
3. **Custom Coordinates:** User-defined bounding boxes (west, south, east, north)

### **Response Formats:**
- **JSON:** Structured data with statistics and metadata
- **GeoJSON:** Spatial data with geometry (where applicable)
- **Interactive Maps:** HTML files with visualization layers
- **Time Series:** Temporal data arrays for trend analysis

### **Error Handling:**
- Graceful fallbacks for large regions (auto-scaling, pixel limits)
- Region disambiguation (state_name parameter)
- Data availability validation
- Detailed error messages with suggestions

---

## 🚀 Quick Start

### **1. Setup Environment:**
```bash
# Install dependencies
pip install fastapi uvicorn earthengine-api geemap python-dotenv

# Setup Earth Engine authentication
earthengine authenticate

# Create .env file with credentials
echo "GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json" > .env
```

### **2. Start Any API:**
```bash
# Administrative boundaries (port 8001)
uvicorn.exe app_gaul:app --port 8001

# Vegetation analysis (port 8002)  
uvicorn.exe app_viirs:app --port 8002

# Hydrology analysis (port 8003)
uvicorn.exe app_merit_hydro:app --port 8003

# Water surface analysis (port 8004)
uvicorn.exe app_jrc_water:app --port 8004

# Building footprints (port 8005)
uvicorn.exe app_open_buildings:app --port 8005

# Forest change (port 8006)
uvicorn.exe app_hansen_forest:app --port 8006

# Temporal buildings (port 8007)
uvicorn.exe app_open_buildings_temporal:app --port 8007
```
    http://localhost:portnumber/docs

### **3. Access Interactive Documentation:**
- Navigate to `http://localhost:PORT/docs` for Swagger UI
- Example: `http://localhost:8002/docs` for vegetation API

---

## 📋 Usage Examples

### **Administrative Boundaries:**
```bash
# Get all districts in Karnataka
curl "http://localhost:8001/gaul-state-districts/Karnataka"

# Search for districts containing "Bangalore"
curl "http://localhost:8001/gaul-search?search_term=Bangalore"
```

### **Vegetation Analysis:**
```bash
# NDVI analysis for Ernakulam district
curl "http://localhost:8002/viirs-vegetation-indices?region=Ernakulam&state_name=Kerala&indices=NDVI"

# Time series for custom coordinates
curl "http://localhost:8002/viirs-time-series?region=custom&west=77.0&south=12.5&east=78.0&north=13.5&index=NDVI&start_date=2023-01-01&end_date=2023-12-31"
```

### **Water Surface Analysis:**
```bash
# Water occurrence in Chennai
curl "http://localhost:8004/water-occurrence?region=chennai&include_map=true"

# Water change analysis for Mumbai
curl "http://localhost:8004/water-change?region=mumbai&start_epoch=1984-1999&end_epoch=2000-2021"
```

### **Building Analysis:**
```bash
# Building height analysis in Bangalore
curl "http://localhost:8007/temporal-height-analysis?region=bangalore&height_threshold=20&include_map=true"

# Building footprints in Delhi
curl "http://localhost:8005/buildings-footprints?region=delhi&min_confidence=0.8"
```

---

## 🛠️ Technical Specifications

### **Earth Engine Authentication:**
- Service account authentication via JSON key file
- User authentication via `earthengine authenticate`
- Environment variable: `GOOGLE_APPLICATION_CREDENTIALS`

### **Performance Optimizations:**
- Automatic pixel limit handling (`maxPixels`, `bestEffort`)
- Scale optimization based on region size
- Progressive fallback strategies for large regions
- Efficient composite methods for temporal data

### **Data Processing:**
- Server-side processing via Earth Engine
- Client-side aggregation for statistics
- On-demand map generation with geemap
- Temporal compositing (median, mean, max)

---

## 📈 Data Coverage Summary

| Dataset | Temporal Range | Spatial Resolution | Coverage | Update Frequency |
|---------|----------------|-------------------|----------|------------------|
| FAO GAUL | 2015 (static) | 500m simplified | Global | Static |
| NASA VIIRS | 2012-present | 500m | Global | 16-day |
| MERIT Hydro | Static DEM | ~93m | Global | Static |
| JRC Water | 1984-2021 | 30m | Global | Annual |
| Hansen Forest | 2000-2024 | ~30m | Global | Annual |
| Open Buildings v3 | Static snapshot | Variable | Global | Static |
| Open Buildings Temporal | 2016-2024 | Variable | Global | Irregular |

---

## 🔧 Additional Features to Consider Adding

### **Enhanced Documentation:**
1. **Dataset Metadata Endpoints:** Add `/dataset-info` endpoints with detailed metadata
2. **Usage Statistics:** Track API usage and popular queries
3. **Rate Limiting:** Implement request rate limiting for production use

### **Advanced Analysis:**
4. **Multi-Dataset Queries:** Combine data from multiple datasets in single requests
5. **Batch Processing:** Process multiple regions simultaneously
6. **Export Capabilities:** Direct export to Google Drive, Cloud Storage
7. **Caching Layer:** Redis caching for frequently requested data

### **User Experience:**
8. **Interactive Web Frontend:** Simple web interface for non-technical users
9. **Query Builder:** Visual query construction tool
10. **Data Validation:** Input validation and suggestion system
11. **Thumbnail Previews:** Quick preview images for regions

### **Production Features:**
12. **Authentication System:** User management and API keys
13. **Monitoring & Logging:** Request tracking and error monitoring
14. **Auto-scaling:** Kubernetes deployment configurations
15. **Database Integration:** Store processed results and user queries

### **Data Integration:**
16. **Weather Data:** Add meteorological datasets
17. **Population Data:** Demographic and census integration
18. **Economic Indicators:** GDP, land use economics
19. **Real-time Data:** Satellite imagery with near real-time updates

---

## 📝 Contributing

To add a new dataset API:

1. **Create new FastAPI file:** `app_your_dataset.py`
2. **Follow existing patterns:** Region handling, error management, map generation
3. **Add GAUL integration:** Support district/state name queries
4. **Include comprehensive endpoints:** Health check, data analysis, visualization
5. **Update documentation:** Add dataset details to this README
6. **Test thoroughly:** Verify all endpoints and error cases

---

## 📄 License & Credits

- **Earth Engine:** Google Earth Engine Terms of Service
- **Datasets:** Each dataset has its own license (see individual dataset documentation)
- **FastAPI:** MIT License
- **This Project:** Open source (specify your preferred license)

---

## 🔗 Useful Links

- [Google Earth Engine](https://earthengine.google.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Earth Engine Python API](https://developers.google.com/earth-engine/guides/python_install)
- [Geemap Documentation](https://geemap.org/)
- [Dataset Catalog](https://developers.google.com/earth-engine/datasets/)
