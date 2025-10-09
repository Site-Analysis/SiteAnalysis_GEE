# 🛰️ GEE Geospatial Analysis Platform

A comprehensive FastAPI backend service that integrates **Google Earth Engine (GEE)** for advanced geospatial analysis. This platform provides real-time satellite data analysis, building-level intelligence, and interactive mapping capabilities with a focus on India.

## 🌟 Key Features

### 🛰️ **Multi-Dataset Satellite Analysis**
- **Sentinel-2**: High-resolution imagery for vegetation indices (NDVI, NDBI, NDWI)
- **SRTM**: Digital elevation models and terrain analysis
- **ESA WorldCover**: Global land cover classification
- **JRC Water**: Surface water occurrence and hydrology
- **CHIRPS**: Precipitation and climate data

### � **Comprehensive Vegetation Analysis** (NEW!)
- **Sentinel-2 + MODIS Integration**: Dual-source vegetation monitoring for maximum reliability
- **Multiple Vegetation Indices**: NDVI, EVI, and SAVI for comprehensive plant health assessment
- **Vegetation Health Metrics**: Combined health indices and greenness indicators
- **Dynamic Distribution Analysis**: Automated vegetation density classification
- **5 Specialized Visualizations**: NDVI, EVI, SAVI, health index, and classification maps
- **Polygon-Based Clipping**: Precise vegetation analysis within drawn boundaries

### �🏢 **Building-Level Intelligence**
- **Google Research Open Buildings**: Individual building footprints and metrics
- **VIIRS Nighttime Lights**: Economic activity indicators
- **WorldPop Population**: High-resolution demographic data
- **Urban Heat Island**: Thermal analysis using Landsat 8

### 🏛️ **Administrative Boundaries Analysis** 
- **FAO GAUL Dataset**: Country, state, and district-level boundary analysis
- **3-Tier Hierarchy**: Complete administrative context with area calculations
- **Polygon-Clipped Visualizations**: Boundary maps precisely fitted to analysis areas

### 🎯 **Advanced Analysis Modes**
- **Point Analysis**: Click-and-analyze with customizable buffers
- **Polygon Analysis**: Draw precise areas for specialized analysis (buildings, vegetation, administrative)
- **Interactive Mapping**: Real-time visualization with Leaflet.js
- **RESTful API**: Clean endpoints with automatic documentation

## 🆕 Recent Major Updates (v2.0)

### 🌱 **Comprehensive Vegetation Analysis System**
- **Dual-Source Integration**: Combined Sentinel-2 (10m resolution) and MODIS (250m resolution) for maximum reliability
- **Advanced Vegetation Indices**:
  - **NDVI**: Traditional vegetation health metric
  - **EVI**: Enhanced vegetation index for dense canopy areas  
  - **SAVI**: Soil-adjusted vegetation index for accurate readings
- **Intelligent Health Metrics**: Vegetation health index, greenness indicators, and quality assessments
- **Dynamic Classification**: Automated vegetation density distribution (non-vegetated, low, moderate, dense)
- **5 Specialized Visualizations**: Individual maps for NDVI, EVI, SAVI, health index, and classification
- **Global Coverage**: Works worldwide with intelligent fallback systems

### 🏛️ **Administrative Boundaries Integration**
- **FAO GAUL Dataset**: Official administrative boundaries for global coverage
- **3-Tier Hierarchy Analysis**: Country → State/Province → District/County breakdown
- **Contextual Information**: Full administrative path and area calculations within ROI
- **Polygon-Clipped Visualizations**: Boundary maps precisely fitted to analysis areas
- **Regional Intelligence**: Administrative unit details with codes and geographic context

### 🎯 **Enhanced Analysis Capabilities**
- **Polygon-Based Processing**: All analysis types now support precise polygon boundaries
- **Improved Visualization Clipping**: Maps are clipped to exact analysis areas (no more circles!)
- **Comprehensive Frontend**: Dedicated UI sections for each analysis type with detailed metrics
- **Robust Error Handling**: Multiple fallback systems for maximum reliability
- **Performance Optimizations**: Faster processing with intelligent data source selection

### 🛠️ **Technical Improvements**
- **Pydantic Model Updates**: Enhanced data validation and serialization
- **API Endpoint Expansion**: New `/analyze-polygon` endpoint for specialized analysis
- **Layer Configuration System**: Dynamic layer selection with intelligent defaults
- **Comprehensive Logging**: Detailed backend logging for debugging and monitoring
- **Quality Indicators**: Data source information and analysis quality metrics

## 📁 Project Structure

