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
    
    def get_climate_data(self, lat: float, lon: float, radius: int = 5000) -> Dict:
        """
        Get climate data (precipitation, temperature) for transport risk assessment
        
        Args:
            lat: Latitude
            lon: Longitude
            radius: Radius in meters for analysis
            
        Returns:
            Dict with climate data and transport risk assessment
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
            
            # Date range - last 7 days for current conditions
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Get ERA5 climate data (temperature and precipitation)
            era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
            
            # Filter for recent data
            climate_data = (era5
                           .filterBounds(aoi)
                           .filterDate(start_date.strftime('%Y-%m-%d'),
                                     end_date.strftime('%Y-%m-%d')))
            
            # Get latest climate image
            latest_climate = climate_data.sort('system:time_start', False).first()
            
            if latest_climate.getInfo() is None:
                return {
                    "error": "No recent climate data available",
                    "location": {"lat": lat, "lon": lon}
                }
            
            # Calculate climate statistics
            climate_stats = latest_climate.select(['temperature_2m', 'total_precipitation']).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=11132,  # ERA5 native resolution ~11km
                maxPixels=1e9
            )
            
            # Get the results
            stats = climate_stats.getInfo()
            
            # Convert temperature from Kelvin to Celsius
            temp_celsius = stats.get('temperature_2m', 273.15) - 273.15
            precipitation_mm = stats.get('total_precipitation', 0) * 1000  # Convert m to mm
            
            # Calculate transport risk based on weather conditions
            risk_factors = []
            risk_level = "LOW"
            
            # Temperature-based risks
            if temp_celsius < -5:
                risk_factors.append("Extreme cold - ice formation risk")
                risk_level = "HIGH"
            elif temp_celsius < 0:
                risk_factors.append("Freezing conditions - frost risk")
                risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
            elif temp_celsius > 35:
                risk_factors.append("Extreme heat - transport delays")
                risk_level = "HIGH"
            
            # Precipitation-based risks
            if precipitation_mm > 20:
                risk_factors.append("Heavy precipitation - flooding risk")
                risk_level = "HIGH"
            elif precipitation_mm > 10:
                risk_factors.append("Moderate precipitation - road conditions")
                risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
            elif precipitation_mm > 5:
                risk_factors.append("Light precipitation - minor delays")
            
            # Overall risk assessment
            if not risk_factors:
                risk_factors.append("Favorable weather conditions")
            
            return {
                "success": True,
                "location": {"lat": lat, "lon": lon, "radius": radius},
                "acquisition_date": datetime.now().isoformat(),
                "climate": {
                    "temperature_celsius": round(temp_celsius, 1),
                    "precipitation_mm": round(precipitation_mm, 2),
                    "risk_level": risk_level,
                    "risk_factors": risk_factors
                },
                "transport_impact": self._assess_transport_impact(temp_celsius, precipitation_mm),
                "data_source": "ERA5 Climate Reanalysis"
            }
            
        except Exception as e:
            logger.error(f"Error getting climate data: {e}")
            return {"error": str(e)}
    
    def _assess_transport_impact(self, temp: float, precip: float) -> Dict:
        """Assess transport impact based on weather conditions"""
        
        # Base delay factor (1.0 = no delay)
        delay_factor = 1.0
        impact_description = "Normal conditions"
        
        # Temperature impacts
        if temp < -10:
            delay_factor += 0.5  # 50% longer travel time
            impact_description = "Severe cold - major delays expected"
        elif temp < 0:
            delay_factor += 0.2  # 20% longer
            impact_description = "Cold conditions - minor delays possible"
        elif temp > 40:
            delay_factor += 0.3  # 30% longer
            impact_description = "Extreme heat - equipment stress"
        elif temp > 35:
            delay_factor += 0.1  # 10% longer
            impact_description = "Hot conditions - reduced speeds"
        
        # Precipitation impacts
        if precip > 25:
            delay_factor += 0.6  # 60% longer
            impact_description = "Heavy rain/snow - significant delays"
        elif precip > 15:
            delay_factor += 0.3  # 30% longer
            impact_description = "Moderate precipitation - delays likely"
        elif precip > 5:
            delay_factor += 0.1  # 10% longer
            impact_description = "Light precipitation - minor impact"
        
        # Calculate estimated delay
        base_travel_time = 2.5  # hours (average for Swiss routes)
        estimated_time = base_travel_time * delay_factor
        delay_minutes = (estimated_time - base_travel_time) * 60
        
        return {
            "delay_factor": round(delay_factor, 2),
            "estimated_travel_time_hours": round(estimated_time, 1),
            "additional_delay_minutes": round(delay_minutes, 0),
            "impact_description": impact_description,
            "recommended_action": self._get_transport_recommendation(delay_factor, temp, precip)
        }
    
    def _get_transport_recommendation(self, delay_factor: float, temp: float, precip: float) -> str:
        """Get transport recommendations based on conditions"""
        
        if delay_factor > 1.4:
            return "Consider delaying shipment or using alternative routes"
        elif delay_factor > 1.2:
            return "Allow extra time and monitor conditions closely"
        elif delay_factor > 1.1:
            return "Minor delays expected, inform drivers"
        else:
            return "Normal transport operations"
    
    def get_route_climate_risk(self, start_lat: float, start_lon: float, 
                              end_lat: float, end_lon: float) -> Dict:
        """
        Get climate risk assessment for a specific route
        
        Args:
            start_lat, start_lon: Starting coordinates (supplier)
            end_lat, end_lon: Ending coordinates (Swiss Corp HQ)
            
        Returns:
            Dict with route-specific climate risk assessment
        """
        if not self.available:
            return {"error": "Google Earth Engine package not installed"}
            
        if not self.initialized:
            if not self.initialize():
                return {"error": "Google Earth Engine authentication failed"}
        
        try:
            # Sample points along the route (start, middle, end)
            mid_lat = (start_lat + end_lat) / 2
            mid_lon = (start_lon + end_lon) / 2
            
            route_points = [
                {"lat": start_lat, "lon": start_lon, "name": "Origin"},
                {"lat": mid_lat, "lon": mid_lon, "name": "Midpoint"},
                {"lat": end_lat, "lon": end_lon, "name": "Destination"}
            ]
            
            # Get climate data for each point
            route_climate = []
            max_risk_level = "LOW"
            all_risk_factors = []
            
            for point in route_points:
                climate_data = self.get_climate_data(point["lat"], point["lon"], 3000)
                if climate_data.get("success"):
                    route_climate.append({
                        "point": point["name"],
                        "coordinates": {"lat": point["lat"], "lon": point["lon"]},
                        "climate": climate_data["climate"],
                        "transport_impact": climate_data["transport_impact"]
                    })
                    
                    # Track highest risk level
                    risk_level = climate_data["climate"]["risk_level"]
                    if risk_level == "HIGH":
                        max_risk_level = "HIGH"
                    elif risk_level == "MEDIUM" and max_risk_level == "LOW":
                        max_risk_level = "MEDIUM"
                    
                    # Collect all risk factors
                    all_risk_factors.extend(climate_data["climate"]["risk_factors"])
            
            # Calculate route distance for context
            route_distance = self._calculate_distance(start_lat, start_lon, end_lat, end_lon)
            
            return {
                "success": True,
                "route": {
                    "start": {"lat": start_lat, "lon": start_lon},
                    "end": {"lat": end_lat, "lon": end_lon},
                    "distance_km": round(route_distance, 1)
                },
                "overall_risk": max_risk_level,
                "risk_factors": list(set(all_risk_factors)),  # Remove duplicates
                "route_points": route_climate,
                "recommendation": self._get_route_recommendation(max_risk_level, route_climate)
            }
            
        except Exception as e:
            logger.error(f"Error getting route climate risk: {e}")
            return {"error": str(e)}
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        from math import radians, sin, cos, asin, sqrt
        
        R = 6371.0  # Earth radius in km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))
    
    def _get_route_recommendation(self, risk_level: str, route_points: List[Dict]) -> str:
        """Get overall route recommendation"""
        
        if risk_level == "HIGH":
            return "High risk route - consider postponing or using alternative transport"
        elif risk_level == "MEDIUM":
            return "Moderate risk - allow extra time and monitor weather updates"
        else:
            return "Low risk route - normal operations expected"
    
    def get_traffic_data(self, start_lat: float, start_lon: float, 
                        end_lat: float, end_lon: float) -> Dict:
        """
        Get real-time traffic data for a route using Google Maps API
        
        Args:
            start_lat, start_lon: Starting coordinates
            end_lat, end_lon: Ending coordinates
            
        Returns:
            Dict with traffic conditions and delay information
        """
        try:
            import googlemaps
            
            # Get Google Maps API key from environment
            gmaps_key = os.getenv('GOOGLE_MAPS_API_KEY')
            if not gmaps_key:
                # Fallback to mock data if no API key
                return self._get_mock_traffic_data(start_lat, start_lon, end_lat, end_lon)
            
            gmaps = googlemaps.Client(key=gmaps_key)
            
            # Get directions with traffic
            directions = gmaps.directions(
                origin=(start_lat, start_lon),
                destination=(end_lat, end_lon),
                mode="driving",
                departure_time="now",  # For real-time traffic
                traffic_model="best_guess"
            )
            
            if not directions:
                return {"error": "No route found"}
            
            route = directions[0]
            leg = route['legs'][0]
            
            # Extract traffic information
            duration_normal = leg['duration']['value']  # seconds without traffic
            duration_traffic = leg.get('duration_in_traffic', {}).get('value', duration_normal)
            
            # Calculate delay
            delay_seconds = duration_traffic - duration_normal
            delay_minutes = delay_seconds / 60
            
            # Determine traffic level
            if delay_minutes > 30:
                traffic_level = "HEAVY"
                color = "#ef4444"  # Red
            elif delay_minutes > 10:
                traffic_level = "MODERATE" 
                color = "#f59e0b"  # Yellow
            else:
                traffic_level = "LIGHT"
                color = "#22c55e"  # Green
            
            return {
                "success": True,
                "route": {
                    "start": {"lat": start_lat, "lon": start_lon},
                    "end": {"lat": end_lat, "lon": end_lon},
                    "distance_km": leg['distance']['value'] / 1000
                },
                "traffic": {
                    "level": traffic_level,
                    "color": color,
                    "duration_normal_minutes": duration_normal / 60,
                    "duration_traffic_minutes": duration_traffic / 60,
                    "delay_minutes": delay_minutes,
                    "delay_percentage": (delay_minutes / (duration_normal / 60)) * 100 if duration_normal > 0 else 0
                },
                "recommendation": self._get_traffic_recommendation(traffic_level, delay_minutes),
                "data_source": "Google Maps Traffic API"
            }
            
        except ImportError:
            logger.warning("googlemaps package not installed. Using mock traffic data.")
            return self._get_mock_traffic_data(start_lat, start_lon, end_lat, end_lon)
        except Exception as e:
            logger.error(f"Error getting traffic data: {e}")
            return self._get_mock_traffic_data(start_lat, start_lon, end_lat, end_lon)
    
    def _get_mock_traffic_data(self, start_lat: float, start_lon: float, 
                              end_lat: float, end_lon: float) -> Dict:
        """Generate mock traffic data for testing"""
        import random
        
        # Use coordinates to seed for consistent results
        seed = int((start_lat + start_lon + end_lat + end_lon) * 1000) % 1000
        random.seed(seed)
        
        # Calculate approximate distance
        distance_km = self._calculate_distance(start_lat, start_lon, end_lat, end_lon)
        
        # Base travel time (assuming 60 km/h average)
        base_time_minutes = (distance_km / 60) * 60
        
        # Generate traffic delay
        delay_minutes = random.uniform(0, 45)
        
        # Determine traffic level
        if delay_minutes > 25:
            traffic_level = "HEAVY"
            color = "#ef4444"
        elif delay_minutes > 10:
            traffic_level = "MODERATE"
            color = "#f59e0b"
        else:
            traffic_level = "LIGHT"
            color = "#22c55e"
        
        return {
            "success": True,
            "route": {
                "start": {"lat": start_lat, "lon": start_lon},
                "end": {"lat": end_lat, "lon": end_lon},
                "distance_km": round(distance_km, 1)
            },
            "traffic": {
                "level": traffic_level,
                "color": color,
                "duration_normal_minutes": round(base_time_minutes, 1),
                "duration_traffic_minutes": round(base_time_minutes + delay_minutes, 1),
                "delay_minutes": round(delay_minutes, 1),
                "delay_percentage": round((delay_minutes / base_time_minutes) * 100, 1) if base_time_minutes > 0 else 0
            },
            "recommendation": self._get_traffic_recommendation(traffic_level, delay_minutes),
            "data_source": "Mock Traffic Data"
        }
    
    def _get_traffic_recommendation(self, traffic_level: str, delay_minutes: float) -> str:
        """Get traffic-based recommendations"""
        if traffic_level == "HEAVY":
            return f"Heavy traffic - consider delaying departure or alternative routes (+{delay_minutes:.0f} min delay)"
        elif traffic_level == "MODERATE":
            return f"Moderate traffic - allow extra time (+{delay_minutes:.0f} min delay)"
        else:
            return "Light traffic - normal travel time expected"

    def get_swiss_climate_heatmap(self, bounds: Dict) -> Dict:
        """
        Get climate heatmap tiles for the Swiss region
        
        Args:
            bounds: Dictionary with north, south, east, west coordinates
            
        Returns:
            Dict with climate heatmap tile URL and metadata
        """
        if not self.available:
            return {"error": "Google Earth Engine package not installed"}
            
        if not self.initialized:
            if not self.initialize():
                return {"error": "Google Earth Engine authentication failed"}
        
        try:
            # Define Swiss region
            swiss_bounds = ee.Geometry.Rectangle([
                bounds['west'], bounds['south'],
                bounds['east'], bounds['north']
            ])
            
            # Get recent ERA5 climate data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)  # Last 24 hours
            
            era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
            
            # Filter for recent data
            climate_data = (era5
                           .filterBounds(swiss_bounds)
                           .filterDate(start_date.strftime('%Y-%m-%d'),
                                     end_date.strftime('%Y-%m-%d')))
            
            # Get latest climate image
            latest_climate = climate_data.sort('system:time_start', False).first()
            
            if latest_climate.getInfo() is None:
                return {
                    "error": "No recent climate data available",
                    "bounds": bounds
                }
            
            # Create temperature visualization
            temp_vis = {
                'min': 250,  # -23°C in Kelvin
                'max': 320,  # 47°C in Kelvin
                'palette': ['blue', 'cyan', 'yellow', 'orange', 'red']
            }
            
            # Create precipitation visualization
            precip_vis = {
                'min': 0,
                'max': 0.01,  # 10mm in meters
                'palette': ['white', 'lightblue', 'blue', 'darkblue', 'purple']
            }
            
            # Generate temperature heatmap tiles
            temp_map_id = latest_climate.select('temperature_2m').getMapId(temp_vis)
            
            # Generate precipitation heatmap tiles
            precip_map_id = latest_climate.select('total_precipitation').getMapId(precip_vis)
            
            return {
                "success": True,
                "temperature_tiles": {
                    "url": temp_map_id['tile_fetcher'].url_format,
                    "attribution": "Temperature data from ERA5 via Google Earth Engine"
                },
                "precipitation_tiles": {
                    "url": precip_map_id['tile_fetcher'].url_format,
                    "attribution": "Precipitation data from ERA5 via Google Earth Engine"
                },
                "bounds": bounds,
                "timestamp": end_date.isoformat(),
                "data_source": "ERA5 Climate Reanalysis",
                "resolution": "~11km"
            }
            
        except Exception as e:
            logger.error(f"Error getting Swiss climate heatmap: {e}")
            return {"error": str(e)}

# Global client instance
gee_client = GEEClient()