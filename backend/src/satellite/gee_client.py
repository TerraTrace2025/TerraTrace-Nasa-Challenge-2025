"""
Google Earth Engine client for satellite data integration
"""
import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Optional Google Earth Engine import
try:
    import ee
    import pandas as pd
    GEE_AVAILABLE = True
except ImportError:
    ee = None
    pd = None
    GEE_AVAILABLE = False

logger = logging.getLogger(__name__)

class GEEClient:
    """Google Earth Engine client for Swiss Corp satellite data"""
    
    def __init__(self):
        self.initialized = False
        self.available = GEE_AVAILABLE
        self.service_account_key = os.getenv('GEE_SERVICE_ACCOUNT_KEY')
        self.project_id = os.getenv('GEE_PROJECT_ID', 'swiss-corp-satellite')
        
    def initialize(self) -> bool:
        """Initialize Google Earth Engine authentication"""
        if not self.available:
            logger.warning("Google Earth Engine package not available. Install with: pip install earthengine-api")
            return False
            
        try:
            if self.service_account_key:
                # Service account authentication (production)
                service_account_info = json.loads(self.service_account_key)
                credentials = ee.ServiceAccountCredentials(
                    service_account_info['client_email'],
                    key_data=self.service_account_key
                )
                ee.Initialize(credentials, project=self.project_id)
            else:
                # Try default authentication (development)
                ee.Initialize(project=self.project_id)
            
            # Test the connection
            ee.Number(1).getInfo()
            self.initialized = True
            logger.info("✅ Google Earth Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Earth Engine: {e}")
            self.initialized = False
            return False
    
    def get_sentinel2_ndvi(self, lat: float, lon: float, radius: int = 1000, 
                          days_back: int = 30) -> Dict:
        """
        Get Sentinel-2 NDVI data for a specific location
        
        Args:
            lat: Latitude
            lon: Longitude  
            radius: Radius in meters around the point
            days_back: Number of days to look back for data
            
        Returns:
            Dict with NDVI statistics and metadata
        """
        if not self.available:
            return {
                "error": "Google Earth Engine package not installed",
                "setup_required": "Run: pip install earthengine-api pandas",
                "documentation": "See backend/GEE_SETUP.md for complete setup instructions"
            }
            
        if not self.initialized:
            if not self.initialize():
                return {
                    "error": "Google Earth Engine authentication failed",
                    "setup_required": "Set GEE_SERVICE_ACCOUNT_KEY environment variable",
                    "documentation": "See backend/GEE_SETUP.md for authentication setup"
                }
        
        try:
            # Define the area of interest
            point = ee.Geometry.Point([lon, lat])
            aoi = point.buffer(radius)
            
            # Date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Sentinel-2 Surface Reflectance collection
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(aoi)
                         .filterDate(start_date.strftime('%Y-%m-%d'), 
                                   end_date.strftime('%Y-%m-%d'))
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
            
            # Function to calculate NDVI
            def calculate_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            # Apply NDVI calculation
            ndvi_collection = collection.map(calculate_ndvi)
            
            # Get the most recent image
            latest_image = ndvi_collection.sort('system:time_start', False).first()
            
            if latest_image.getInfo() is None:
                return {
                    "error": "No recent Sentinel-2 data available",
                    "location": {"lat": lat, "lon": lon},
                    "search_period": f"{start_date.date()} to {end_date.date()}"
                }
            
            # Calculate statistics
            ndvi_stats = latest_image.select('NDVI').reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.minMax(), sharedInputs=True
                ).combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=aoi,
                scale=10,  # 10m resolution
                maxPixels=1e9
            )
            
            # Get image metadata
            image_info = latest_image.getInfo()
            acquisition_date = datetime.fromtimestamp(
                image_info['properties']['system:time_start'] / 1000
            )
            
            # Get the results
            stats = ndvi_stats.getInfo()
            
            return {
                "success": True,
                "location": {"lat": lat, "lon": lon, "radius": radius},
                "acquisition_date": acquisition_date.isoformat(),
                "ndvi": {
                    "mean": round(stats.get('NDVI_mean', 0), 3),
                    "min": round(stats.get('NDVI_min', 0), 3),
                    "max": round(stats.get('NDVI_max', 0), 3),
                    "std": round(stats.get('NDVI_stdDev', 0), 3)
                },
                "cloud_cover": image_info['properties'].get('CLOUDY_PIXEL_PERCENTAGE', 0),
                "satellite": "Sentinel-2",
                "resolution": "10m"
            }
            
        except Exception as e:
            logger.error(f"Error getting Sentinel-2 NDVI: {e}")
            return {"error": str(e)}
    
    def get_ndvi_time_series(self, lat: float, lon: float, radius: int = 1000,
                            months_back: int = 6) -> Dict:
        """
        Get NDVI time series for trend analysis
        
        Args:
            lat: Latitude
            lon: Longitude
            radius: Radius in meters
            months_back: Number of months of historical data
            
        Returns:
            Dict with time series data
        """
        if not self.available:
            return {
                "error": "Google Earth Engine package not installed",
                "setup_required": "Run: pip install earthengine-api pandas"
            }
            
        if not self.initialized:
            if not self.initialize():
                return {
                    "error": "Google Earth Engine authentication failed",
                    "setup_required": "Set GEE_SERVICE_ACCOUNT_KEY environment variable"
                }
        
        try:
            # Define area of interest
            point = ee.Geometry.Point([lon, lat])
            aoi = point.buffer(radius)
            
            # Date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            
            # Sentinel-2 collection
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(aoi)
                         .filterDate(start_date.strftime('%Y-%m-%d'),
                                   end_date.strftime('%Y-%m-%d'))
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
            
            # Calculate NDVI for each image
            def calculate_ndvi_with_date(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return ndvi.set('system:time_start', image.get('system:time_start'))
            
            ndvi_collection = collection.map(calculate_ndvi_with_date)
            
            # Create monthly composites
            def create_monthly_composite(year_month):
                start = ee.Date(year_month)
                end = start.advance(1, 'month')
                monthly = ndvi_collection.filterDate(start, end)
                composite = monthly.median()
                return composite.set('system:time_start', start.millis())
            
            # Generate monthly dates
            months = []
            current = start_date.replace(day=1)
            while current <= end_date:
                months.append(current.strftime('%Y-%m-01'))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            
            # Create composites
            monthly_composites = ee.ImageCollection([
                create_monthly_composite(month) for month in months
            ])
            
            # Extract time series
            def extract_ndvi(image):
                stats = image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=aoi,
                    scale=10,
                    maxPixels=1e9
                )
                return ee.Feature(None, {
                    'date': image.get('system:time_start'),
                    'ndvi': stats.get('NDVI')
                })
            
            time_series = monthly_composites.map(extract_ndvi)
            
            # Get the results
            features = time_series.getInfo()['features']
            
            data = []
            for feature in features:
                props = feature['properties']
                if props['ndvi'] is not None:
                    date = datetime.fromtimestamp(props['date'] / 1000)
                    data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'ndvi': round(props['ndvi'], 3)
                    })
            
            return {
                "success": True,
                "location": {"lat": lat, "lon": lon, "radius": radius},
                "time_series": sorted(data, key=lambda x: x['date']),
                "period": f"{start_date.date()} to {end_date.date()}",
                "satellite": "Sentinel-2"
            }
            
        except Exception as e:
            logger.error(f"Error getting NDVI time series: {e}")
            return {"error": str(e)}
    
    def get_swiss_region_ndvi(self, bounds: Dict) -> Dict:
        """
        Get NDVI data for the entire Swiss region
        
        Args:
            bounds: Dictionary with north, south, east, west coordinates
            
        Returns:
            Dict with regional NDVI data and tile URL
        """
        if not self.initialized:
            if not self.initialize():
                return {"error": "Google Earth Engine not available"}
        
        try:
            # Define Swiss region
            swiss_bounds = ee.Geometry.Rectangle([
                bounds['west'], bounds['south'],
                bounds['east'], bounds['north']
            ])
            
            # Get recent Sentinel-2 data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=14)  # Last 2 weeks
            
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(swiss_bounds)
                         .filterDate(start_date.strftime('%Y-%m-%d'),
                                   end_date.strftime('%Y-%m-%d'))
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
            
            # Calculate NDVI
            def calculate_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return ndvi
            
            ndvi_collection = collection.map(calculate_ndvi)
            
            # Create median composite
            ndvi_composite = ndvi_collection.median()
            
            # Generate map tile URL
            vis_params = {
                'min': 0,
                'max': 1,
                'palette': ['red', 'yellow', 'green']
            }
            
            map_id = ndvi_composite.getMapId(vis_params)
            
            return {
                "success": True,
                "tile_url": map_id['tile_fetcher'].url_format,
                "bounds": bounds,
                "period": f"{start_date.date()} to {end_date.date()}",
                "visualization": vis_params,
                "satellite": "Sentinel-2 NDVI Composite"
            }
            
        except Exception as e:
            logger.error(f"Error getting Swiss region NDVI: {e}")
            return {"error": str(e)}

# Global client instance
gee_client = GEEClient()