```
gee-trial/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment and authentication setup
│   ├── models.py            # Pydantic request/response schemas
│   └── gee_utils.py         # Earth Engine utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test configuration and fixtures
│   ├── test_main.py         # API endpoint tests
│   ├── test_models.py       # Pydantic model tests
│   ├── test_gee_utils.py    # Earth Engine utility tests
│   └── test_integration.py  # Integration tests
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🚀 Complete Setup Guide

### 📋 **Prerequisites**

Before starting, ensure you have:

1. **Python 3.8 or higher** installed
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Visual Studio Code** with Live Server extension
   - Download VS Code from [code.visualstudio.com](https://code.visualstudio.com/)
   - Install Live Server extension for the interactive map

3. **Google Cloud Account** (free tier available)
   - Sign up at [cloud.google.com](https://cloud.google.com/)

4. **Git** installed (optional but recommended)
   - Download from [git-scm.com](https://git-scm.com/)

---

### 🛠️ **Step 1: Download and Setup Project**

#### Option A: Download ZIP (Recommended for beginners)
1. **Download the project** as a ZIP file from GitHub
2. **Extract** to your desired location (e.g., `C:\Users\YourName\Desktop\gee-trial`)
3. **Open PowerShell** as Administrator and navigate to the project:
   ```powershell
   cd "C:\Users\YourName\Desktop\gee-trial"
   ```

#### Option B: Clone with Git
```bash
git clone https://github.com/TanmayCJ/tcjpr.git
cd tcjpr
```

---

### 🐍 **Step 2: Python Environment Setup**

1. **Open PowerShell** in the project directory:
   ```powershell
   # Navigate to your project folder
   cd "C:\Users\YourName\Desktop\gee-trial"
   ```

2. **Create virtual environment**:
   ```powershell
   python -m venv venv
   ```

3. **Activate virtual environment**:
   ```powershell
   # On Windows PowerShell
   .\venv\Scripts\Activate.ps1
   
   # If you get execution policy error, run this first:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Install all required packages**:
   ```powershell
   # Upgrade pip first
   python -m pip install --upgrade pip
   
   # Install core packages
   pip install fastapi uvicorn pydantic httpx
   
   # Install Earth Engine and dependencies
   pip install earthengine-api google-cloud-storage google-auth
   
   # Install additional dependencies
   pip install python-dotenv pytest pytest-cov
   ```

   **Alternative: Install from requirements.txt**
   ```powershell
   pip install -r requirements.txt
   ```

---

### 🌍 **Step 3: Google Earth Engine Setup**

#### **3.1 Create Google Cloud Project**

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project**:
   - Click "Select a project" → "New Project"
   - Enter project name (e.g., "my-gee-project")
   - Click "Create"

#### **3.2 Enable Earth Engine API**

1. **In Cloud Console**, search for "Earth Engine API"
2. **Click on "Earth Engine API"** in results
3. **Click "Enable"** button
4. **Wait for enablement** (usually takes 1-2 minutes)

#### **3.3 Create Service Account**

1. **Go to IAM & Admin** → **Service Accounts**
2. **Click "Create Service Account"**:
   - **Service account name**: `gee-service-account`
   - **Description**: `Service account for Earth Engine access`
   - Click **"Create and Continue"**

3. **Grant permissions**:
   - **Select role**: `Editor` (or `Earth Engine Resource Admin`)
   - Click **"Continue"** → **"Done"**

4. **Create and download key**:
   - **Click on your service account** in the list
   - Go to **"Keys"** tab
   - **Click "Add Key"** → **"Create new key"**
   - **Select "JSON"** format
   - **Click "Create"** - this downloads the JSON file

5. **Save the JSON file**:
   - **Rename** the downloaded file to `gee-sa.json`
   - **Move it** to your project folder (same directory as `main.py`)

#### **3.4 Register for Earth Engine**

