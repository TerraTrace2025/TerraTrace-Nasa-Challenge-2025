"""
Satellite data API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.satellite.gee_client import gee_client
import logging
import random

logger = logging.getLogger(__name__)

def generate_mock_climate_data(supplier_id: int, coords: dict) -> dict:
    """Generate mock climate data when GEE service is unavailable"""
    
    # Set seed for consistent results
    random.seed(supplier_id * 42)
    
    # Generate realistic weather conditions for Central Europe
    temp = random.uniform(-5, 35)  # Temperature range
    precip = random.uniform(0, 30)  # Precipitation in mm
    
    # Determine risk level
    if (temp < -2 or temp > 32) or precip > 20:
        risk_level = "HIGH"
        impact = "Significant transport delays expected"
        delay_minutes = random.uniform(30, 60)
    elif (temp < 2 or temp > 28) or precip > 10:
        risk_level = "MEDIUM"
        impact = "Moderate transport delays possible"
        delay_minutes = random.uniform(10, 30)
    else:
        risk_level = "LOW"
        impact = "Normal transport conditions"
        delay_minutes = random.uniform(0, 10)
    
    # Risk factors
    risk_factors = []
    if temp < 0:
        risk_factors.append("Freezing conditions")
    elif temp > 30:
        risk_factors.append("High temperature")
    
    if precip > 15:
        risk_factors.append("Heavy precipitation")
    elif precip > 5:
        risk_factors.append("Moderate precipitation")
    
    if not risk_factors:
        risk_factors.append("Favorable weather conditions")
    
    return {
        "success": True,
        "location": {"lat": coords["lat"], "lon": coords["lon"], "radius": 5000},
        "acquisition_date": "2024-01-01T12:00:00",  # Mock timestamp
        "climate": {
            "risk_level": risk_level,
            "temperature_celsius": round(temp, 1),
            "precipitation_mm": round(precip, 2),
            "risk_factors": risk_factors
        },
        "transport_impact": {
            "delay_factor": round(1 + (delay_minutes / 120), 2),
            "estimated_travel_time_hours": round(2.5 + (delay_minutes / 60), 1),
            "additional_delay_minutes": round(delay_minutes, 0),
            "impact_description": impact,
            "recommended_action": f"Allow extra {delay_minutes:.0f} minutes for transport"
        },
        "supplier": {
            "id": supplier_id,
            "name": coords["name"],
            "coordinates": {"lat": coords["lat"], "lon": coords["lon"]}
        },
        "data_source": "Mock Climate Data (GEE service unavailable)"
    }

def generate_mock_traffic_data(supplier_id: int, coords: dict, destination: dict) -> dict:
    """Generate mock traffic data when traffic service is unavailable"""
    
    # Set seed for consistent results
    random.seed(supplier_id * 123)
    
    # Calculate approximate distance (simple formula)
    lat_diff = abs(coords["lat"] - destination["lat"])
    lon_diff = abs(coords["lon"] - destination["lon"])
    distance_km = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # Rough km conversion
    
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
            "start": {"lat": coords["lat"], "lon": coords["lon"]},
            "end": {"lat": destination["lat"], "lon": destination["lon"]},
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
        "recommendation": f"{traffic_level.title()} traffic - {delay_minutes:.0f} min delay expected",
        "supplier": {
            "id": supplier_id,
            "name": coords["name"]
        },
        "destination": "Swiss Corp HQ, Zurich",
        "data_source": "Mock Traffic Data (service unavailable)"
    }

router = APIRouter(prefix="/satellite", tags=["satellite"])

@router.get("/health")
def satellite_health():
    """Check if satellite services are available"""
    if gee_client.initialize():
        return {
            "status": "healthy",
            "service": "Google Earth Engine",
            "message": "Satellite data services are operational"
        }
    else:
        return {
            "status": "unavailable", 
            "service": "Google Earth Engine",
            "message": "Satellite data services are not available. Check GEE authentication."
        }

@router.get("/ndvi/supplier/{supplier_id}")
def get_supplier_ndvi(
    supplier_id: int,
    radius: int = Query(1000, description="Radius in meters around supplier location"),
    days_back: int = Query(30, description="Number of days to look back for data")
):
    """Get NDVI data for a specific supplier location"""
    
    # Swiss Corp supplier coordinates (from your existing data)
    supplier_coords = {
        1: {"lat": 46.9481, "lon": 7.4474, "name": "Fenaco Genossenschaft, Bern"},
        2: {"lat": 47.6062, "lon": 8.1090, "name": "Alpine Farms AG, Thurgau"},
        3: {"lat": 47.2692, "lon": 11.4041, "name": "Swiss Valley Produce, Innsbruck"},
        4: {"lat": 47.0502, "lon": 8.3093, "name": "Organic Harvest Co, Lucerne"},
        5: {"lat": 48.1351, "lon": 11.5820, "name": "Bavarian Grain Collective, Munich"},
        6: {"lat": 46.2044, "lon": 6.1432, "name": "Rhône Valley Vineyards, Geneva"},
        7: {"lat": 45.4642, "lon": 9.1900, "name": "Lombardy Agricultural Union, Milan"},
        8: {"lat": 48.0196, "lon": 7.8421, "name": "Black Forest Organics, Freiburg"},
        9: {"lat": 48.5734, "lon": 7.7521, "name": "Alsace Premium Produce, Strasbourg"},
        10: {"lat": 47.0707, "lon": 15.4395, "name": "Tyrolean Mountain Farms, Graz"}
    }
    
    if supplier_id not in supplier_coords:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    
    coords = supplier_coords[supplier_id]
    
    try:
        result = gee_client.get_sentinel2_ndvi(
            lat=coords["lat"],
            lon=coords["lon"], 
            radius=radius,
            days_back=days_back
        )
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        # Add supplier info to result
        result["supplier"] = {
            "id": supplier_id,
            "name": coords["name"],
            "coordinates": {"lat": coords["lat"], "lon": coords["lon"]}
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting NDVI for supplier {supplier_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ndvi/timeseries/supplier/{supplier_id}")
def get_supplier_ndvi_timeseries(
    supplier_id: int,
    radius: int = Query(1000, description="Radius in meters"),
    months_back: int = Query(6, description="Number of months of historical data")
):
    """Get NDVI time series for trend analysis"""
    
    supplier_coords = {
        1: {"lat": 46.9481, "lon": 7.4474, "name": "Fenaco Genossenschaft, Bern"},
        2: {"lat": 47.6062, "lon": 8.1090, "name": "Alpine Farms AG, Thurgau"},
        3: {"lat": 47.2692, "lon": 11.4041, "name": "Swiss Valley Produce, Innsbruck"},
        4: {"lat": 47.0502, "lon": 8.3093, "name": "Organic Harvest Co, Lucerne"},
        5: {"lat": 48.1351, "lon": 11.5820, "name": "Bavarian Grain Collective, Munich"},
        6: {"lat": 46.2044, "lon": 6.1432, "name": "Rhône Valley Vineyards, Geneva"},
        7: {"lat": 45.4642, "lon": 9.1900, "name": "Lombardy Agricultural Union, Milan"},
        8: {"lat": 48.0196, "lon": 7.8421, "name": "Black Forest Organics, Freiburg"},
        9: {"lat": 48.5734, "lon": 7.7521, "name": "Alsace Premium Produce, Strasbourg"},
        10: {"lat": 47.0707, "lon": 15.4395, "name": "Tyrolean Mountain Farms, Graz"}
    }
    
    if supplier_id not in supplier_coords:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    
    coords = supplier_coords[supplier_id]
    
    try:
        result = gee_client.get_ndvi_time_series(
            lat=coords["lat"],
            lon=coords["lon"],
            radius=radius,
            months_back=months_back
        )
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        result["supplier"] = {
            "id": supplier_id,
            "name": coords["name"]
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting NDVI time series for supplier {supplier_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ndvi/region/swiss")
def get_swiss_region_ndvi():
    """Get NDVI overlay for the entire Swiss region"""
    
    # Swiss bounding box
    swiss_bounds = {
        "north": 47.8,
        "south": 45.8, 
        "east": 10.5,
        "west": 5.9
    }
    
    try:
        result = gee_client.get_swiss_region_ndvi(swiss_bounds)
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Swiss region NDVI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ndvi/point")
def get_point_ndvi(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(1000, description="Radius in meters"),
    days_back: int = Query(30, description="Days to look back")
):
    """Get NDVI data for any point (for testing/exploration)"""
    
    try:
        result = gee_client.get_sentinel2_ndvi(lat, lon, radius, days_back)
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting point NDVI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/climate/supplier/{supplier_id}")
def get_supplier_climate(
    supplier_id: int,
    radius: int = Query(5000, description="Radius in meters for climate analysis")
):
    """Get climate data and transport risk for a specific supplier"""
    
    # Swiss Corp supplier coordinates
    supplier_coords = {
        1: {"lat": 46.9481, "lon": 7.4474, "name": "Fenaco Genossenschaft, Bern"},
        2: {"lat": 47.6062, "lon": 8.1090, "name": "Alpine Farms AG, Thurgau"},
        3: {"lat": 47.2692, "lon": 11.4041, "name": "Swiss Valley Produce, Innsbruck"},
        4: {"lat": 47.0502, "lon": 8.3093, "name": "Organic Harvest Co, Lucerne"},
        5: {"lat": 48.1351, "lon": 11.5820, "name": "Bavarian Grain Collective, Munich"},
        6: {"lat": 46.2044, "lon": 6.1432, "name": "Rhône Valley Vineyards, Geneva"},
        7: {"lat": 45.4642, "lon": 9.1900, "name": "Lombardy Agricultural Union, Milan"},
        8: {"lat": 48.0196, "lon": 7.8421, "name": "Black Forest Organics, Freiburg"},
        9: {"lat": 48.5734, "lon": 7.7521, "name": "Alsace Premium Produce, Strasbourg"},
        10: {"lat": 47.0707, "lon": 15.4395, "name": "Tyrolean Mountain Farms, Graz"}
    }
    
    if supplier_id not in supplier_coords:
        # Return a graceful response for unknown suppliers instead of 404
        return {
            "success": False,
            "error": f"Climate data not available for supplier {supplier_id}",
            "supplier": {"id": supplier_id, "name": f"Supplier {supplier_id}"},
            "message": "Climate monitoring only available for suppliers 1-10"
        }
    
    coords = supplier_coords[supplier_id]
    
    try:
        result = gee_client.get_climate_data(
            lat=coords["lat"],
            lon=coords["lon"],
            radius=radius
        )
        
        if "error" in result:
            # If GEE service fails, return mock data instead of error
            logger.warning(f"GEE climate service failed for supplier {supplier_id}: {result['error']}")
            return generate_mock_climate_data(supplier_id, coords)
        
        result["supplier"] = {
            "id": supplier_id,
            "name": coords["name"],
            "coordinates": {"lat": coords["lat"], "lon": coords["lon"]}
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting climate data for supplier {supplier_id}: {e}")
        # Return mock data instead of 500 error
        return generate_mock_climate_data(supplier_id, coords)

@router.get("/climate/route/{supplier_id}")
def get_route_climate_risk(supplier_id: int):
    """Get climate risk assessment for route from supplier to Swiss Corp HQ"""
    
    # Swiss Corp HQ coordinates
    swiss_corp_hq = {"lat": 47.3769, "lon": 8.5417}
    
    # Supplier coordinates
    supplier_coords = {
        1: {"lat": 46.9481, "lon": 7.4474, "name": "Fenaco Genossenschaft, Bern"},
        2: {"lat": 47.6062, "lon": 8.1090, "name": "Alpine Farms AG, Thurgau"},
        3: {"lat": 47.2692, "lon": 11.4041, "name": "Swiss Valley Produce, Innsbruck"},
        4: {"lat": 47.0502, "lon": 8.3093, "name": "Organic Harvest Co, Lucerne"},
        5: {"lat": 48.1351, "lon": 11.5820, "name": "Bavarian Grain Collective, Munich"},
        6: {"lat": 46.2044, "lon": 6.1432, "name": "Rhône Valley Vineyards, Geneva"},
        7: {"lat": 45.4642, "lon": 9.1900, "name": "Lombardy Agricultural Union, Milan"},
        8: {"lat": 48.0196, "lon": 7.8421, "name": "Black Forest Organics, Freiburg"},
        9: {"lat": 48.5734, "lon": 7.7521, "name": "Alsace Premium Produce, Strasbourg"},
        10: {"lat": 47.0707, "lon": 15.4395, "name": "Tyrolean Mountain Farms, Graz"}
    }
    
    if supplier_id not in supplier_coords:
        # Return a graceful response for unknown suppliers instead of 404
        return {
            "success": False,
            "error": f"Climate route data not available for supplier {supplier_id}",
            "supplier": {"id": supplier_id, "name": f"Supplier {supplier_id}"},
            "message": "Climate route monitoring only available for suppliers 1-10"
        }
    
    coords = supplier_coords[supplier_id]
    
    try:
        result = gee_client.get_route_climate_risk(
            start_lat=coords["lat"],
            start_lon=coords["lon"],
            end_lat=swiss_corp_hq["lat"],
            end_lon=swiss_corp_hq["lon"]
        )
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        result["supplier"] = {
            "id": supplier_id,
            "name": coords["name"]
        }
        result["destination"] = "Swiss Corp HQ, Zurich"
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting route climate risk for supplier {supplier_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/climate/heatmap/swiss")
def get_swiss_climate_heatmap():
    """Get climate heatmap overlay for the Swiss region"""
    
    if not gee_client.available:
        raise HTTPException(status_code=503, detail="Google Earth Engine not available")
    
    if not gee_client.initialized:
        if not gee_client.initialize():
            raise HTTPException(status_code=503, detail="Google Earth Engine authentication failed")
    
    try:
        # Swiss bounding box
        swiss_bounds = {
            "north": 47.8,
            "south": 45.8,
            "east": 10.5,
            "west": 5.9
        }
        
        # Get climate heatmap from GEE
        result = gee_client.get_swiss_climate_heatmap(swiss_bounds)
        
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Swiss climate heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/traffic/route/{supplier_id}")
def get_route_traffic(supplier_id: int):
    """Get real-time traffic data for route from supplier to Swiss Corp HQ"""
    
    # Swiss Corp HQ coordinates
    swiss_corp_hq = {"lat": 47.3769, "lon": 8.5417}
    
    # Supplier coordinates
    supplier_coords = {
        1: {"lat": 46.9481, "lon": 7.4474, "name": "Fenaco Genossenschaft, Bern"},
        2: {"lat": 47.6062, "lon": 8.1090, "name": "Alpine Farms AG, Thurgau"},
        3: {"lat": 47.2692, "lon": 11.4041, "name": "Swiss Valley Produce, Innsbruck"},
        4: {"lat": 47.0502, "lon": 8.3093, "name": "Organic Harvest Co, Lucerne"},
        5: {"lat": 48.1351, "lon": 11.5820, "name": "Bavarian Grain Collective, Munich"},
        6: {"lat": 46.2044, "lon": 6.1432, "name": "Rhône Valley Vineyards, Geneva"},
        7: {"lat": 45.4642, "lon": 9.1900, "name": "Lombardy Agricultural Union, Milan"},
        8: {"lat": 48.0196, "lon": 7.8421, "name": "Black Forest Organics, Freiburg"},
        9: {"lat": 48.5734, "lon": 7.7521, "name": "Alsace Premium Produce, Strasbourg"},
        10: {"lat": 47.0707, "lon": 15.4395, "name": "Tyrolean Mountain Farms, Graz"}
    }
    
    if supplier_id not in supplier_coords:
        # Return a graceful response for unknown suppliers instead of 404
        return {
            "success": False,
            "error": f"Traffic data not available for supplier {supplier_id}",
            "supplier": {"id": supplier_id, "name": f"Supplier {supplier_id}"},
            "message": "Traffic monitoring only available for suppliers 1-10"
        }
    
    coords = supplier_coords[supplier_id]
    
    try:
        result = gee_client.get_traffic_data(
            start_lat=coords["lat"],
            start_lon=coords["lon"],
            end_lat=swiss_corp_hq["lat"],
            end_lon=swiss_corp_hq["lon"]
        )
        
        if "error" in result:
            # If traffic service fails, return mock data instead of error
            logger.warning(f"Traffic service failed for supplier {supplier_id}: {result['error']}")
            return generate_mock_traffic_data(supplier_id, coords, swiss_corp_hq)
        
        result["supplier"] = {
            "id": supplier_id,
            "name": coords["name"]
        }
        result["destination"] = "Swiss Corp HQ, Zurich"
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting traffic data for supplier {supplier_id}: {e}")
        # Return mock data instead of 500 error
        return generate_mock_traffic_data(supplier_id, coords, swiss_corp_hq)