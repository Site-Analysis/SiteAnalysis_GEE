# Flood Risk Scoring Bug Fixes

## Issue Identified
User reported that flood risk scoring was inaccurate - placing a marker in the ocean showed `historical_risk` as 100% when it should be 0 or very low.

## Root Causes

### 1. **Rainfall Score Overflow** (Line 2112)
```python
# BEFORE - BROKEN:
rainfall_score = min(rainfall / 50, 30)  # Max 30 points from rainfall
```

**Problem**: The `rainfall` parameter is the 30-year precipitation sum in millimeters, which can be 25,000+ mm for typical locations. Dividing 25,000 by 50 = 500, which always maxes out at 30 points. This meant almost every location got maximum rainfall risk score.

### 2. **Ocean/Permanent Water Misclassification** (Line 2111)
```python
# BEFORE - BROKEN:
recurrence_score = min(recurrence * 3, 30)  # Max 30 points from recurrence
```

**Problem**: The `recurrence` value from JRC Global Surface Water represents the percentage of months with water present. For oceans and permanent water bodies, this is ~100%, giving 100 * 3 = 300 → capped at 30 points. The algorithm didn't distinguish between:
- **Permanent water bodies** (ocean, lakes) - not flood risk
- **Seasonal flooding** (river floodplains) - actual flood risk

### 3. **Elevation Scoring Too Sensitive** (Line 2184)
```python
# BEFORE - BROKEN:
elev_score = max(0, 100 - (mean_elev / 10))
```

**Problem**: Any elevation below 1000m received a risk score > 0, which is unrealistic. Mountains at 500m elevation shouldn't have flood risk.

## Fixes Applied

### 1. **Fixed Rainfall Scoring** (Lines 2119-2133)
```python
# AFTER - FIXED:
annual_rainfall = rainfall / 30  # Convert 30-year sum to annual average

# Typical flood-prone: >2000mm/year
# Moderate: 1000-2000mm/year
# Low: <1000mm/year
if annual_rainfall > 2500:
    rainfall_score = 30
elif annual_rainfall > 2000:
    rainfall_score = 25
elif annual_rainfall > 1500:
    rainfall_score = 20
elif annual_rainfall > 1000:
    rainfall_score = 15
elif annual_rainfall > 500:
    rainfall_score = 10
else:
    rainfall_score = 5
```

**Fix**: Convert 30-year sum to annual average, then use realistic thresholds based on global flood risk patterns.

### 2. **Fixed Water Recurrence Scoring** (Lines 2114-2127)
```python
# AFTER - FIXED:
if recurrence > 90:
    # Permanent water body (ocean, lake) = not flood risk for land
    recurrence_score = 0
elif recurrence > 50:
    # Highly seasonal water = high flood risk
    recurrence_score = 30
elif recurrence > 10:
    # Moderate seasonal flooding
    recurrence_score = recurrence * 0.6  # Scale 10-50% to 6-30 points
else:
    # Occasional flooding
    recurrence_score = recurrence * 2  # Scale 0-10% to 0-20 points
```

**Fix**: Added logic to detect permanent water bodies (>90% recurrence) and assign 0 risk. For actual flood-prone areas, scaled scoring based on seasonal flooding patterns.

### 3. **Fixed Elevation Scoring** (Lines 2177-2204)
```python
# AFTER - FIXED:
if mean_elev < -10:
    # Deep ocean - not flood risk for land development
    return 0

# Elevation-based scoring with realistic thresholds:
# Sea level to 10m = Very High Risk (100 points)
# 10-50m = High Risk (60-100 points)
# 50-100m = Moderate Risk (30-60 points)
# 100-200m = Low Risk (10-30 points)
# >200m = Very Low Risk (0-10 points)
if mean_elev < 10:
    elev_score = 100
elif mean_elev < 50:
    elev_score = 100 - ((mean_elev - 10) / 40 * 40)  # 100 to 60
elif mean_elev < 100:
    elev_score = 60 - ((mean_elev - 50) / 50 * 30)  # 60 to 30
elif mean_elev < 200:
    elev_score = 30 - ((mean_elev - 100) / 100 * 20)  # 30 to 10
else:
    elev_score = max(0, 10 - ((mean_elev - 200) / 300 * 10))  # 10 to 0
```

**Fix**: Added ocean detection (<-10m elevation) and realistic elevation-based risk thresholds. Only areas below 200m have significant flood risk.

### 4. **Fixed Hydrology Scoring** (Lines 2219-2252)
```python
# AFTER - FIXED:
# Handle permanent water bodies (oceans, large lakes)
if water_occ > 95:
    # This is a permanent water body (ocean/lake), not flood-prone land
    return 0

# Water occurrence scoring (for non-permanent water)
# 0-10% = Low risk (occasional water)
# 10-30% = Moderate risk (seasonal flooding)
# 30-70% = High risk (frequent flooding)
# 70-95% = Very high risk (nearly permanent water)
```

**Fix**: Added detection for permanent water bodies (>95% water occurrence) and assigned 0 risk. For actual flood-prone land, scaled scoring based on flooding frequency.

## Expected Results After Fix

### Ocean Locations (e.g., middle of Pacific Ocean)
- **Elevation Risk**: 0 (negative elevation detected as ocean)
- **Hydrology Risk**: 0 (>95% water occurrence = permanent water body)
- **Historical Risk**: 0 (>90% recurrence = ocean, not flood risk)
- **LLAI Risk**: ~0 (low-lying but classified correctly)
- **Overall Score**: 0-5 → **Very Low Risk** ✅

### Coastal Floodplain (e.g., Bangladesh delta)
- **Elevation Risk**: 80-100 (near sea level)
- **Hydrology Risk**: 60-80 (near rivers, seasonal water)
- **Historical Risk**: 40-60 (multiple flood events, seasonal flooding)
- **LLAI Risk**: 60-80 (extensive low-lying areas)
- **Overall Score**: 60-80 → **High to Very High Risk** ✅

### Mountain Location (e.g., Himalayas at 2000m)
- **Elevation Risk**: 0-5 (high elevation)
- **Hydrology Risk**: 10-20 (far from major rivers)
- **Historical Risk**: 0-10 (no flood history)
- **LLAI Risk**: 0-5 (no low-lying areas)
- **Overall Score**: 5-15 → **Very Low Risk** ✅

## Testing Recommendations

Test the updated scoring with these diverse locations:

1. **Ocean** (0°, 0°) - Should show Very Low risk
2. **Coastal City** (Mumbai, India) - Should show High risk
3. **River Delta** (Bangladesh) - Should show Very High risk
4. **Desert** (Sahara) - Should show Very Low risk
5. **Mountains** (Himalayas) - Should show Very Low risk
6. **Floodplain** (Ganges River plains) - Should show Moderate to High risk

## Server Status
- ✅ Backend restarted on port 8000
- ✅ Frontend running on port 8001
- ✅ Changes applied to `app/gee_utils.py`

## Next Steps
1. Test with ocean location again (should now show 0-5% risk)
2. Test with known flood-prone area (should show 60-80% risk)
3. Validate all 4 risk components display correctly
4. Verify PDF report generation includes accurate scores
