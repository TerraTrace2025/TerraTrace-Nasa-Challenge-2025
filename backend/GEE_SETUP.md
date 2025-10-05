# Google Earth Engine Setup for Swiss Corp Satellite Integration

## 🛰️ Quick Setup Guide

### Step 1: Google Earth Engine Account
1. Go to: https://earthengine.google.com/
2. Click "Get Started" 
3. Sign up with your Google account
4. Request access (usually approved within 1-2 days)
5. Choose "Commercial" use case

### Step 2: Google Cloud Project Setup
1. Go to: https://console.cloud.google.com/
2. Create a new project: "swiss-corp-satellite"
3. Enable the Earth Engine API:
   - Go to APIs & Services > Library
   - Search for "Earth Engine API"
   - Click Enable

### Step 3: Service Account Creation
1. In Google Cloud Console, go to IAM & Admin > Service Accounts
2. Click "Create Service Account"
3. Name: "swiss-corp-gee-service"
4. Grant roles:
   - Earth Engine Resource Admin
   - Earth Engine Resource Viewer
5. Create and download JSON key file

### Step 4: Environment Variables
Set these environment variables:

```bash
# For development
export GEE_SERVICE_ACCOUNT_KEY='{"type": "service_account", "project_id": "your-project-id", ...}'
export GEE_PROJECT_ID='swiss-corp-satellite'

# Or create .env file in backend/
echo 'GEE_SERVICE_ACCOUNT_KEY={"type": "service_account", ...}' >> .env
echo 'GEE_PROJECT_ID=swiss-corp-satellite' >> .env
```

### Step 5: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 6: Test the Integration
```bash
# Start the backend
cd backend
python -m src.app

# Test satellite endpoints
curl http://localhost:8000/api/satellite/health
curl http://localhost:8000/api/satellite/ndvi/supplier/1
```

## 🗺️ Available Endpoints

### Health Check
```
GET /api/satellite/health
```

### Supplier NDVI Data
```
GET /api/satellite/ndvi/supplier/{supplier_id}?radius=1000&days_back=30
```

### NDVI Time Series
```
GET /api/satellite/ndvi/timeseries/supplier/{supplier_id}?months_back=6
```

### Swiss Region NDVI Overlay
```
GET /api/satellite/ndvi/region/swiss
```

### Point NDVI (Testing)
```
GET /api/satellite/ndvi/point?lat=47.3769&lon=8.5417&radius=1000
```

## 🎯 Swiss Corp Supplier Coverage

The system includes coordinates for all 10 Swiss Corp suppliers:

1. **Fenaco Genossenschaft** (Bern) - 46.9481°N, 7.4474°E
2. **Alpine Farms AG** (Thurgau) - 47.6062°N, 8.1090°E  
3. **Swiss Valley Produce** (Innsbruck) - 47.2692°N, 11.4041°E
4. **Organic Harvest Co** (Lucerne) - 47.0502°N, 8.3093°E
5. **Bavarian Grain Collective** (Munich) - 48.1351°N, 11.5820°E
6. **Rhône Valley Vineyards** (Geneva) - 46.2044°N, 6.1432°E
7. **Lombardy Agricultural Union** (Milan) - 45.4642°N, 9.1900°E
8. **Black Forest Organics** (Freiburg) - 48.0196°N, 7.8421°E
9. **Alsace Premium Produce** (Strasbourg) - 48.5734°N, 7.7521°E
10. **Tyrolean Mountain Farms** (Graz) - 47.0707°N, 15.4395°E

## 📊 Data Products

### NDVI (Normalized Difference Vegetation Index)
- **Range**: -1 to +1
- **Healthy Crops**: 0.7 - 1.0
- **Moderate**: 0.5 - 0.7
- **Stressed**: 0.3 - 0.5
- **Critical**: < 0.3

### Sentinel-2 Specifications
- **Resolution**: 10m per pixel
- **Revisit**: Every 2-3 days
- **Bands Used**: B4 (Red), B8 (NIR)
- **Cloud Filter**: < 20% cloud cover

## 🔧 Frontend Integration

The satellite data is integrated into the map when "Climate & Weather" toggle is enabled:

- **NDVI Circles**: Color-coded rings around suppliers
- **Satellite Overlay**: Regional vegetation imagery
- **Tooltips**: NDVI values and vegetation status
- **Real-time Updates**: Fresh data every 2-3 days

## 🚨 Troubleshooting

### "Google Earth Engine not available"
- Check if GEE_SERVICE_ACCOUNT_KEY is set correctly
- Verify the service account has Earth Engine permissions
- Ensure the project has Earth Engine API enabled

### "No recent Sentinel-2 data available"
- Try increasing days_back parameter
- Check if location is covered by Sentinel-2
- Verify cloud cover threshold (increase if needed)

### Rate Limits
- Free tier: 10,000 requests/day
- Batch multiple suppliers in single requests
- Cache results to reduce API calls

## 🌍 Next Steps

1. **Real-time Alerts**: Set up automated NDVI monitoring
2. **Historical Analysis**: 6-month trend analysis
3. **Crop-specific Thresholds**: Different NDVI ranges per crop type
4. **Weather Integration**: Combine with precipitation/temperature data

Your Swiss Corp platform now has **real NASA-quality satellite monitoring** for all suppliers! 🛰️🌾