1. **Go to [earthengine.google.com](https://earthengine.google.com/)**
2. **Click "Get Started"**
3. **Choose "Noncommercial Use"** (free)
4. **Sign in** with the same Google account used for Cloud Console
5. **Fill out the registration form**
6. **Wait for approval** (usually instant for noncommercial use)

---

### ⚙️ **Step 4: Configure Environment**

1. **Create `.env` file** in your project root:
   ```powershell
   # Create the file
   New-Item -Path ".env" -ItemType File
   ```

2. **Edit `.env` file** (open with Notepad or VS Code):
   ```env
   # Google Earth Engine Configuration
   GEE_SERVICE_ACCOUNT_EMAIL=gee-service-account@your-project-id.iam.gserviceaccount.com
   GEE_SERVICE_ACCOUNT_KEY_PATH=gee-sa.json
   
   # Replace 'your-project-id' with your actual Google Cloud project ID
   ```

   **Find your project ID**: In Google Cloud Console, it's shown in the project selector dropdown.

---

### 🧪 **Step 5: Test Installation**

1. **Test Python packages**:
   ```powershell
   # Make sure virtual environment is activated
   .\venv\Scripts\Activate.ps1
   
   # Test Earth Engine import
   python -c "import ee; print('✅ Earth Engine imported successfully')"
   
   # Test FastAPI import  
   python -c "import fastapi; print('✅ FastAPI imported successfully')"
   ```

2. **Test Earth Engine authentication**:
   ```powershell
   python -c "
   import ee
   ee.Initialize()
   print('✅ Earth Engine authenticated successfully')
   test_image = ee.Image('COPERNICUS/S2_SR/20230101T061241_20230101T061238_T43PGQ')
   print('✅ Can access satellite data')
   "
   ```

---

### 🚀 **Step 6: Launch the Application**

#### **6.1 Start the Backend Server**

1. **Open PowerShell** in project directory:
   ```powershell
   cd "C:\Users\YourName\Desktop\gee-trial"
   
   # Activate virtual environment
   .\venv\Scripts\Activate.ps1
   
   # Start the server
   uvicorn app.main:app --reload --port 8001
   ```

2. **Success indicators** you should see:
   ```
   🚀 Starting GEE FastAPI Backend...
   ✅ Google Earth Engine initialized successfully  
   ✅ GEE connection test successful
   ✅ Application startup completed successfully
   INFO: Uvicorn running on http://127.0.0.1:8001
   ```

3. **Test the API**:
   - **Open browser** and go to: http://localhost:8001/docs
   - **Try the health check**: http://localhost:8001/health

#### **6.2 Launch Interactive Map**

**Method A: Using VS Code Live Server (Recommended)**
1. **Open VS Code** in your project folder
2. **Install Live Server extension**:
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Live Server" by Ritwick Dey
   - Click "Install"
3. **Launch the map**:
   - **Right-click** on `interactive_map.html`
   - **Select "Open with Live Server"**
   - The map opens automatically in your browser

**Method B: Using Python HTTP Server**
1. **Open a new PowerShell terminal**:
   ```powershell
   cd "C:\Users\YourName\Desktop\gee-trial"
   
   # Start HTTP server
   python -m http.server 8080
   ```
2. **Open browser** and go to: http://localhost:8080/interactive_map.html

---

### 🎯 **Step 7: Use the Platform**

#### **Basic Analysis**
1. **Click anywhere on the map** to analyze that location
2. **Select analysis type**:
   - **Basic**: NDVI, elevation, land cover
   - **Vegetation**: Comprehensive vegetation analysis
   - **Urban Planning**: Built-up area analysis
   - **Building Analysis (NEW!)**: Individual building intelligence
3. **Adjust buffer radius** (100-5000 meters)
4. **Click "Analyze Location"**

#### **Building Analysis (Advanced)**
1. **Select "Building Analysis (NEW!)"** from dropdown
2. **Use drawing tools** to draw a polygon around buildings
3. **Click "Analyze Location"**
4. **View results**: Building count, individual building metrics, urban context

---

### 📦 **Complete Package List**

Your system uses these Python packages:

#### **Core Web Framework**
- `fastapi==0.104.1` - Modern web framework
- `uvicorn==0.24.0` - ASGI server
- `pydantic==2.5.0` - Data validation

#### **Google Earth Engine**
- `earthengine-api==0.1.385` - Earth Engine Python API
- `google-cloud-storage==2.10.0` - Google Cloud integration
- `google-auth==2.25.2` - Authentication

#### **Data Processing**
- `httpx==0.25.2` - HTTP client for API calls
- `python-dotenv==1.0.0` - Environment variable management

#### **Development & Testing**
- `pytest==7.4.3` - Testing framework
- `pytest-cov==4.1.0` - Test coverage

#### **Optional Dependencies**
- `requests==2.31.0` - Alternative HTTP client
- `python-multipart==0.0.6` - File upload support

## 🗺️ Interactive Map Interface

### Running the Complete System

Follow these steps to run both the backend API and interactive map:

#### Step 1: Start the Backend Server

1. **Open PowerShell** and navigate to project directory:
   ```powershell
   cd "c:\Users\tanny\OneDrive\Desktop\gee trial"
   ```

2. **Activate the virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Start the FastAPI server**:
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

   ✅ **Success indicators:**
   - You should see "🚀 Starting GEE FastAPI Backend..."
   - "✅ Google Earth Engine initialized successfully"
   - "INFO: Uvicorn running on http://0.0.0.0:8001"

#### Step 2: Launch the Interactive Map

1. **Open VS Code** in the project directory
2. **Install Live Server extension** (if not already installed):
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Live Server"
   - Install the extension by Ritwick Dey

3. **Launch the interactive map**:
   - Right-click on `interactive_map.html`
   - Select "Open with Live Server"
   - The map will open in your default browser

   **Alternative method (without Live Server):**
   ```powershell
   # In a new PowerShell terminal
   cd "c:\Users\tanny\OneDrive\Desktop\gee trial"
   .\venv\Scripts\python.exe -m http.server 3000
   # Then open: http://localhost:3000/interactive_map.html
   ```

#### Step 3: Use the Interactive Map

1. **Draw on the map**:
   - Use the drawing tools on the left to draw a polygon
   - Or simply click anywhere on the map to analyze that point

2. **Configure analysis**:
   - Select which layers to analyze (NDVI, elevation, landcover, etc.)
   - Adjust the buffer radius (100-5000 meters)
   - Set date range for satellite data

3. **Run analysis**:
   - Click "Analyze Location"
   - View results in the sidebar
   - See visualization overlays on the map

### For Team Setup (Others)

If someone else wants to run this project:

#### Initial Setup (One-time)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd gee-trial
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Google Earth Engine Setup**:
   - Create a Google Cloud Project
   - Enable Earth Engine API
   - Create a service account with Earth Engine permissions
   - Download the service account JSON key as `gee-sa.json`
   - Create `.env` file with your credentials:
     ```env
     GEE_SERVICE_ACCOUNT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
     GEE_SERVICE_ACCOUNT_KEY_PATH=gee-sa.json
     ```

4. **Register for Earth Engine** (if not already done):
   - Go to [Earth Engine registration](https://earthengine.google.com/)
   - Sign up for a noncommercial account
   - Wait for approval (usually instant for noncommercial use)

#### Daily Workflow

1. **Terminal 1 - Backend**:
   ```bash
   cd path/to/gee-trial
   .\venv\Scripts\Activate.ps1  # Windows
   # source venv/bin/activate    # macOS/Linux
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

2. **Terminal 2 - Frontend (optional)**:
   ```bash
   cd path/to/gee-trial
   .\venv\Scripts\python.exe -m http.server 3000
   # Then open: http://localhost:3000/interactive_map.html
   ```

3. **Or use VS Code Live Server**:
   - Open project in VS Code
   - Right-click `interactive_map.html` → "Open with Live Server"

## 📊 **Complete Dataset Reference**

Your platform integrates **9 comprehensive satellite datasets** for advanced geospatial intelligence:

### **🛰️ Core Earth Observation Data**

| Dataset | Purpose | Resolution | Coverage | Usage |
|---------|---------|------------|----------|-------|
| **Sentinel-2 Harmonized** | Multispectral imagery | 10-60m | Global | NDVI, NDBI, NDWI, true color |
| **SRTM Digital Elevation** | Terrain analysis | 30m | Near-global | Elevation, slope, watershed |
| **ESA WorldCover** | Land classification | 10m | Global | 11 land cover classes |
| **JRC Global Surface Water** | Water occurrence | 30m | Global | Water frequency (1984-2021) |
| **CHIRPS Precipitation** | Climate data | 5.5km | Global | Daily/annual rainfall |

### **🏢 Urban Intelligence Data**

| Dataset | Purpose | Resolution | Coverage | Usage |
|---------|---------|------------|----------|-------|
| **Google Open Buildings** | Building footprints | Vector | 60+ countries | Individual building analysis |
| **VIIRS Nighttime Lights** | Economic activity | 463m | Global | Urban development, energy |
| **WorldPop Population** | Demographics | 100m | Global | Population density |
| **Landsat 8 Thermal** | Temperature | 30m | Global | Urban heat island analysis |

### **📈 Analysis Capabilities**

#### **🌱 Vegetation Intelligence**
- **NDVI** (Normalized Difference Vegetation Index)
- **NDBI** (Built-up Index) 
- **NDWI** (Water Index)
- **Green space analysis** around buildings

#### **�️ Terrain Analysis**
- **Digital elevation models**
- **Slope calculations** for development suitability
- **Watershed analysis**
- **Flood risk assessment**

#### **🏙️ Urban Planning**
- **Land cover classification** (11 categories)
- **Built-up area detection** and quantification
- **Urban growth monitoring**
- **Green infrastructure mapping**

#### **🏢 Building-Level Intelligence**
- **Individual building detection** with confidence scores
- **Building metrics**: Area, perimeter, footprint analysis
- **Urban context**: Population, economic activity, thermal conditions
- **Microclimate assessment** around each building

---

### Analyze Location

**POST** `/analyze-location`

Analyze a geographic location with customizable parameters.

**Request Body:**
```json
{
  "lat": 12.9716,
  "lon": 77.5946,
  "buffer_m": 750,
  "layers": ["ndvi", "elevation", "slope", "landcover"]
}
```

**Parameters:**
- `lat`: Latitude (-90 to 90)
- `lon`: Longitude (-180 to 180)
- `buffer_m`: Analysis buffer in meters (100-5000, default: 750)
- `layers`: List of analysis layers (optional, defaults: ["ndvi", "elevation", "slope", "landcover"])

**Available Layers:**
- `ndvi`: Normalized Difference Vegetation Index
- `ndbi`: Normalized Difference Built-up Index
- `ndwi`: Normalized Difference Water Index
- `elevation`: Digital Elevation Model (SRTM)
- `slope`: Terrain slope derived from elevation
- `landcover`: ESA WorldCover land classification
- `water_occurrence`: JRC Global Surface Water occurrence
- `rainfall`: CHIRPS annual precipitation
- `buildings`: Individual building analysis with Google Research Open Buildings
- `administrative`: **NEW!** Administrative boundaries analysis with FAO GAUL dataset
- `vegetation`: **NEW!** Comprehensive vegetation analysis with Sentinel-2 + MODIS integration

**Response Structure:**
```json
{
  "coordinates": [{"lat": 12.97, "long": 77.59}],
  "bhuvan": {},
  "kgis": {},
  "osm": {},
  "owm": {},
  "earth_engine": {
    "summary": {
      "ndvi_mean": 0.456,
      "elevation_mean": 920.5,
      "slope_mean": 3.2
    },
    "landcover_histogram": {
      "tree_cover": 25.5,
      "built_up": 45.2,
      "cropland": 20.1
    },
    "visuals": {
      "ndvi_url": "https://earthengine.googleapis.com/...",
      "elevation_url": "https://earthengine.googleapis.com/...",
      "true_color_url": "https://earthengine.googleapis.com/..."
    },
    "roi": {
      "center_lat": 12.97,
      "center_lon": 77.59,
      "buffer_meters": 750,
      "area_hectares": 17.67
    }
  },
  "report": {}
}
```

### Other Endpoints

- **GET** `/` - API information
- **GET** `/health` - Health check with Earth Engine connectivity test
- **GET** `/supported-layers` - List all available analysis layers

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py

# Run integration tests (requires Earth Engine setup)
pytest -m integration

# Run tests with verbose output
pytest -v
```

**Test Categories:**
- **Unit Tests**: Model validation, utility functions
- **API Tests**: Endpoint behavior, validation
- **Integration Tests**: Real Earth Engine calls (requires setup)

### Manual API Testing

#### **Comprehensive Vegetation Analysis**
```bash
# Test vegetation analysis with Delhi coordinates
curl -X POST "http://localhost:8000/analyze-location" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 28.6139,
    "longitude": 77.2090,
    "layers": ["vegetation"]
  }'
```

**Expected Response Structure:**
```json
{
  "vegetation": {
    "metrics": {
      "mean_ndvi": 0.093,
      "mean_evi": 0.419,
      "mean_savi": 0.075,
      "vegetation_health_index": 0.529,
      "data_source": "Combined Sentinel-2 and MODIS analysis"
    },
    "distribution": {
      "non_vegetated": 65.2,
      "low_vegetation": 22.1,
      "moderate_vegetation": 8.9,
      "dense_vegetation": 3.8
    },
    "visualization_urls": {
      "ndvi_map": "https://earthengine.googleapis.com/...",
      "evi_map": "https://earthengine.googleapis.com/...",
      "savi_map": "https://earthengine.googleapis.com/...",
      "health_map": "https://earthengine.googleapis.com/...",
      "classification_map": "https://earthengine.googleapis.com/..."
    }
  }
}
```

#### **Administrative Boundaries Analysis**
```bash
# Test administrative context for New York City
curl -X POST "http://localhost:8000/analyze-location" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "layers": ["administrative"]
  }'
```

#### **Multi-Layer Polygon Analysis**
```bash
# Comprehensive analysis with custom polygon
curl -X POST "http://localhost:8000/analyze-polygon" \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": [
      [-74.0059, 40.7128],
      [-74.0058, 40.7129],
      [-74.0057, 40.7127],
      [-74.0059, 40.7128]
    ],
    "layers": ["vegetation", "buildings", "administrative"]
  }'
```

#### **Available Analysis Layers**
| Layer | Description | Resolution | Coverage | Quality |
|-------|-------------|------------|----------|---------|
| `vegetation` | NDVI, EVI, SAVI with health metrics | 10m-250m | 🌍 Global | ⭐⭐⭐⭐⭐ |
| `administrative` | Country/state/district boundaries | Vector | 🌍 Global | ⭐⭐⭐⭐⭐ |
| `buildings` | Building footprints and density | 1m-10m | 🌆 Major regions | ⭐⭐⭐⭐ |
| `elevation` | Digital elevation model | 30m | 🌍 Global | ⭐⭐⭐⭐ |
| `landcover` | Land use classification | 10m | 🌍 Global | ⭐⭐⭐⭐ |
| `population` | Population density estimates | 100m | 🌍 Global | ⭐⭐⭐ |
| `water` | Water body detection | 30m | 🌍 Global | ⭐⭐⭐⭐ |
| `soil` | Soil properties and types | 250m | 🌍 Global | ⭐⭐⭐ |
| `climate` | Temperature and precipitation | 1km | 🌍 Global | ⭐⭐⭐ |
| `fires` | Active fire detection | 1km | 🌍 Global | ⭐⭐⭐ |
| `air_quality` | Air quality indicators | 1km | 🌆 Major regions | ⭐⭐ |

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GEE_SERVICE_ACCOUNT_EMAIL` | Service account email | Yes | - |
| `GEE_SERVICE_ACCOUNT_KEY_PATH` | Path to service account JSON | Yes* | `gee-sa.json` |
| `GEE_SERVICE_ACCOUNT_KEY_JSON` | Service account JSON as string | Yes* | - |

*Either `KEY_PATH` or `KEY_JSON` is required.

### Application Settings

- **Default Buffer**: 750 meters
- **India Bounds**: [68.0, 6.0, 97.0, 37.0] (west, south, east, north)
- **Image Resolution**: 30m for most datasets, 10m for Sentinel-2
- **Visualization Size**: 512x512 pixels

## 🌍 Dataset Information & Quality

### 🌱 **Vegetation Analysis Engine**
- **Primary Source**: Sentinel-2 MSI Level-2A (10m resolution)
  - Real-time cloud masking and atmospheric correction
  - Global coverage with 5-day revisit time
  - Optimal for detailed vegetation monitoring
- **Secondary Source**: MODIS Terra/Aqua Combined (250m resolution)  
  - 16-day composites for gap-filling and validation
  - Proven reliability for long-term vegetation trends
  - Excellent temporal consistency

**Vegetation Indices Computed:**
- **NDVI**: (NIR - Red) / (NIR + Red) - Standard vegetation health
- **EVI**: 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1) - Enhanced for dense vegetation
- **SAVI**: (NIR - Red) / (NIR + Red + 0.5) * 1.5 - Soil-adjusted for accurate readings

### 🏛️ **Administrative Boundaries**
- **Dataset**: FAO Global Administrative Unit Layers (GAUL)
- **Hierarchy**: 3-tier system (ADM0/Country → ADM1/State → ADM2/District)
- **Coverage**: 195+ countries with standardized coding
- **Quality**: Official boundaries maintained by UN FAO

### 🏢 **Building Intelligence**
- **Dataset**: Google Research Open Buildings
- **Resolution**: Sub-meter to 10m accuracy
- **Coverage**: 57+ countries and growing
- **Quality**: AI-detected footprints with confidence scores

## 🌍 India-Specific Features

- **Coordinate Validation**: Warns when coordinates are outside India bounds
- **Optimized Datasets**: Uses India-relevant satellite data
- **Regional Analysis**: Tailored for Indian geographic and climatic conditions
- **Multi-temporal**: Composite generation for cloud-free analysis

## 🚧 Future Enhancements

### 🎯 **Planned Features (Q1 2024)**
- **Temporal Analysis**: Multi-date vegetation change detection
- **Advanced Agriculture**: Crop classification and health monitoring  
- **Water Resources**: Detailed hydrology analysis with flow patterns
- **Urban Planning**: Building density trends and development analysis
- **Climate Insights**: Weather pattern analysis and predictions

### 🔬 **Technical Roadmap**
- **Machine Learning Integration**: AI-powered pattern recognition
- **Real-time Monitoring**: Live satellite data streaming
- **Custom Analysis**: User-defined algorithms and indices
- **Data Export**: GeoJSON, KML, and GeoTIFF downloads
- **Batch Processing**: Large-area analysis capabilities

### 🌐 **Platform Expansion**
- **Mobile Application**: Native iOS/Android apps
- **Desktop Client**: Electron-based desktop application
- **Cloud Deployment**: Multi-region hosting for global performance
- **Enterprise Features**: Team collaboration and project management
- **API Expansion**: GraphQL endpoints and webhook integrations

---

## 📈 Platform Statistics

| Metric | Current Status |
|--------|----------------|
| **Analysis Layers** | 11+ comprehensive datasets |
| **Vegetation Indices** | 5 specialized maps (NDVI, EVI, SAVI, Health, Classification) |
| **Administrative Coverage** | 195+ countries with 3-tier hierarchy |
| **Building Footprints** | 57+ countries with sub-meter accuracy |
| **API Endpoints** | 6 RESTful endpoints with automatic documentation |
| **Polygon Support** | ✅ All analysis types support custom boundaries |
| **Global Coverage** | ✅ Worldwide analysis capabilities |
| **Real-time Processing** | ⚡ Sub-minute response times |

---

### Phase 1 (Current)
- ✅ Core Earth Engine integration
- ✅ FastAPI endpoints
- ✅ Basic visualization

### Phase 2 (Planned)
- 🔄 **Database Integration**: Postgres/pgAdmin4 for result storage
- 🔄 **Additional APIs**: Bhuvan, KGIS, OpenStreetMap integration
- 🔄 **Weather Data**: OpenWeatherMap integration

### Phase 3 (Future)
- 📋 **AI Reporting**: LLM-powered analysis reports
- 📋 **PDF Export**: Automated report generation
- 📋 **Time Series**: Historical trend analysis
- 📋 **Advanced Analytics**: Machine learning insights

## 🐛 Troubleshooting

---

## 🛠️ **Troubleshooting Guide**

### **Common Setup Issues**

#### ❌ **Python/Virtual Environment Problems**

**Issue**: `cannot be loaded because running scripts is disabled`
```powershell
# Solution: Enable PowerShell script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Issue**: `python: command not found`
```powershell
# Solution: Add Python to PATH or use full path
# Check if Python is installed:
python --version
# If not found, reinstall Python with "Add to PATH" checked
```

**Issue**: Packages not found after installation
```powershell
# Solution: Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1
# Verify you're using venv Python:
which python  # Should show path to venv\Scripts\python.exe
```

#### ❌ **Earth Engine Authentication Errors**

**Issue**: `ModuleNotFoundError: No module named 'ee'`
```powershell
# Solution: Install Earth Engine in virtual environment
.\venv\Scripts\Activate.ps1
pip install earthengine-api
```

**Issue**: `HttpError 403: Earth Engine API has not been used`
```powershell
# Solution: Enable Earth Engine API in Google Cloud Console
# 1. Go to console.cloud.google.com
# 2. Search "Earth Engine API"
# 3. Click "Enable"
```

**Issue**: `Error: Unable to load private key`
```powershell
# Solution: Check service account setup
# 1. Ensure gee-sa.json exists in project folder
# 2. Verify JSON file is valid (open in text editor)
# 3. Check .env file has correct email and file path
```

**Issue**: `User does not have access to Earth Engine`
```powershell
# Solution: Register for Earth Engine
# 1. Go to earthengine.google.com
# 2. Sign up for noncommercial use  
# 3. Use same Google account as Cloud Console
```

#### ❌ **Server Issues**

**Issue**: `Port 8001 already in use`
```powershell
# Solution: Kill existing processes or use different port
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
# Or use different port:
uvicorn app.main:app --reload --port 8002
```

**Issue**: `CORS errors` in browser
```powershell
# Solution: Ensure proper server setup
# 1. Backend must run on localhost:8001
# 2. Use Live Server or HTTP server for frontend
# 3. Don't open HTML file directly (file:// URLs)
```

#### ❌ **Map Interface Issues**

**Issue**: Interactive map doesn't load
```
Solution: Check these steps:
1. Ensure backend server is running (localhost:8001)
2. Use Live Server or python -m http.server 8080
3. Don't open HTML file directly from file explorer
4. Check browser console (F12) for error messages
```

**Issue**: Analysis returns errors or no data
```
Solution: This is normal for some areas:
- Cloud cover may prevent satellite data
- Ocean areas have limited land data
- Try different locations (urban areas work best)
- Use smaller buffer sizes for testing
```

### **Verification Commands**

```powershell
# Test complete setup
.\venv\Scripts\Activate.ps1

# 1. Test Earth Engine
python -c "import ee; ee.Initialize(); print('✅ Earth Engine working')"

# 2. Test FastAPI
python -c "import fastapi, uvicorn; print('✅ FastAPI working')"

# 3. Test API endpoint
curl http://localhost:8001/health

# 4. Test basic analysis endpoint
curl -X POST "http://localhost:8001/analyze-location" -H "Content-Type: application/json" -d "{\"lat\": 12.9716, \"lon\": 77.5946, \"layers\": [\"ndvi\"]}"

# 5. Test comprehensive vegetation analysis (NEW!)
curl -X POST "http://localhost:8001/analyze-location" -H "Content-Type: application/json" -d "{\"lat\": 12.9716, \"lon\": 77.5946, \"buffer_m\": 1000, \"layers\": [\"vegetation\"]}"

# 6. Test administrative boundaries analysis (NEW!)
curl -X POST "http://localhost:8001/analyze-location" -H "Content-Type: application/json" -d "{\"lat\": 12.9716, \"lon\": 77.5946, \"buffer_m\": 1000, \"layers\": [\"administrative\"]}"

# 7. Test complete analysis with all new features
curl -X POST "http://localhost:8001/analyze-location" -H "Content-Type: application/json" -d "{\"lat\": 12.9716, \"lon\": 77.5946, \"buffer_m\": 1000, \"layers\": [\"ndvi\", \"elevation\", \"landcover\", \"buildings\", \"administrative\", \"vegetation\"]}"
```

### **Getting Help**

If you encounter issues:

1. **Check the error message** carefully
2. **Look in browser console** (F12) for frontend issues  
3. **Check terminal output** for backend errors
4. **Verify all prerequisites** are installed
5. **Try the verification commands** above

**Common URLs to check:**
- Backend API: http://localhost:8001
- API Documentation: http://localhost:8001/docs  
- Health Check: http://localhost:8001/health
- Interactive Map: http://localhost:8080/interactive_map.html

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Check the [Earth Engine documentation](https://developers.google.com/earth-engine)
- Review [FastAPI documentation](https://fastapi.tiangolo.com/)

## 🎯 **Quick Start Reference**

### **Essential Commands**

```powershell
# Navigate to project
cd "C:\Users\YourName\Desktop\gee-trial"

# Activate virtual environment  
.\venv\Scripts\Activate.ps1

# Start backend server
uvicorn app.main:app --reload --port 8001

# Start frontend server (alternative to Live Server)
python -m http.server 8080
```

### **Key URLs**

| Service | URL | Purpose |
|---------|-----|---------|
| **API Documentation** | http://localhost:8001/docs | Interactive API testing |
| **Health Check** | http://localhost:8001/health | Verify server status |
| **Interactive Map** | http://localhost:8080/interactive_map.html | Main application |
| **Backend API** | http://localhost:8001 | REST API endpoints |

### **Quick Test Commands**

```powershell
# Test API health
curl http://localhost:8001/health

# Test basic analysis  
curl -X POST "http://localhost:8001/analyze-location" `
  -H "Content-Type: application/json" `
  -d '{"lat": 12.9716, "lon": 77.5946, "layers": ["ndvi", "elevation"]}'

# Test building analysis
curl -X POST "http://localhost:8001/analyze-location" `
  -H "Content-Type: application/json" `
  -d '{"lat": 12.9716, "lon": 77.5946, "layers": ["buildings"]}'
```

---

## 📝 **Project Information**

### **File Structure**
```
gee-trial/
├── app/
│   ├── main.py           # FastAPI application & endpoints
│   ├── gee_utils.py      # Earth Engine processing functions
│   ├── models.py         # Data validation schemas
│   └── config.py         # Authentication & settings
├── interactive_map.html  # Interactive web interface
├── requirements.txt      # Python dependencies
├── .env                 # Environment configuration
├── gee-sa.json          # Service account credentials
└── README.md            # This documentation
```

### **Technology Stack**
- **Backend**: FastAPI + Python 3.8+
- **Earth Engine**: Google Earth Engine Python API
- **Frontend**: HTML5 + JavaScript + Leaflet.js
- **Visualization**: Chart.js for analytics
- **Authentication**: Google Cloud Service Account

### **Support & Resources**

- **Earth Engine Documentation**: [developers.google.com/earth-engine](https://developers.google.com/earth-engine)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)  
- **Google Cloud Console**: [console.cloud.google.com](https://console.cloud.google.com/)
- **GitHub Repository**: [github.com/TanmayCJ/tcjpr](https://github.com/TanmayCJ/tcjpr)

---

**🛰️ Built with ❤️ for India's geospatial intelligence community**

*This platform provides comprehensive satellite data analysis for urban planning, environmental monitoring, and building-level intelligence using cutting-edge Earth observation technologies.*