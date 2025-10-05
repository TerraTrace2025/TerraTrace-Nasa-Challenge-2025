import os
import logging
import json
import math
import requests
import pandas as pd
import datetime as dt
from typing import Any, Dict, List, Optional
from math import radians, sin, cos, asin, sqrt
from dash.dependencies import ALL, MATCH

import plotly.graph_objects as go
import plotly.express as px

from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash

# OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not installed. Install with: pip install openai")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("food_waste_frontend")

CARD_STYLE = {"width": "400px", "margin": "auto", "marginTop": "150px", "padding": "20px"}
CONTAINER_STYLE = {"height": "100vh", "overflow": "hidden", "padding": "0"}

# ----------------------------
# Config
# ----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
USE_OSRM = os.getenv("USE_OSRM", "true").lower() == "true"
REFRESH_MS = int(os.getenv("REFRESH_MS", "30000"))  # 30s
DEFAULT_COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))
APP_PORT = int(os.getenv("PORT", "8051"))

# Simple cache for API data to avoid repeated calls
_API_CACHE = {}
_CACHE_TIMEOUT = 300  # 5 minutes

# ----------------------------
# RAG Knowledge Base for Risk Indicators
# ----------------------------
RAG_KNOWLEDGE_BASE = {
    "agriculture_risk": {
        "overview": "Agricultural risk assessment uses NDVI (Normalized Difference Vegetation Index) satellite data to monitor crop health across supplier locations.",
        "metrics": {
            "ndvi_ranges": {
                "healthy": {"range": "> 0.7", "color": "green", "description": "Excellent crop health, optimal growing conditions"},
                "moderate": {"range": "0.5 - 0.7", "color": "yellow", "description": "Moderate crop health, some stress indicators"},
                "stressed": {"range": "0.3 - 0.5", "color": "orange", "description": "Crop stress detected, potential yield reduction"},
                "critical": {"range": "< 0.3", "color": "red", "description": "Severe crop stress, significant yield impact expected"}
            },
            "factors": [
                "Drought conditions affecting vegetation growth",
                "Excessive rainfall causing waterlogging",
                "Temperature extremes impacting crop development",
                "Pest and disease pressure on crops",
                "Soil quality and nutrient availability"
            ]
        },
        "suppliers": {
            "1": {"name": "Fenaco Genossenschaft", "location": "Bern, Switzerland", "ndvi": 0.75, "status": "healthy", "risk_factors": ["Stable weather conditions", "Good soil moisture"], "crops": ["grains", "dairy"]},
            "2": {"name": "Alpine Farms AG", "location": "Thurgau, Switzerland", "ndvi": 0.45, "status": "stressed", "risk_factors": ["Alpine climate challenges", "Short growing season"], "crops": ["potatoes", "vegetables"]},
            "3": {"name": "Swiss Valley Produce", "location": "Innsbruck, Austria", "ndvi": 0.68, "status": "healthy", "risk_factors": ["Seasonal variations", "Mountain agriculture"], "crops": ["corn", "vegetables"]},
            "4": {"name": "Organic Harvest Co", "location": "Lucerne, Switzerland", "ndvi": 0.25, "status": "critical", "risk_factors": ["Severe drought", "Organic pest management challenges"], "crops": ["soybeans", "organic produce"]},
            "5": {"name": "Bavarian Grain Collective", "location": "Munich, Germany", "ndvi": 0.72, "status": "healthy", "risk_factors": ["Stable continental climate", "Good infrastructure"], "crops": ["grains", "corn"]},
            "6": {"name": "Rhône Valley Vineyards", "location": "Geneva, Switzerland", "ndvi": 0.82, "status": "healthy", "risk_factors": ["Optimal grape growing conditions", "Surplus harvest"], "crops": ["grapes", "wine"]},
            "7": {"name": "Lombardy Agricultural Union", "location": "Milan, Italy", "ndvi": 0.42, "status": "stressed", "risk_factors": ["Flooding concerns", "Heavy rainfall"], "crops": ["rice", "dairy"]},
            "8": {"name": "Black Forest Organics", "location": "Freiburg, Germany", "ndvi": 0.69, "status": "healthy", "risk_factors": ["Forest microclimate benefits", "Organic certification"], "crops": ["organic vegetables", "herbs"]},
            "9": {"name": "Alsace Premium Produce", "location": "Strasbourg, France", "ndvi": 0.58, "status": "moderate", "risk_factors": ["Seasonal weather variations", "Cross-border logistics"], "crops": ["wine grapes", "specialty produce"]},
            "10": {"name": "Tyrolean Mountain Farms", "location": "Graz, Austria", "ndvi": 0.35, "status": "stressed", "risk_factors": ["High altitude conditions", "Temperature fluctuations"], "crops": ["dairy", "mountain herbs"]}
        },
        "recommendations": {
            "healthy": "Continue current practices, monitor for changes",
            "moderate": "Increase monitoring frequency, prepare contingency plans",
            "stressed": "Implement water management strategies, consider alternative suppliers",
            "critical": "Immediate action required, diversify supply sources"
        }
    },
    "climate_risk": {
        "overview": "Climate risk assessment evaluates weather-related transport disruptions and supply chain impacts based on real-time meteorological data.",
        "metrics": {
            "risk_levels": {
                "low": {"description": "Normal weather conditions, minimal transport delays", "color": "green"},
                "medium": {"description": "Moderate weather impact, some delays expected", "color": "yellow"},
                "high": {"description": "Severe weather conditions, significant disruptions", "color": "red"}
            },
            "weather_factors": [
                "Temperature extremes affecting transport efficiency",
                "Precipitation levels impacting road conditions",
                "Wind speeds affecting logistics operations",
                "Seasonal weather patterns",
                "Climate change adaptation requirements"
            ]
        },
        "suppliers": {
            "1": {"name": "Fenaco Genossenschaft", "temp": 15, "precip": 2.5, "risk": "low", "impact": "Minimal delays expected", "forecast": "Stable conditions next 7 days"},
            "2": {"name": "Alpine Farms AG", "temp": 8, "precip": 15.2, "risk": "medium", "impact": "Mountain weather affecting transport", "forecast": "Snow possible, monitor conditions"},
            "3": {"name": "Swiss Valley Produce", "temp": 12, "precip": 8.1, "risk": "low", "impact": "Normal operations", "forecast": "Clear weather expected"},
            "4": {"name": "Organic Harvest Co", "temp": 18, "precip": 0.8, "risk": "medium", "impact": "Drought conditions affecting crops", "forecast": "No rain forecast, drought continues"},
            "5": {"name": "Bavarian Grain Collective", "temp": 16, "precip": 5.2, "risk": "low", "impact": "Good transport conditions", "forecast": "Mild weather continuing"},
            "6": {"name": "Rhône Valley Vineyards", "temp": 19, "precip": 3.1, "risk": "low", "impact": "Optimal harvest conditions", "forecast": "Perfect weather for harvest"},
            "7": {"name": "Lombardy Agricultural Union", "temp": 22, "precip": 45.8, "risk": "high", "impact": "Heavy rainfall disrupting logistics", "forecast": "Storms continuing, flooding risk"},
            "8": {"name": "Black Forest Organics", "temp": 14, "precip": 12.3, "risk": "medium", "impact": "Moderate rainfall, some delays", "forecast": "Rain tapering off"},
            "9": {"name": "Alsace Premium Produce", "temp": 12, "precip": 8.7, "risk": "medium", "impact": "Seasonal weather variations", "forecast": "Variable conditions"},
            "10": {"name": "Tyrolean Mountain Farms", "temp": 6, "precip": 18.5, "risk": "high", "impact": "Alpine weather disrupting dairy operations", "forecast": "Cold front approaching"}
        },
        "seasonal_patterns": {
            "winter": "Increased transport delays due to snow and ice conditions",
            "spring": "Flooding risks in certain regions affecting logistics",
            "summer": "Heat waves impacting perishable goods transport",
            "autumn": "Storm systems causing temporary disruptions"
        }
    },
    "transport_risk": {
        "overview": "Transport risk assessment monitors real-time traffic conditions, route efficiency, and logistics performance across the supply network.",
        "metrics": {
            "traffic_levels": {
                "light": {"delay": "0-5 minutes", "color": "green", "description": "Optimal transport conditions"},
                "moderate": {"delay": "5-15 minutes", "color": "yellow", "description": "Some congestion, minor delays"},
                "heavy": {"delay": "15+ minutes", "color": "red", "description": "Significant traffic delays"}
            },
            "transport_modes": [
                "Truck transport - most flexible but weather dependent",
                "Rail transport - more reliable but limited routes",
                "Combined transport - optimal for long distances"
            ]
        },
        "suppliers": {
            "1": {"name": "Fenaco Genossenschaft", "traffic": "light", "delay": 3, "route": "Bern-Zurich corridor", "transport_modes": ["truck", "train"], "reliability": "95%"},
            "2": {"name": "Alpine Farms AG", "traffic": "moderate", "delay": 12, "route": "Mountain routes with seasonal challenges", "transport_modes": ["truck"], "reliability": "87%"},
            "3": {"name": "Swiss Valley Produce", "traffic": "light", "delay": 8, "route": "Innsbruck-Zurich via A12", "transport_modes": ["truck", "train"], "reliability": "92%"},
            "4": {"name": "Organic Harvest Co", "traffic": "moderate", "delay": 15, "route": "Lucerne-Zurich direct", "transport_modes": ["truck"], "reliability": "78%"},
            "5": {"name": "Bavarian Grain Collective", "traffic": "heavy", "delay": 25, "route": "Munich-Zurich via A8 autobahn", "transport_modes": ["truck", "train"], "reliability": "82%"},
            "6": {"name": "Rhône Valley Vineyards", "traffic": "light", "delay": 5, "route": "Geneva-Zurich via A1", "transport_modes": ["truck"], "reliability": "94%"},
            "7": {"name": "Lombardy Agricultural Union", "traffic": "moderate", "delay": 18, "route": "Milan-Zurich via Gotthard", "transport_modes": ["truck", "train"], "reliability": "85%"},
            "8": {"name": "Black Forest Organics", "traffic": "light", "delay": 7, "route": "Freiburg-Zurich via A3", "transport_modes": ["truck"], "reliability": "91%"},
            "9": {"name": "Alsace Premium Produce", "traffic": "moderate", "delay": 14, "route": "Strasbourg-Zurich via A4", "transport_modes": ["truck", "train"], "reliability": "88%"},
            "10": {"name": "Tyrolean Mountain Farms", "traffic": "heavy", "delay": 22, "route": "Graz-Zurich via A9/A1", "transport_modes": ["truck"], "reliability": "79%"}
        },
        "optimization_strategies": [
            "Dynamic route planning based on real-time traffic",
            "Multi-modal transport combinations",
            "Strategic warehouse positioning",
            "Predictive analytics for demand forecasting"
        ]
    },
    "supplier_directory": {
        # Switzerland (8 suppliers)
        "1": {"name": "Fenaco Genossenschaft", "location": "Bern, Switzerland", "tier": "SURPLUS", "specialties": ["grains", "dairy"], "capacity": "high", "contract_type": "long-term"},
        "2": {"name": "Alpine Farms AG", "location": "Thurgau, Switzerland", "tier": "RISK", "specialties": ["potatoes", "vegetables"], "capacity": "medium", "contract_type": "seasonal"},
        "4": {"name": "Organic Harvest Co", "location": "Lucerne, Switzerland", "tier": "HIGHRISK", "specialties": ["soybeans", "organic produce"], "capacity": "low", "contract_type": "premium"},
        "6": {"name": "Rhône Valley Vineyards", "location": "Geneva, Switzerland", "tier": "SURPLUS", "specialties": ["grapes", "wine"], "capacity": "medium", "contract_type": "seasonal"},
        "11": {"name": "Valais Mountain Dairy", "location": "Sion, Switzerland", "tier": "SURPLUS", "specialties": ["dairy", "cheese"], "capacity": "medium", "contract_type": "long-term"},
        "12": {"name": "Graubünden Organic", "location": "Chur, Switzerland", "tier": "STABLE", "specialties": ["organic vegetables", "herbs"], "capacity": "medium", "contract_type": "premium"},
        "13": {"name": "Ticino Vineyards", "location": "Lugano, Switzerland", "tier": "SURPLUS", "specialties": ["wine", "grapes"], "capacity": "medium", "contract_type": "seasonal"},
        "14": {"name": "Jura Cheese Collective", "location": "Delémont, Switzerland", "tier": "STABLE", "specialties": ["cheese", "dairy"], "capacity": "medium", "contract_type": "specialty"},
        
        # Germany (12 suppliers)
        "5": {"name": "Bavarian Grain Collective", "location": "Munich, Germany", "tier": "SURPLUS", "specialties": ["grains", "corn"], "capacity": "very high", "contract_type": "bulk"},
        "8": {"name": "Black Forest Organics", "location": "Freiburg, Germany", "tier": "SURPLUS", "specialties": ["organic vegetables", "herbs"], "capacity": "medium", "contract_type": "premium"},
        "15": {"name": "Baden-Württemberg Farms", "location": "Stuttgart, Germany", "tier": "SURPLUS", "specialties": ["vegetables", "grains"], "capacity": "high", "contract_type": "long-term"},
        "16": {"name": "Rhineland Produce", "location": "Cologne, Germany", "tier": "STABLE", "specialties": ["vegetables", "fruits"], "capacity": "high", "contract_type": "long-term"},
        "17": {"name": "Swabian Grain Co", "location": "Augsburg, Germany", "tier": "SURPLUS", "specialties": ["grains", "cereals"], "capacity": "very high", "contract_type": "bulk"},
        "18": {"name": "Allgäu Dairy Union", "location": "Kempten, Germany", "tier": "RISK", "specialties": ["dairy", "cheese"], "capacity": "high", "contract_type": "long-term"},
        "19": {"name": "Franconian Organics", "location": "Nuremberg, Germany", "tier": "STABLE", "specialties": ["organic produce", "grains"], "capacity": "medium", "contract_type": "premium"},
        "20": {"name": "Lake Constance Fruits", "location": "Konstanz, Germany", "tier": "SURPLUS", "specialties": ["fruits", "vegetables"], "capacity": "medium", "contract_type": "seasonal"},
        "21": {"name": "Hessian Grain Mills", "location": "Frankfurt, Germany", "tier": "STABLE", "specialties": ["grains", "flour"], "capacity": "high", "contract_type": "bulk"},
        "22": {"name": "Palatinate Vineyards", "location": "Mannheim, Germany", "tier": "SURPLUS", "specialties": ["wine", "grapes"], "capacity": "medium", "contract_type": "seasonal"},
        "23": {"name": "Thuringian Vegetables", "location": "Erfurt, Germany", "tier": "RISK", "specialties": ["vegetables", "herbs"], "capacity": "medium", "contract_type": "seasonal"},
        "24": {"name": "Saxon Specialty Foods", "location": "Dresden, Germany", "tier": "STABLE", "specialties": ["specialty produce", "organic"], "capacity": "medium", "contract_type": "premium"},
        
        # Austria (10 suppliers)
        "3": {"name": "Swiss Valley Produce", "location": "Innsbruck, Austria", "tier": "SURPLUS", "specialties": ["corn", "vegetables"], "capacity": "high", "contract_type": "long-term"},
        "10": {"name": "Tyrolean Mountain Farms", "location": "Graz, Austria", "tier": "HIGHRISK", "specialties": ["dairy", "mountain herbs"], "capacity": "low", "contract_type": "specialty"},
        "25": {"name": "Salzburg Alpine Farms", "location": "Salzburg, Austria", "tier": "RISK", "specialties": ["dairy", "alpine cheese"], "capacity": "medium", "contract_type": "specialty"},
        "26": {"name": "Vorarlberg Dairy", "location": "Bregenz, Austria", "tier": "STABLE", "specialties": ["dairy", "cheese"], "capacity": "medium", "contract_type": "long-term"},
        "27": {"name": "Carinthian Organics", "location": "Klagenfurt, Austria", "tier": "SURPLUS", "specialties": ["organic vegetables", "herbs"], "capacity": "medium", "contract_type": "premium"},
        "28": {"name": "Upper Austria Grains", "location": "Linz, Austria", "tier": "STABLE", "specialties": ["grains", "cereals"], "capacity": "high", "contract_type": "bulk"},
        "29": {"name": "Styrian Pumpkins", "location": "Graz, Austria", "tier": "SURPLUS", "specialties": ["pumpkins", "vegetables"], "capacity": "medium", "contract_type": "seasonal"},
        "30": {"name": "Burgenland Wines", "location": "Eisenstadt, Austria", "tier": "SURPLUS", "specialties": ["wine", "grapes"], "capacity": "medium", "contract_type": "seasonal"},
        "31": {"name": "Tyrol Mountain Herbs", "location": "Innsbruck, Austria", "tier": "RISK", "specialties": ["herbs", "mountain produce"], "capacity": "low", "contract_type": "specialty"},
        "32": {"name": "Lower Austria Vegetables", "location": "Vienna, Austria", "tier": "STABLE", "specialties": ["vegetables", "grains"], "capacity": "high", "contract_type": "long-term"},
        
        # Italy (7 suppliers)
        "7": {"name": "Lombardy Agricultural Union", "location": "Milan, Italy", "tier": "RISK", "specialties": ["rice", "dairy"], "capacity": "high", "contract_type": "long-term"},
        "33": {"name": "Piedmont Truffles", "location": "Turin, Italy", "tier": "SURPLUS", "specialties": ["truffles", "specialty produce"], "capacity": "low", "contract_type": "premium"},
        "34": {"name": "Veneto Rice Fields", "location": "Venice, Italy", "tier": "RISK", "specialties": ["rice", "grains"], "capacity": "high", "contract_type": "bulk"},
        "35": {"name": "Emilia-Romagna Cheese", "location": "Bologna, Italy", "tier": "STABLE", "specialties": ["cheese", "dairy"], "capacity": "high", "contract_type": "premium"},
        "36": {"name": "Trentino Apples", "location": "Trento, Italy", "tier": "SURPLUS", "specialties": ["apples", "fruits"], "capacity": "high", "contract_type": "seasonal"},
        "37": {"name": "South Tyrol Organics", "location": "Bolzano, Italy", "tier": "STABLE", "specialties": ["organic produce", "herbs"], "capacity": "medium", "contract_type": "premium"},
        "38": {"name": "Friuli Wines", "location": "Trieste, Italy", "tier": "SURPLUS", "specialties": ["wine", "grapes"], "capacity": "medium", "contract_type": "seasonal"},
        
        # France (5 suppliers)
        "9": {"name": "Alsace Premium Produce", "location": "Strasbourg, France", "tier": "RISK", "specialties": ["wine grapes", "specialty produce"], "capacity": "medium", "contract_type": "premium"},
        "39": {"name": "Burgundy Vineyards", "location": "Dijon, France", "tier": "SURPLUS", "specialties": ["wine", "grapes"], "capacity": "medium", "contract_type": "premium"},
        "40": {"name": "Franche-Comté Dairy", "location": "Besançon, France", "tier": "STABLE", "specialties": ["dairy", "cheese"], "capacity": "medium", "contract_type": "long-term"},
        "41": {"name": "Champagne Growers", "location": "Reims, France", "tier": "SURPLUS", "specialties": ["champagne grapes", "wine"], "capacity": "medium", "contract_type": "premium"},
        "42": {"name": "Lorraine Vegetables", "location": "Metz, France", "tier": "RISK", "specialties": ["vegetables", "grains"], "capacity": "medium", "contract_type": "seasonal"}
    },
    "current_alerts": {
        "high_priority": [
            {"supplier": "Organic Harvest Co", "issue": "Critical drought affecting soybean harvest", "impact": "40% yield reduction", "action": "Source alternatives immediately"},
            {"supplier": "Tyrolean Mountain Farms", "issue": "Alpine weather disrupting dairy operations", "impact": "Delivery delays 2-3 days", "action": "Activate backup suppliers"}
        ],
        "medium_priority": [
            {"supplier": "Alpine Farms AG", "issue": "Storage temperature fluctuations", "impact": "Potato quality concerns", "action": "Increase quality checks"},
            {"supplier": "Lombardy Agricultural Union", "issue": "Heavy rainfall affecting rice fields", "impact": "Potential flooding damage", "action": "Monitor weather forecasts"},
            {"supplier": "Alsace Premium Produce", "issue": "Cross-border transport delays", "impact": "15-20 minute delays", "action": "Adjust delivery schedules"}
        ],
        "opportunities": [
            {"supplier": "Rhône Valley Vineyards", "issue": "Exceptional grape harvest", "impact": "25% above-average yield", "action": "Negotiate bulk pricing"},
            {"supplier": "Swiss Valley Produce", "issue": "Corn surplus available", "impact": "500t additional capacity", "action": "Consider forward contracts"}
        ]
    },
    "company_context": {
        "name": "Swiss Corp",
        "location": "Zurich, Switzerland",
        "business": "Food supply chain management and distribution",
        "suppliers": 42,
        "countries": ["Switzerland", "Germany", "Austria", "Italy", "France"],
        "key_challenges": [
            "Managing agricultural supply variability",
            "Climate change adaptation",
            "Transport optimization across Alpine regions",
            "Maintaining food quality and safety standards"
        ],
        "current_priorities": [
            "Mitigate drought impact on soybean supply",
            "Secure alternative dairy sources",
            "Optimize transport routes during weather disruptions",
            "Capitalize on surplus opportunities"
        ]
    }
}

def get_rag_context(query: str) -> str:
    """Extract relevant context from RAG knowledge base based on query"""
    query_lower = query.lower()
    context_parts = []
    
    # Add company context
    context_parts.append(f"Company: {RAG_KNOWLEDGE_BASE['company_context']['name']} - {RAG_KNOWLEDGE_BASE['company_context']['business']}")
    
    # Check for specific supplier queries
    supplier_mentioned = None
    for supplier_id, supplier_data in RAG_KNOWLEDGE_BASE['supplier_directory'].items():
        if supplier_data['name'].lower() in query_lower or supplier_data['location'].lower() in query_lower:
            supplier_mentioned = supplier_id
            break
    
    if supplier_mentioned:
        supplier = RAG_KNOWLEDGE_BASE['supplier_directory'][supplier_mentioned]
        context_parts.append(f"SUPPLIER FOCUS: {supplier['name']} ({supplier['location']})")
        context_parts.append(f"- Tier: {supplier['tier']}, Specialties: {', '.join(supplier['specialties'])}")
        
        # Add specific risk data for this supplier
        if supplier_mentioned in RAG_KNOWLEDGE_BASE['agriculture_risk']['suppliers']:
            ag_data = RAG_KNOWLEDGE_BASE['agriculture_risk']['suppliers'][supplier_mentioned]
            context_parts.append(f"- Agriculture: NDVI {ag_data['ndvi']} ({ag_data['status']})")
        
        if supplier_mentioned in RAG_KNOWLEDGE_BASE['climate_risk']['suppliers']:
            climate_data = RAG_KNOWLEDGE_BASE['climate_risk']['suppliers'][supplier_mentioned]
            context_parts.append(f"- Climate: {climate_data['temp']}°C, {climate_data['precip']}mm, Risk: {climate_data['risk']}")
        
        if supplier_mentioned in RAG_KNOWLEDGE_BASE['transport_risk']['suppliers']:
            transport_data = RAG_KNOWLEDGE_BASE['transport_risk']['suppliers'][supplier_mentioned]
            context_parts.append(f"- Transport: {transport_data['traffic']} traffic, +{transport_data['delay']} min delay, {transport_data['reliability']} reliability")
    
    # Check for agriculture-related queries
    if any(term in query_lower for term in ['agriculture', 'crop', 'ndvi', 'farm', 'harvest', 'yield', 'drought', 'soybean']):
        ag_data = RAG_KNOWLEDGE_BASE['agriculture_risk']
        context_parts.append(f"AGRICULTURE RISK: {ag_data['overview']}")
        context_parts.append("Critical suppliers by NDVI status:")
        for supplier_id, data in ag_data['suppliers'].items():
            context_parts.append(f"- {data['name']}: NDVI {data['ndvi']} ({data['status']}) - {', '.join(data['crops'])}")
    
    # Check for climate-related queries
    if any(term in query_lower for term in ['climate', 'weather', 'temperature', 'rain', 'storm', 'flooding']):
        climate_data = RAG_KNOWLEDGE_BASE['climate_risk']
        context_parts.append(f"CLIMATE RISK: {climate_data['overview']}")
        context_parts.append("Current weather conditions by risk level:")
        for supplier_id, data in climate_data['suppliers'].items():
            context_parts.append(f"- {data['name']}: {data['temp']}°C, {data['precip']}mm, {data['risk']} risk - {data['forecast']}")
    
    # Check for transport-related queries
    if any(term in query_lower for term in ['transport', 'traffic', 'logistics', 'delivery', 'route', 'delay', 'reliability']):
        transport_data = RAG_KNOWLEDGE_BASE['transport_risk']
        context_parts.append(f"TRANSPORT RISK: {transport_data['overview']}")
        context_parts.append("Transport performance by reliability:")
        for supplier_id, data in transport_data['suppliers'].items():
            context_parts.append(f"- {data['name']}: {data['reliability']} reliable, +{data['delay']} min delay, {data['traffic']} traffic")
    
    # Check for supplier listing queries
    if any(term in query_lower for term in ['list', 'all suppliers', '42 suppliers', 'show suppliers', 'supplier list']):
        context_parts.append("COMPLETE SUPPLIER DIRECTORY (42 suppliers):")
        supplier_dir = RAG_KNOWLEDGE_BASE['supplier_directory']
        
        # Group by country for better organization
        countries = {}
        for supplier_id, supplier in supplier_dir.items():
            country = supplier['location'].split(', ')[-1]
            if country not in countries:
                countries[country] = []
            countries[country].append(f"- {supplier['name']} ({supplier['location']}) - {supplier['tier']} tier, {supplier['specialties']}")
        
        for country, suppliers in countries.items():
            context_parts.append(f"{country} ({len(suppliers)} suppliers):")
            context_parts.extend(suppliers)
    
    # Check for alert-related queries
    if any(term in query_lower for term in ['alert', 'problem', 'issue', 'priority', 'urgent']):
        alerts = RAG_KNOWLEDGE_BASE['current_alerts']
        context_parts.append("CURRENT ALERTS:")
        context_parts.append("High Priority:")
        for alert in alerts['high_priority']:
            context_parts.append(f"- {alert['supplier']}: {alert['issue']} ({alert['impact']}) → {alert['action']}")
        context_parts.append("Medium Priority:")
        for alert in alerts['medium_priority']:
            context_parts.append(f"- {alert['supplier']}: {alert['issue']} ({alert['impact']}) → {alert['action']}")
    
    # Check for opportunity queries
    if any(term in query_lower for term in ['opportunity', 'surplus', 'advantage', 'harvest', 'bulk']):
        opportunities = RAG_KNOWLEDGE_BASE['current_alerts']['opportunities']
        context_parts.append("CURRENT OPPORTUNITIES:")
        for opp in opportunities:
            context_parts.append(f"- {opp['supplier']}: {opp['issue']} ({opp['impact']}) → {opp['action']}")
    
    # Add general risk overview if no specific category detected
    if not any(term in query_lower for term in ['agriculture', 'crop', 'climate', 'weather', 'transport', 'traffic', 'alert', 'supplier', 'list']):
        context_parts.append("RISK OVERVIEW: Swiss Corp monitors three key risk categories:")
        context_parts.append("1. Agriculture Risk: NDVI-based crop health monitoring")
        context_parts.append("2. Climate Risk: Weather impact on transport and operations")
        context_parts.append("3. Transport Risk: Real-time traffic and logistics optimization")
        context_parts.append(f"Current Priorities: {', '.join(RAG_KNOWLEDGE_BASE['company_context']['current_priorities'])}")
    
    return "\n".join(context_parts)

def test_rag_system():
    """Test function to verify RAG system is working"""
    test_queries = [
        "What's the agriculture risk?",
        "Show me climate conditions",
        "Any transport delays?",
        "Tell me about suppliers"
    ]
    
    print("🧪 Testing RAG System:")
    for query in test_queries:
        context = get_rag_context(query)
        print(f"\nQuery: '{query}'")
        print(f"Context length: {len(context)} characters")
        print(f"Context preview: {context[:100]}...")
    print("✅ RAG system test complete")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI client initialized successfully")
else:
    openai_client = None
    if not OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY environment variable not set")
    if not OPENAI_AVAILABLE:
        print("⚠️  OpenAI package not available")

# ----------------------------
# Mock Data for Swiss Corp
# ----------------------------
MOCK_COMPANY = {
    "id": 1,
    "name": "Swiss Corp",
    "latitude": 47.3769,
    "longitude": 8.5417,
    "city": "Zurich",
    "country": "Switzerland"
}

MOCK_SUPPLIERS = [
    # Switzerland (12 suppliers)
    {"id": 1, "name": "Fenaco Genossenschaft", "latitude": 46.9481, "longitude": 7.4474, "city": "Bern", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 2, "name": "Alpine Farms AG", "latitude": 47.6062, "longitude": 8.1090, "city": "Thurgau", "country": "Switzerland", "tier": "RISK", "transport_modes": "Truck"},
    {"id": 3, "name": "Swiss Valley Produce", "latitude": 47.2692, "longitude": 11.4041, "city": "Innsbruck", "country": "Austria", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 4, "name": "Organic Harvest Co", "latitude": 47.0502, "longitude": 8.3093, "city": "Lucerne", "country": "Switzerland", "tier": "HIGHRISK", "transport_modes": "Truck"},
    {"id": 5, "name": "Bavarian Grain Collective", "latitude": 48.1351, "longitude": 11.5820, "city": "Munich", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 6, "name": "Rhône Valley Vineyards", "latitude": 46.2044, "longitude": 6.1432, "city": "Geneva", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 7, "name": "Lombardy Agricultural Union", "latitude": 45.4642, "longitude": 9.1900, "city": "Milan", "country": "Italy", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 8, "name": "Black Forest Organics", "latitude": 48.0196, "longitude": 7.8421, "city": "Freiburg", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 9, "name": "Alsace Premium Produce", "latitude": 48.5734, "longitude": 7.7521, "city": "Strasbourg", "country": "France", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 10, "name": "Tyrolean Mountain Farms", "latitude": 47.0707, "longitude": 15.4395, "city": "Graz", "country": "Austria", "tier": "HIGHRISK", "transport_modes": "Truck"},
    
    # Additional Swiss suppliers
    {"id": 11, "name": "Valais Mountain Dairy", "latitude": 46.2276, "longitude": 7.3591, "city": "Sion", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 12, "name": "Graubünden Organic", "latitude": 46.8182, "longitude": 9.8347, "city": "Chur", "country": "Switzerland", "tier": "STABLE", "transport_modes": "Truck"},
    {"id": 13, "name": "Ticino Vineyards", "latitude": 46.0037, "longitude": 8.9511, "city": "Lugano", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 14, "name": "Jura Cheese Collective", "latitude": 47.3667, "longitude": 7.3333, "city": "Delémont", "country": "Switzerland", "tier": "STABLE", "transport_modes": "Truck"},
    
    # Germany (10 suppliers)
    {"id": 15, "name": "Baden-Württemberg Farms", "latitude": 48.7758, "longitude": 9.1829, "city": "Stuttgart", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 16, "name": "Rhineland Produce", "latitude": 50.9375, "longitude": 6.9603, "city": "Cologne", "country": "Germany", "tier": "STABLE", "transport_modes": "Truck,Train"},
    {"id": 17, "name": "Swabian Grain Co", "latitude": 48.3668, "longitude": 10.8986, "city": "Augsburg", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 18, "name": "Allgäu Dairy Union", "latitude": 47.7261, "longitude": 10.3158, "city": "Kempten", "country": "Germany", "tier": "RISK", "transport_modes": "Truck"},
    {"id": 19, "name": "Franconian Organics", "latitude": 49.4521, "longitude": 10.9982, "city": "Nuremberg", "country": "Germany", "tier": "STABLE", "transport_modes": "Truck,Train"},
    {"id": 20, "name": "Lake Constance Fruits", "latitude": 47.6779, "longitude": 9.1732, "city": "Konstanz", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 21, "name": "Hessian Grain Mills", "latitude": 50.1109, "longitude": 8.6821, "city": "Frankfurt", "country": "Germany", "tier": "STABLE", "transport_modes": "Truck,Train"},
    {"id": 22, "name": "Palatinate Vineyards", "latitude": 49.3501, "longitude": 8.1067, "city": "Mannheim", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 23, "name": "Thuringian Vegetables", "latitude": 50.9848, "longitude": 11.0299, "city": "Erfurt", "country": "Germany", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 24, "name": "Saxon Specialty Foods", "latitude": 51.0504, "longitude": 13.7373, "city": "Dresden", "country": "Germany", "tier": "STABLE", "transport_modes": "Truck,Train"},
    
    # Austria (8 suppliers)
    {"id": 25, "name": "Salzburg Alpine Farms", "latitude": 47.8095, "longitude": 13.0550, "city": "Salzburg", "country": "Austria", "tier": "RISK", "transport_modes": "Truck"},
    {"id": 26, "name": "Vorarlberg Dairy", "latitude": 47.5058, "longitude": 9.7471, "city": "Bregenz", "country": "Austria", "tier": "STABLE", "transport_modes": "Truck"},
    {"id": 27, "name": "Carinthian Organics", "latitude": 46.6247, "longitude": 14.3055, "city": "Klagenfurt", "country": "Austria", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 28, "name": "Upper Austria Grains", "latitude": 48.3069, "longitude": 14.2858, "city": "Linz", "country": "Austria", "tier": "STABLE", "transport_modes": "Truck,Train"},
    {"id": 29, "name": "Styrian Pumpkins", "latitude": 47.0707, "longitude": 15.4395, "city": "Graz", "country": "Austria", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 30, "name": "Burgenland Wines", "latitude": 47.8450, "longitude": 16.5200, "city": "Eisenstadt", "country": "Austria", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 31, "name": "Tyrol Mountain Herbs", "latitude": 47.2692, "longitude": 11.4041, "city": "Innsbruck", "country": "Austria", "tier": "RISK", "transport_modes": "Truck"},
    {"id": 32, "name": "Lower Austria Vegetables", "latitude": 48.2082, "longitude": 16.3738, "city": "Vienna", "country": "Austria", "tier": "STABLE", "transport_modes": "Truck,Train"},
    
    # Italy (6 suppliers)
    {"id": 33, "name": "Piedmont Truffles", "latitude": 45.0703, "longitude": 7.6869, "city": "Turin", "country": "Italy", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 34, "name": "Veneto Rice Fields", "latitude": 45.4408, "longitude": 12.3155, "city": "Venice", "country": "Italy", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 35, "name": "Emilia-Romagna Cheese", "latitude": 44.4949, "longitude": 11.3426, "city": "Bologna", "country": "Italy", "tier": "STABLE", "transport_modes": "Truck,Train"},
    {"id": 36, "name": "Trentino Apples", "latitude": 46.0748, "longitude": 11.1217, "city": "Trento", "country": "Italy", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 37, "name": "South Tyrol Organics", "latitude": 46.4983, "longitude": 11.3548, "city": "Bolzano", "country": "Italy", "tier": "STABLE", "transport_modes": "Truck"},
    {"id": 38, "name": "Friuli Wines", "latitude": 45.6494, "longitude": 13.7768, "city": "Trieste", "country": "Italy", "tier": "SURPLUS", "transport_modes": "Truck"},
    
    # France (6 suppliers)
    {"id": 39, "name": "Burgundy Vineyards", "latitude": 47.3220, "longitude": 5.0415, "city": "Dijon", "country": "France", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 40, "name": "Franche-Comté Dairy", "latitude": 47.2378, "longitude": 6.0241, "city": "Besançon", "country": "France", "tier": "STABLE", "transport_modes": "Truck"},
    {"id": 41, "name": "Champagne Growers", "latitude": 49.2583, "longitude": 4.0317, "city": "Reims", "country": "France", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 42, "name": "Lorraine Vegetables", "latitude": 49.1193, "longitude": 6.1757, "city": "Metz", "country": "France", "tier": "RISK", "transport_modes": "Truck,Train"}
]

MOCK_ALERTS = [
    {"id": 1, "company_id": 1, "supplier_id": 4, "crop_type": "soybeans", "severity": "HIGHRISK", "title": "Critical drought conditions", "message": "Severe drought affecting soybean harvest. 40% yield reduction expected.", "created_at": "2025-01-04T10:30:00"},
    {"id": 2, "company_id": 1, "supplier_id": 2, "crop_type": "potatoes", "severity": "RISK", "title": "Storage conditions deteriorating", "message": "Temperature fluctuations in storage facility.", "created_at": "2025-01-04T08:15:00"},
    {"id": 3, "company_id": 1, "supplier_id": 7, "crop_type": "rice", "severity": "RISK", "title": "Flooding concerns in Lombardy", "message": "Heavy rainfall affecting rice paddies.", "created_at": "2025-01-04T14:20:00"},
    {"id": 4, "company_id": 1, "supplier_id": 10, "crop_type": "dairy", "severity": "HIGHRISK", "title": "Alpine dairy disrupted", "message": "Extreme weather affecting mountain operations.", "created_at": "2025-01-04T11:45:00"},
    {"id": 5, "company_id": 1, "supplier_id": 6, "crop_type": "grapes", "severity": "SURPLUS", "title": "Exceptional grape harvest", "message": "25% above-average yield available.", "created_at": "2025-01-03T09:30:00"},
    {"id": 6, "company_id": 1, "supplier_id": 9, "crop_type": "wine_grapes", "severity": "SURPLUS", "title": "Alsace wine grape surplus", "message": "Premium grapes available at special pricing.", "created_at": "2025-01-02T16:15:00"},
    {"id": 7, "company_id": 1, "supplier_id": 3, "crop_type": "corn", "severity": "SURPLUS", "title": "Excellent corn harvest", "message": "Additional 500t available at discounted rates.", "created_at": "2025-01-03T16:45:00"}
]


# ----------------------------
# Helpers: HTTP
# ----------------------------
def api_get(path: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None) -> Any:
    """GET helper with Bearer auth if token is provided."""
    url = f"{API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"GET {url} failed: {e}")
        return {"error": str(e)}

def api_post(path: str, payload: Dict[str, Any], token: Optional[str] = None) -> Any:
    """POST helper with Bearer auth if token is provided."""
    url = f"{API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"POST {url} failed: {e}")
        return {"error": str(e)}

def get_suppliers(token: str):
    return api_get("/suppliers/", token=token)

def get_supplier_stocks(supplier_id: int, token: str):
    return api_get(f"/stocks/supplier/{supplier_id}", token=token)

def get_stock(stock_id: int, token: str):
    return api_get(f"/stocks/{stock_id}", token=token)

def get_crop_stocks(crop_type: str, token: str):
    return api_get(f"/stocks/crop/{crop_type}", token=token)

def get_company_mappings(token: str):
    return api_get("/mappings/", token=token)

def create_mapping(payload: dict, token: str):
    return api_post("/mappings/", payload, token=token)

def get_company(token: str):
    return api_get("/companies", token=token)


# ----------------------------
# Normalize API payloads (robust vs. schema variants)
# ----------------------------
def normalize_suppliers(suppliers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for s in suppliers or []:
        sid = s.get("SupplierId") or s.get("supplierId") or s.get("id") or s.get("supplier_id")
        name = s.get("Name") or s.get("name")
        lat  = s.get("Lat") or s.get("lat") or s.get("Latitude") or s.get("latitude")
        lon  = s.get("Lon") or s.get("lon") or s.get("Longitude") or s.get("longitude")
        tier = s.get("CurrentTier") or s.get("currentTier") or s.get("tier")
        loc  = s.get("Location") or s.get("location")
        modes= s.get("TransportModes") or s.get("transportModes")

        try:
            lat = float(lat) if lat is not None else None
        except:
            lat = None

        try:
            lon = float(lon) if lon is not None else None
        except:
            lon = None

        norm.append({
            "SupplierId": sid, "Name": name, "Lat": lat, "Lon": lon,
            "CurrentTier": tier, "Location": loc, "TransportModes": modes, "_raw": s
        })
    return norm

def normalize_company(company: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize single company object."""
    if not isinstance(company, dict) or company.get("error"):
        return {}
    return {
        "CompanyId": company.get("id") or company.get("CompanyId"),
        "Name": company.get("name") or company.get("Name"),
        "Lat": company.get("latitude") or company.get("Lat"),
        "Lon": company.get("longitude") or company.get("Lon"),
        "City": company.get("city"),
        "Country": company.get("country"),
        "_raw": company
    }

def normalize_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for a in alerts or []:
        sev = a.get("Severity") or a.get("severity")
        if sev:
            sev = sev.upper()
        else:
            sev = "STABLE"  # Default fallback

        norm.append({
            "AlertId": a.get("AlertId") or a.get("alertId"),
            "CompanyId": a.get("CompanyId") or a.get("companyId"),
            "SupplierId": a.get("SupplierId") or a.get("supplierId"),
            "CropId": a.get("CropId") or a.get("cropId"),
            "CreatedAt": a.get("CreatedAt") or a.get("createdAt"),
            "Severity": sev,
            "Title": a.get("Title") or a.get("title") or "",
            "Details": a.get("Details") or a.get("details") or {},
        })
    return norm

def normalize_recs(recs: Dict[str, Any]) -> Dict[str, Any]:
    out = {"recommendations": []}
    raw_recs = recs.get("recommendations") or recs.get("Recommendations") or []

    for r in raw_recs:
        out["recommendations"].append({
            "supplier": r.get("supplier") or r.get("Supplier") or "",
            "reasoning": r.get("reasoning") or r.get("Reasoning") or "",
        })
    return out


# ----------------------------
# UI helpers
# ----------------------------
TIER_COLOR = {
    "SURPLUS": "#22c55e",   # green
    "STABLE": "#6C757D",    # grey
    "RISK": "#f59e0b",      # amber
    "HIGHRISK": "#ef4444",  # red
    None: "#93c5fd",        # fallback
}

SEVERITY_BADGE = {
    "SURPLUS": {"color": "success", "text": "Surplus"},
    "STABLE": {"color": "secondary", "text": "Stable"},
    "RISK": {"color": "warning", "text": "Risk"},
    "CRITICAL": {"color": "danger", "text": "Critical"},
}

SEVERITY_ORDER = {
    "CRITICAL": 3,
    "RISK": 2,
    "STABLE": 1,
    "SURPLUS": 0,
}

def marker_for_supplier(s, selected_supplier_id=None, show_yield_shortage=False, show_agriculture=False, show_climate=False, show_transport=False):
    is_selected = s.get("SupplierId") == selected_supplier_id
    radius = 14 if is_selected else 10
    weight = 3 if is_selected else 1
    
    print(f"marker_for_supplier called: show_agriculture={show_agriculture}, show_climate={show_climate}, show_transport={show_transport}, supplier={s.get('SupplierId')}")
    
    # Color logic based on toggles (yield shortage takes priority, then transport, then climate, then agriculture)
    if show_yield_shortage:
        # When yield shortage is ON, show regular suppliers in neutral gray
        # The wheat CSV data will be shown as separate markers with red/green colors
        color = "#6b7280"  # Gray - neutral color for regular suppliers
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Regular Supplier"
        
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Hr(),
            html.Div([
                html.Strong("📋 Regular Supplier"),
                html.Br(),
                html.Div("🌾 Wheat yield data shown separately"),
                html.Div("📊 See wheat farm markers for 2026 predictions"),
                html.Br(),
                html.Div("💡 Focus on red/green wheat markers for yield shortage analysis", 
                        className="small text-primary")
            ])
        ]
        
    elif show_transport:
        # Use traffic-based colors for logistics risk
        traffic_data = get_traffic_data_for_supplier(s.get("SupplierId"))
        traffic_level = traffic_data["traffic_level"]
        color = traffic_data["color"]
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Traffic: {traffic_level} (+{traffic_data['delay_minutes']:.0f} min)"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Hr(),
            html.Div([
                html.Strong(f"🚛 Traffic Level: {traffic_level}"),
                html.Br(),
                html.Div(f"⏱️ Normal Travel Time: {traffic_data['duration_normal']:.0f} minutes"),
                html.Div(f"🚦 Current Travel Time: {traffic_data['duration_traffic']:.0f} minutes"),
                html.Div(f"⏰ Traffic Delay: +{traffic_data['delay_minutes']:.0f} minutes"),
                html.Div(f"📊 Delay Percentage: {traffic_data['delay_percentage']:.1f}%"),
                html.Br(),
                html.Div(f"💡 Recommendation: {traffic_data['recommendation']}", 
                        className="small text-primary")
            ])
        ]
        
    elif show_climate:
        # Use climate-based colors for transport risk
        climate_risk = get_climate_risk_for_supplier(s.get("SupplierId"))
        risk_level = climate_risk["risk_level"]
        
        if risk_level == "HIGH":
            color = "#ef4444"  # Red - high transport risk
        elif risk_level == "MEDIUM":
            color = "#f59e0b"  # Yellow - moderate transport risk
        else:
            color = "#22c55e"  # Green - low transport risk
        
        # Create clearer tooltip with risk explanation
        risk_emoji = "🔴" if risk_level == "HIGH" else ("🟡" if risk_level == "MEDIUM" else "🟢")
        tooltip_text = f"{s.get('Name') or 'Supplier'} - {risk_emoji} {risk_level} Transport Risk"
        
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Hr(),
            html.Div([
                html.Strong(f"{risk_emoji} Transport Risk: {risk_level}"),
                html.Br(),
                html.Div(f"🌡️ Temperature: {climate_risk['temp']}°C"),
                html.Div(f"🌧️ Precipitation: {climate_risk['precip']}mm"),
                html.Br(),
                html.Div(f"⏱️ Expected Delay: +{climate_risk.get('additional_delay_minutes', 0)} minutes"),
                html.Div(f"📋 Impact: {climate_risk['impact']}", className="small"),
                html.Div(f"💡 Recommendation: {climate_risk.get('recommendation', 'Normal operations')}", 
                        className="small text-primary")
            ])
        ]
        
    elif show_agriculture:
        # Use NDVI-based colors when satellite data is enabled
        ndvi_value = get_mock_ndvi_for_supplier(s.get("SupplierId"))
        print(f"Supplier {s.get('SupplierId')} ({s.get('Name')}): NDVI = {ndvi_value}")
        
        if ndvi_value > 0.7:
            color = "#22c55e"  # Healthy green
            print(f"  -> Healthy green")
        elif ndvi_value > 0.5:
            color = "#f59e0b"  # Moderate yellow
            print(f"  -> Moderate yellow")
        elif ndvi_value > 0.3:
            color = "#f97316"  # Stressed orange
            print(f"  -> Stressed orange")
        else:
            color = "#ef4444"  # Critical red
            print(f"  -> Critical red")
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Crop Health: {ndvi_value:.3f} ({get_ndvi_status(ndvi_value)})"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Div(f"Crop Health Index: {ndvi_value:.3f}"),
            html.Div(f"Agricultural Status: {get_ndvi_status(ndvi_value)}")
        ]
    else:
        # Default: all farmers are green (healthy)
        color = "#2563eb" if is_selected else "#22c55e"  # Blue if selected, green otherwise
        tooltip_text = f"{s.get('Name') or 'Supplier'} - {s.get('_raw').get('city','')}"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")),
            html.Div(f"Tier: {s.get('CurrentTier','?')}")
        ]

    # Create unique key to force re-rendering when colors change
    marker_mode = "transport" if show_transport else ("climate" if show_climate else ("agriculture" if show_agriculture else "default"))
    marker_key = f"supplier-{s.get('SupplierId')}-{marker_mode}"
    
    return dl.CircleMarker(
        id=marker_key,
        center=(s.get("Lat") or 0, s.get("Lon") or 0),
        radius=radius,
        color=color,
        weight=weight,
        fill=True,
        fillOpacity=0.7 if is_selected else 0.5,
        children=[
            dl.Tooltip(tooltip_text),
            dl.Popup(popup_content)
        ]
    )

def marker_for_company(c):
    if not c or not c.get("Lat") or not c.get("Lon"):
        return None
    # Use a distinctive marker for Swiss Corp HQ
    return dl.CircleMarker(
        center=(c["Lat"], c["Lon"]),
        radius=20,
        color="#1e40af",  # Dark blue border
        weight=4,
        fill=True,
        fillColor="#3b82f6",  # Blue fill
        fillOpacity=0.8,
        children=[
            dl.Tooltip(f"🏢 {c.get('Name','Company')} (HQ)"),
            dl.Popup([
                html.B(f"🏢 {c.get('Name','Company')} Headquarters"), html.Br(),
                html.Div(f"📍 {c.get('City','')}, {c.get('Country','')}")
            ])
        ],
    )

# ----------------------------
# Routing helpers
# ----------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def _decode_polyline5(polyline: str) -> List[tuple]:
    coords=[]; index=0; lat=0; lon=0; length=len(polyline)
    while index<length:
        shift=0; result=0
        while True:
            b=ord(polyline[index])-63; index+=1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        dlat = ~(result>>1) if (result & 1) else (result>>1)
        lat += dlat

        shift=0; result=0
        while True:
            b=ord(polyline[index])-63; index+=1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        dlon = ~(result>>1) if (result & 1) else (result>>1)
        lon += dlon
        coords.append((lat/1e5, lon/1e5))
    return coords

def osrm_route(a: tuple, b: tuple) -> Optional[Dict[str, Any]]:
    if not USE_OSRM:
        return None
    url = f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}"
    params = {"overview":"full","geometries":"polyline","alternatives":"false"}
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        route = routes[0]
        coords = _decode_polyline5(route.get("geometry",""))
        return {"coords": coords}
    except Exception:
        return None

def build_supplier_routes(company: Dict[str, Any], suppliers: List[Dict[str, Any]], show_climate: bool = False, show_transport: bool = False) -> List[Any]:
    """Build polyline routes from each supplier to company location using OSRM routing."""
    if not company or not company.get("Lat") or not company.get("Lon"):
        return []

    target = (company["Lat"], company["Lon"])
    polylines = []
    for s in suppliers:
        if not s.get("Lat") or not s.get("Lon"):
            continue
        src = (s["Lat"], s["Lon"])
        
        # Determine route color based on active mode (transport takes priority)
        if show_transport:
            traffic_data = get_traffic_data_for_supplier(s.get("SupplierId"))
            route_color = traffic_data["color"]
            route_weight = 4 if traffic_data["traffic_level"] == "HEAVY" else 3
        elif show_climate:
            climate_risk = get_climate_risk_for_supplier(s.get("SupplierId"))
            risk_level = climate_risk["risk_level"]
            
            if risk_level == "HIGH":
                route_color = "#ef4444"  # Red
                route_weight = 4
            elif risk_level == "MEDIUM":
                route_color = "#f59e0b"  # Yellow
                route_weight = 3
            else:
                route_color = "#22c55e"  # Green
                route_weight = 3
        else:
            route_color = "#2563eb"  # Default blue
            route_weight = 3
        
        routed = osrm_route(src, target)
        if routed and routed.get("coords"):
            # Use actual routed path with climate-based coloring
            line = dl.Polyline(
                positions=routed["coords"], 
                color=route_color, 
                weight=route_weight, 
                opacity=0.8
            )
        else:
            # Fallback to straight line if routing fails
            line = dl.Polyline(
                positions=[src, target], 
                color=route_color, 
                weight=route_weight, 
                dashArray="5,5"
            )
        polylines.append(line)
    return polylines

def normalize_stocks(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in (stocks or []):
        out.append({
            "id": s.get("id") or s.get("stock_id") or s.get("StockId"),
            "crop_type": s.get("crop_type") or s.get("CropType") or s.get("crop"),
            "available": s.get("available_volume") or s.get("available") or s.get("quantity"),
            "unit": s.get("unit") or s.get("Unit") or "t",
            "price": s.get("price") or s.get("price_per_unit") or s.get("Price"),
            "expiry": s.get("expiry_date") or s.get("expiry") or s.get("best_before"),
            "risk": s.get("risk_class") or s.get("risk") or None,
            "_raw": s,
        })
    return out

def stock_item_card(s: Dict[str, Any]) -> dbc.ListGroupItem:
    top = f"{(s.get('crop_type') or 'Unknown').title()} — {s.get('available','?')} {s.get('unit','')}"
    meta = []
    if s.get("price") is not None:
        meta.append(f"Price: {s['price']}")
    if s.get("risk") is not None:
        meta.append(f"Risk: {s['risk']}")
    if s.get("expiry"):
        meta.append(f"Expiry: {s['expiry']}")
    sub = " | ".join(meta) if meta else "—"
    return dbc.ListGroupItem(
        [html.Div(top, className="fw-semibold"), html.Small(sub, className="text-muted d-block")]
    )


def create_wheat_supplier_marker(wheat_supplier: Dict[str, Any]):
    """Create marker for wheat supplier based on CSV data"""
    
    # Determine color based on yield shortage risk
    if wheat_supplier["is_risk"]:
        color = "#ef4444"  # Red for risk (estimated < requested)
        risk_status = "RISK"
        risk_emoji = "🔴"
    else:
        color = "#22c55e"  # Green for no risk (estimated >= requested)
        risk_status = "SAFE"
        risk_emoji = "🟢"
    
    # Create tooltip text
    tooltip_text = f"{wheat_supplier['name']} - {risk_emoji} {risk_status}"
    
    # Create popup content with detailed information
    popup_content = [
        html.B(wheat_supplier['name']), html.Br(),
        html.Div(f"📍 {wheat_supplier['location']}"), html.Br(),
        html.Hr(),
        html.Div([
            html.Strong(f"{risk_emoji} Yield Status: {risk_status}"),
            html.Br(),
            html.Div(f"🌾 Estimated Yield: {wheat_supplier['estimated_yield']:.0f} tons"),
            html.Div(f"📋 Requested Yield: {wheat_supplier['requested_yield']:.0f} tons"),
            html.Div(f"📊 Shortage/Surplus: {wheat_supplier['yield_shortage']:.0f} tons"),
            html.Br(),
            html.Div(f"🌱 NDVI: {wheat_supplier['ndvi']:.3f}"),
            html.Div(f"🌡️ Avg Temperature: {wheat_supplier['temperature']:.1f}°C"),
            html.Div(f"🌧️ Precipitation: {wheat_supplier['precipitation']:.1f}mm"),
        ])
    ]
    
    return dl.CircleMarker(
        id=f"wheat-marker-{wheat_supplier['id']}",
        center=(wheat_supplier['latitude'], wheat_supplier['longitude']),
        radius=8,  # Smaller radius for wheat suppliers
        color=color,
        weight=2,
        fill=True,
        fillOpacity=0.7,
        children=[
            dl.Tooltip(tooltip_text),
            dl.Popup(popup_content)
        ]
    )

def build_map_with_caching(company: Dict[str, Any], suppliers: List[Dict[str, Any]], alerts: List[Dict[str, Any]], selected_supplier_id=None, show_yield_shortage=False, show_agriculture=False, show_climate=False, show_transport=False):
    """Build map with efficient caching and minimal API calls"""
    
    # Base markers
    marker_children = []
    comp_marker = marker_for_company(company)
    if comp_marker:
        marker_children.append(comp_marker)
    
    # Add wheat suppliers when yield shortage toggle is ON, otherwise show regular suppliers
    if show_yield_shortage:
        # Only show wheat suppliers from CSV data
        wheat_suppliers = load_wheat_data()
        print(f"🌾 Loading {len(wheat_suppliers)} wheat suppliers for yield shortage view")
        
        risk_markers = 0
        safe_markers = 0
        for wheat_supplier in wheat_suppliers:
            if wheat_supplier.get("latitude") and wheat_supplier.get("longitude"):
                marker = create_wheat_supplier_marker(wheat_supplier)
                marker_children.append(marker)
                if wheat_supplier["is_risk"]:
                    risk_markers += 1
                else:
                    safe_markers += 1
        
        print(f"🔴 Added {risk_markers} RISK markers (red)")
        print(f"🟢 Added {safe_markers} SAFE markers (green)")
    else:
        # Show regular suppliers with toggle-based colors
        for s in suppliers:
            if s.get("Lat") and s.get("Lon"):
                marker = marker_for_supplier_cached(s, selected_supplier_id, show_yield_shortage, show_agriculture, show_climate, show_transport)
                marker_children.append(marker)

    # Routes with caching
    route_layers = build_supplier_routes_cached(company, suppliers, show_climate, show_transport)

    # Alert overlays (minimal processing)
    alert_overlays = []
    suppliers_index = {s.get("SupplierId"): s for s in suppliers}
    for a in alerts:
        sev = (a.get("Severity") or "").upper()
        color = TIER_COLOR.get(sev, "#93c5fd")

        sup = suppliers_index.get(a.get("SupplierId"))
        if sup and sup.get("Lat") and sup.get("Lon"):
            lat, lon = sup["Lat"], sup["Lon"]
        else:
            if company and company.get("Lat") and company.get("Lon"):
                lat, lon = company["Lat"], company["Lon"]
            else:
                continue

        alert_overlays.append(
            dl.CircleMarker(
                center=(lat, lon),
                radius=14,
                color=color,
                fill=True,
                fillOpacity=0.45,
            )
        )

    # Base layers (static)
    children = [
        dl.TileLayer(
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )
    ]
    
    # Add layers
    children.extend([
        dl.LayerGroup(alert_overlays, id="alert-overlays"),
        dl.LayerGroup(marker_children, id="entity-markers"),
        dl.LayerGroup(route_layers, id="route-layers"),
    ])
    
    # Add legend table for active mode
    if show_yield_shortage or show_agriculture or show_climate or show_transport:
        legend_table = create_legend_table(show_yield_shortage, show_agriculture, show_climate, show_transport)
        if legend_table:
            children.append(legend_table)
    
    # Return static map
    return dl.Map(
        id="main-map",
        center=(47.3769, 8.5417), 
        zoom=8, 
        children=children, 
        style={"height": "calc(100vh - 80px)", "width": "100%"}
    )

def marker_for_supplier_cached(s, selected_supplier_id=None, show_yield_shortage=False, show_agriculture=False, show_climate=False, show_transport=False):
    """Cached version of marker_for_supplier with minimal API calls"""
    
    supplier_id = s.get("SupplierId")
    is_selected = supplier_id == selected_supplier_id
    radius = 14 if is_selected else 10
    weight = 3 if is_selected else 1
    
    # Use cached data to avoid repeated API calls
    cache_key = f"marker_data_{supplier_id}_{show_yield_shortage}_{show_agriculture}_{show_climate}_{show_transport}"
    now = dt.datetime.now().timestamp()
    
    if cache_key in _API_CACHE:
        cached_data, timestamp = _API_CACHE[cache_key]
        if now - timestamp < 60:  # 1 minute cache for marker data
            color = cached_data["color"]
            tooltip_text = cached_data["tooltip"]
            popup_content = cached_data["popup"]
        else:
            color, tooltip_text, popup_content = get_marker_data(s, show_yield_shortage, show_agriculture, show_climate, show_transport)
            _API_CACHE[cache_key] = {"color": color, "tooltip": tooltip_text, "popup": popup_content}, now
    else:
        color, tooltip_text, popup_content = get_marker_data(s, show_yield_shortage, show_agriculture, show_climate, show_transport)
        _API_CACHE[cache_key] = {"color": color, "tooltip": tooltip_text, "popup": popup_content}, now
    
    marker_key = f"supplier-{supplier_id}-cached"
    
    return dl.CircleMarker(
        id=marker_key,
        center=(s.get("Lat") or 0, s.get("Lon") or 0),
        radius=radius,
        color=color,
        weight=weight,
        fill=True,
        fillOpacity=0.7 if is_selected else 0.5,
        children=[
            dl.Tooltip(tooltip_text),
            dl.Popup(popup_content)
        ]
    )

def get_marker_data(s, show_yield_shortage, show_agriculture, show_climate, show_transport):
    """Get marker color and content based on toggle state"""
    
    supplier_id = s.get("SupplierId")
    
    if show_yield_shortage:
        # When yield shortage is ON, show regular suppliers in neutral gray
        color = "#6b7280"  # Gray - neutral color for regular suppliers
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Regular Supplier"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Div("📋 Regular Supplier"),
            html.Div("🌾 See wheat farm markers for yield data"),
            html.Div("📊 Focus on red/green markers for 2026 predictions")
        ]
    elif show_transport:
        traffic_data = get_traffic_data_for_supplier(supplier_id)
        color = traffic_data["color"]
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Traffic: {traffic_data['traffic_level']}"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Div(f"🚛 Traffic Level: {traffic_data['traffic_level']}"),
            html.Div(f"⏰ Delay: +{traffic_data['delay_minutes']:.0f} minutes")
        ]
    elif show_climate:
        climate_risk = get_climate_risk_for_supplier(supplier_id)
        risk_level = climate_risk["risk_level"]
        
        if risk_level == "HIGH":
            color = "#ef4444"
        elif risk_level == "MEDIUM":
            color = "#f59e0b"
        else:
            color = "#22c55e"
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - Climate Risk: {risk_level}"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Div(f"🌡️ Climate Risk: {risk_level}"),
            html.Div(f"🌧️ Temp: {climate_risk['temp']}°C, Precip: {climate_risk['precip']}mm")
        ]
    elif show_agriculture:
        ndvi_value = get_mock_ndvi_for_supplier(supplier_id)
        
        if ndvi_value > 0.7:
            color = "#22c55e"
        elif ndvi_value > 0.5:
            color = "#f59e0b"
        elif ndvi_value > 0.3:
            color = "#f97316"
        else:
            color = "#ef4444"
        
        tooltip_text = f"{s.get('Name') or 'Supplier'} - NDVI: {ndvi_value:.3f}"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")), html.Br(),
            html.Div(f"🌱 NDVI: {ndvi_value:.3f}"),
            html.Div(f"Status: {get_ndvi_status(ndvi_value)}")
        ]
    else:
        color = "#22c55e"
        tooltip_text = f"{s.get('Name') or 'Supplier'}"
        popup_content = [
            html.B(s.get("Name") or "Supplier"), html.Br(),
            html.Div(s.get("Location","")),
            html.Div(f"Tier: {s.get('CurrentTier','?')}")
        ]
    
    return color, tooltip_text, popup_content

def build_supplier_routes_cached(company: Dict[str, Any], suppliers: List[Dict[str, Any]], show_climate: bool = False, show_transport: bool = False) -> List[Any]:
    """Cached version of route building"""
    
    if not company or not company.get("Lat") or not company.get("Lon"):
        return []

    # Cache routes to avoid rebuilding
    route_cache_key = f"routes_v2_{len(suppliers)}_{show_climate}_{show_transport}"
    now = dt.datetime.now().timestamp()
    
    if route_cache_key in _API_CACHE:
        cached_routes, timestamp = _API_CACHE[route_cache_key]
        if now - timestamp < 120:  # 2 minute cache for routes
            return cached_routes

    target = (company["Lat"], company["Lon"])
    polylines = []
    
    for s in suppliers:
        if not s.get("Lat") or not s.get("Lon"):
            continue
        src = (s["Lat"], s["Lon"])
        
        # Determine route color
        if show_transport:
            traffic_data = get_traffic_data_for_supplier(s.get("SupplierId"))
            route_color = traffic_data["color"]
            route_weight = 4 if traffic_data["traffic_level"] == "HEAVY" else 3
        elif show_climate:
            climate_risk = get_climate_risk_for_supplier(s.get("SupplierId"))
            risk_level = climate_risk["risk_level"]
            
            if risk_level == "HIGH":
                route_color = "#ef4444"
                route_weight = 4
            elif risk_level == "MEDIUM":
                route_color = "#f59e0b"
                route_weight = 3
            else:
                route_color = "#22c55e"
                route_weight = 3
        else:
            route_color = "#2563eb"  # Default blue
            route_weight = 3
        
        routed = osrm_route(src, target)
        if routed and routed.get("coords"):
            line = dl.Polyline(
                positions=routed["coords"], 
                color=route_color, 
                weight=route_weight, 
                opacity=0.8
            )
        else:
            line = dl.Polyline(
                positions=[src, target], 
                color=route_color, 
                weight=route_weight, 
                dashArray="5,5"
            )
        polylines.append(line)
    
    # Cache the routes
    _API_CACHE[route_cache_key] = (polylines, now)
    
    return polylines

def build_map_fast(company: Dict[str, Any], suppliers: List[Dict[str, Any]], alerts: List[Dict[str, Any]], selected_supplier_id=None, show_agriculture=False, show_climate=False, show_transport=False):
    """Fast map building - only update markers, reuse base map"""
    
    print("⚡ Fast map update - only changing marker colors")
    
    # Base markers
    marker_children = []
    comp_marker = marker_for_company(company)
    if comp_marker:
        marker_children.append(comp_marker)
    
    # Only update supplier markers (this is what changes with toggles)
    for s in suppliers:
        if s.get("Lat") and s.get("Lon"):
            marker = marker_for_supplier(s, selected_supplier_id, show_agriculture, show_climate, show_transport)
            marker_children.append(marker)

    # Routes - use cached routes when possible
    route_cache_key = f"routes_{len(suppliers)}_{show_climate}_{show_transport}"
    now = dt.datetime.now().timestamp()
    
    if route_cache_key in _API_CACHE:
        route_layers, timestamp = _API_CACHE[route_cache_key]
        if now - timestamp < 60:  # 1 minute cache for routes
            print("🚀 Using cached routes")
        else:
            route_layers = build_supplier_routes(company, suppliers, show_climate, show_transport)
            _API_CACHE[route_cache_key] = (route_layers, now)
    else:
        route_layers = build_supplier_routes(company, suppliers, show_climate, show_transport)
        _API_CACHE[route_cache_key] = (route_layers, now)

    # Alert overlays (minimal processing)
    alert_overlays = []
    suppliers_index = {s.get("SupplierId"): s for s in suppliers}
    for a in alerts:
        sev = (a.get("Severity") or "").upper()
        color = TIER_COLOR.get(sev, "#93c5fd")

        sup = suppliers_index.get(a.get("SupplierId"))
        if sup and sup.get("Lat") and sup.get("Lon"):
            lat, lon = sup["Lat"], sup["Lon"]
        else:
            if company and company.get("Lat") and company.get("Lon"):
                lat, lon = company["Lat"], company["Lon"]
            else:
                continue

        alert_overlays.append(
            dl.CircleMarker(
                center=(lat, lon),
                radius=14,
                color=color,
                fill=True,
                fillOpacity=0.45,
            )
        )

    # Base layers (static)
    children = [
        dl.TileLayer(
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )
    ]
    
    # Add overlays (only if needed)
    if show_agriculture:
        agriculture_layer = create_satellite_overlay()
        if agriculture_layer:
            children.append(agriculture_layer)
    
    if show_climate:
        climate_layer = create_climate_overlay()
        if climate_layer:
            children.append(climate_layer)
    
    # Add layers
    children.extend([
        dl.LayerGroup(alert_overlays, id="alert-overlays"),
        dl.LayerGroup(marker_children, id="entity-markers"),
        dl.LayerGroup(route_layers, id="route-layers"),
    ])
    
    # Add legend table for active mode
    if show_yield_shortage or show_agriculture or show_climate or show_transport:
        legend_table = create_legend_table(show_yield_shortage, show_agriculture, show_climate, show_transport)
        if legend_table:
            children.append(legend_table)
    
    # Return optimized map
    return dl.Map(
        id="main-map",
        center=(47.3769, 8.5417), 
        zoom=8, 
        children=children, 
        style={"height": "calc(100vh - 80px)", "width": "100%"}
    )

def build_map(company: Dict[str, Any], suppliers: List[Dict[str, Any]], alerts: List[Dict[str, Any]], selected_supplier_id=None, show_agriculture=False, show_climate=False, show_transport=False):
    """Original map building function (kept for compatibility)"""
    # Base markers
    marker_children = []
    comp_marker = marker_for_company(company)
    if comp_marker:
        marker_children.append(comp_marker)
    
    # Enhanced supplier markers with agricultural monitoring data
    # Enhanced supplier markers with agricultural monitoring, climate data, and transport data
    for s in suppliers:
        if s.get("Lat") and s.get("Lon"):
            marker = marker_for_supplier(s, selected_supplier_id, show_agriculture, show_climate, show_transport)
            marker_children.append(marker)

    # Routes with proper OSRM routing and risk coloring
    route_layers = build_supplier_routes(company, suppliers, show_climate, show_transport)

    # Alert overlays (CircleMarkers) at supplier if SupplierId present, else at company
    alert_overlays = []
    suppliers_index = {s.get("SupplierId"): s for s in suppliers}
    for a in alerts:
        sev = (a.get("Severity") or "").upper()
        color = TIER_COLOR.get(sev, "#93c5fd")

        sup = suppliers_index.get(a.get("SupplierId"))

        if sup and sup.get("Lat") and sup.get("Lon"):
            lat, lon = sup["Lat"], sup["Lon"]
        else:
            # Fallback: place at company HQ if no supplier available
            if company and company.get("Lat") and company.get("Lon"):
                lat, lon = company["Lat"], company["Lon"]
            else:
                # As a last resort, skip if no coordinates at all
                continue

        alert_overlays.append(
            dl.CircleMarker(
                center=(lat, lon),
                radius=14,
                color=color,
                fill=True,
                fillOpacity=0.45,
            )
        )

    # Base layers
    children = [
        dl.TileLayer(
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )
    ]
    
    # Add overlays based on toggles
    if show_agriculture:
        print("🌱 Adding agriculture satellite overlay")
        agriculture_layer = create_satellite_overlay()
        if agriculture_layer:
            children.append(agriculture_layer)
    
    if show_climate:
        print("🌡️ Adding climate heatmap overlay")
        climate_layer = create_climate_overlay()
        if climate_layer:
            children.append(climate_layer)
            print("✅ Climate heatmap overlay added to map")
            
            # Add climate heatmap legend
            legend = html.Div([
                html.Div("🌡️ Climate Heatmap Active", 
                        className="bg-primary text-white px-2 py-1 rounded",
                        style={"fontSize": "12px", "fontWeight": "bold"})
            ], style={
                "position": "absolute", 
                "top": "10px", 
                "right": "10px", 
                "zIndex": "1000"
            })
            children.append(legend)
        else:
            print("❌ Failed to create climate heatmap overlay")
    
    # Add other layers
    children.extend([
        dl.LayerGroup(alert_overlays, id="alert-overlays"),
        dl.LayerGroup(marker_children, id="entity-markers"),
        dl.LayerGroup(route_layers, id="route-layers"),
    ])
    
    # Add legend table for active mode
    if show_yield_shortage or show_agriculture or show_climate or show_transport:
        legend_table = create_legend_table(show_yield_shortage, show_agriculture, show_climate, show_transport)
        if legend_table:
            children.append(legend_table)
    
    # Center on Zurich with appropriate zoom level
    # Keep map ID stable to prevent recentering
    return dl.Map(
        id="main-map",
        center=(47.3769, 8.5417), 
        zoom=8, 
        children=children, 
        style={"height": "calc(100vh - 80px)", "width": "100%"}
    )



def create_satellite_overlay():
    """Create satellite tile overlay for the region"""
    try:
        # This would fetch the tile URL from Google Earth Engine
        # For now, return a placeholder that could be replaced with actual satellite tiles
        return dl.TileLayer(
            url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",  # Google Satellite as placeholder
            attribution='Satellite imagery',
            opacity=0.7,
            id="satellite-overlay"
        )
    except Exception as e:
        print(f"Error creating satellite overlay: {e}")
        return None

def create_climate_overlay():
    """Create climate/weather overlay for the region"""
    try:
        print("🌡️ Creating climate heatmap overlay...")
        
        # Try to get real climate heatmap from your GEE backend
        response = requests.get(f"{API_BASE_URL}/satellite/climate/heatmap/swiss")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("temperature_tiles"):
                # Use real GEE climate data
                print("✅ Using real GEE climate heatmap overlay")
                return dl.TileLayer(
                    url=data["temperature_tiles"]["url"],
                    attribution=data["temperature_tiles"]["attribution"],
                    opacity=0.7,  # More visible
                    id="gee-climate-overlay"
                )
        
        # Fallback to OpenWeatherMap precipitation overlay
        print("⚠️ Using fallback weather radar overlay")
        return dl.TileLayer(
            url="https://tile.openweathermap.org/map/precipitation_new/{z}/{x}/{y}.png?appid=demo",
            attribution='Weather data © OpenWeatherMap',
            opacity=0.7,  # More visible
            id="climate-overlay"
        )
    except Exception as e:
        print(f"❌ Error creating climate overlay: {e}")
        # Final fallback to temperature overlay
        return dl.TileLayer(
            url="https://tile.openweathermap.org/map/temp_new/{z}/{x}/{y}.png?appid=demo",
            attribution='Temperature data © OpenWeatherMap',
            opacity=0.6,
            id="climate-overlay-fallback"
        )

def create_legend_table(show_yield_shortage: bool = False, show_agriculture: bool = False, show_climate: bool = False, show_transport: bool = False):
    """Create legend table showing color meanings and value ranges"""
    
    if show_yield_shortage:
        # 2026 Yield Shortage Legend
        legend_data = [
            {"color": "#ef4444", "emoji": "🔴", "risk": "RISK", "conditions": "Estimated < Requested", "impact": "Yield shortage expected"},
            {"color": "#22c55e", "emoji": "🟢", "risk": "SAFE", "conditions": "Estimated ≥ Requested", "impact": "Sufficient yield projected"}
        ]
        
        title = "🌾 2026 Wheat Yield Legend"
        headers = ["", "Status", "Condition", "Impact"]
        
    elif show_transport:
        # Traffic/Logistics Legend
        legend_data = [
            {"color": "#ef4444", "risk": "HEAVY", "conditions": "Delay > 25 minutes", "impact": "Significant delays expected"},
            {"color": "#f59e0b", "risk": "MODERATE", "conditions": "Delay 10-25 minutes", "impact": "Some delays possible"},
            {"color": "#22c55e", "risk": "LIGHT", "conditions": "Delay < 10 minutes", "impact": "Normal travel time"}
        ]
        
        title = "🚛 Traffic & Logistics Legend"
        headers = ["", "Traffic Level", "Delay Range", "Logistics Impact"]
        
    elif show_climate:
        # Climate/Transport Risk Legend
        legend_data = [
            {"color": "#ef4444", "emoji": "🔴", "risk": "HIGH", "conditions": "Temp < -2°C or > 32°C, Precip > 20mm", "impact": "Major delays expected"},
            {"color": "#f59e0b", "emoji": "🟡", "risk": "MEDIUM", "conditions": "Temp 0-2°C or 28-32°C, Precip 10-20mm", "impact": "Moderate delays possible"},
            {"color": "#22c55e", "emoji": "🟢", "risk": "LOW", "conditions": "Favorable weather conditions", "impact": "Normal operations"}
        ]
        
        title = "🌡️ Transport Risk Legend"
        headers = ["", "Risk Level", "Weather Conditions", "Transport Impact"]
        
    elif show_agriculture:
        # Agriculture/NDVI Legend
        legend_data = [
            {"color": "#22c55e", "emoji": "🟢", "risk": "HEALTHY", "conditions": "NDVI > 0.7", "impact": "Excellent crop health"},
            {"color": "#f59e0b", "emoji": "🟡", "risk": "MODERATE", "conditions": "NDVI 0.5 - 0.7", "impact": "Good vegetation"},
            {"color": "#f97316", "emoji": "🟠", "risk": "STRESSED", "conditions": "NDVI 0.3 - 0.5", "impact": "Crop stress detected"},
            {"color": "#ef4444", "emoji": "🔴", "risk": "CRITICAL", "conditions": "NDVI < 0.3", "impact": "Poor crop health"}
        ]
        
        title = "🌱 Crop Health Legend"
        headers = ["", "Health Status", "NDVI Range", "Agricultural Impact"]
    
    else:
        return None
    
    # Create table rows
    table_rows = []
    for item in legend_data:
        row = html.Tr([
            html.Td([
                html.Div(style={
                    "width": "20px",
                    "height": "20px", 
                    "backgroundColor": item["color"],
                    "borderRadius": "50%",
                    "display": "inline-block",
                    "border": "2px solid white",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.2)"
                })
            ], style={"textAlign": "center", "verticalAlign": "middle"}),
            html.Td(html.Strong(item["risk"]), style={"verticalAlign": "middle"}),
            html.Td(item["conditions"], style={"fontSize": "12px", "verticalAlign": "middle"}),
            html.Td(item["impact"], style={"fontSize": "12px", "verticalAlign": "middle"})
        ])
        table_rows.append(row)
    
    # Create the legend table
    legend_table = html.Div([
        html.Div([
            html.H6(title, className="mb-2 text-center", style={"color": "#1f2937", "fontWeight": "bold"}),
            html.Table([
                html.Thead([
                    html.Tr([
                        html.Th(header, style={
                            "fontSize": "11px", 
                            "fontWeight": "bold", 
                            "color": "#374151",
                            "borderBottom": "2px solid #e5e7eb",
                            "padding": "8px 4px"
                        }) for header in headers
                    ])
                ]),
                html.Tbody(table_rows)
            ], className="table table-sm", style={
                "backgroundColor": "white",
                "fontSize": "11px",
                "margin": "0"
            })
        ], style={
            "backgroundColor": "rgba(255, 255, 255, 0.95)",
            "border": "1px solid #d1d5db",
            "borderRadius": "8px",
            "padding": "12px",
            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "backdropFilter": "blur(4px)"
        })
    ], style={
        "position": "absolute",
        "bottom": "20px",
        "right": "20px",
        "zIndex": "1000",
        "maxWidth": "400px",
        "minWidth": "350px"
    })
    
    return legend_table

def get_mock_ndvi_for_supplier(supplier_id: int) -> float:
    """Mock NDVI data - replace with actual API call"""
    import random
    
    # Set seed based on supplier ID for consistent values
    random.seed(supplier_id)
    
    # Generate realistic NDVI values with some variation
    base_values = [0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]  # Range from critical to healthy
    base_ndvi = random.choice(base_values)
    
    # Add small random variation
    variation = random.uniform(-0.05, 0.05)
    ndvi = max(0.1, min(0.95, base_ndvi + variation))
    
    return round(ndvi, 3)

def get_ndvi_status(ndvi: float) -> str:
    """Convert NDVI value to status text"""
    if ndvi > 0.7:
        return "Healthy Vegetation"
    elif ndvi > 0.5:
        return "Moderate Vegetation"
    elif ndvi > 0.3:
        return "Stressed Vegetation"
    else:
        return "Critical Vegetation"

def get_traffic_data_for_supplier(supplier_id: int) -> Dict:
    """Get real-time traffic data from backend"""
    try:
        # Call traffic API endpoint
        response = requests.get(f"{API_BASE_URL}/satellite/traffic/route/{supplier_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                traffic = data["traffic"]
                
                return {
                    "traffic_level": traffic["level"],
                    "color": traffic["color"],
                    "delay_minutes": traffic["delay_minutes"],
                    "delay_percentage": traffic["delay_percentage"],
                    "duration_normal": traffic["duration_normal_minutes"],
                    "duration_traffic": traffic["duration_traffic_minutes"],
                    "recommendation": data["recommendation"]
                }
        
        # Fallback to mock data if API fails
        print(f"Traffic API failed for supplier {supplier_id}, using fallback")
        return get_mock_traffic_data_for_supplier(supplier_id)
        
    except Exception as e:
        print(f"Error getting traffic data for supplier {supplier_id}: {e}")
        return get_mock_traffic_data_for_supplier(supplier_id)

def get_mock_traffic_data_for_supplier(supplier_id: int) -> Dict:
    """Fallback mock traffic data"""
    import random
    
    # Set seed for consistent results
    random.seed(supplier_id * 123)
    
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
    
    base_time = 120  # 2 hours base
    
    return {
        "traffic_level": traffic_level,
        "color": color,
        "delay_minutes": round(delay_minutes, 1),
        "delay_percentage": round((delay_minutes / base_time) * 100, 1),
        "duration_normal": base_time,
        "duration_traffic": base_time + delay_minutes,
        "recommendation": f"{traffic_level.title()} traffic - {delay_minutes:.0f} min delay"
    }

def get_climate_risk_for_supplier(supplier_id: int) -> Dict:
    """Get real climate risk data from GEE backend"""
    try:
        # Call your existing climate API endpoint
        response = requests.get(f"{API_BASE_URL}/satellite/climate/supplier/{supplier_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                climate = data["climate"]
                transport = data["transport_impact"]
                
                return {
                    "risk_level": climate["risk_level"],
                    "temp": climate["temperature_celsius"],
                    "precip": climate["precipitation_mm"],
                    "risk_factors": climate["risk_factors"],
                    "impact": transport["impact_description"],
                    "delay_factor": transport["delay_factor"],
                    "additional_delay_minutes": transport["additional_delay_minutes"],
                    "recommendation": transport["recommended_action"]
                }
            else:
                # API returned success: false (e.g., supplier not in climate monitoring list)
                if supplier_id <= 10:  # Only log for expected suppliers
                    print(f"Climate data not available for supplier {supplier_id}: {data.get('message', 'Unknown reason')}")
                return get_mock_climate_risk_for_supplier(supplier_id)
        
        # Fallback to mock data if API fails (reduced logging)
        return get_mock_climate_risk_for_supplier(supplier_id)
        
    except Exception as e:
        # Silent fallback for better UX
        return get_mock_climate_risk_for_supplier(supplier_id)

def get_traffic_data_for_supplier(supplier_id: int) -> Dict:
    """Get real-time traffic data from backend"""
    try:
        # Call traffic API endpoint
        response = requests.get(f"{API_BASE_URL}/satellite/traffic/route/{supplier_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                traffic = data["traffic"]
                
                return {
                    "traffic_level": traffic["level"],
                    "color": traffic["color"],
                    "delay_minutes": traffic["delay_minutes"],
                    "delay_percentage": traffic["delay_percentage"],
                    "duration_normal": traffic["duration_normal_minutes"],
                    "duration_traffic": traffic["duration_traffic_minutes"],
                    "recommendation": data["recommendation"]
                }
        
        # Fallback to mock data if API fails
        print(f"Traffic API failed for supplier {supplier_id}, using fallback")
        return get_mock_traffic_data_for_supplier(supplier_id)
        
    except Exception as e:
        print(f"Error getting traffic data for supplier {supplier_id}: {e}")
        return get_mock_traffic_data_for_supplier(supplier_id)

def get_mock_traffic_data_for_supplier(supplier_id: int) -> Dict:
    """Fallback mock traffic data"""
    import random
    
    # Set seed for consistent results
    random.seed(supplier_id * 123)
    
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
    
    base_time = 120  # 2 hours base
    
    return {
        "traffic_level": traffic_level,
        "color": color,
        "delay_minutes": round(delay_minutes, 1),
        "delay_percentage": round((delay_minutes / base_time) * 100, 1),
        "duration_normal": base_time,
        "duration_traffic": base_time + delay_minutes,
        "recommendation": f"{traffic_level.title()} traffic - {delay_minutes:.0f} min delay"
    }

def get_mock_climate_risk_for_supplier(supplier_id: int) -> Dict:
    """Fallback mock climate risk data"""
    import random
    
    # Set seed for consistent results
    random.seed(supplier_id * 42)
    
    # Generate realistic weather conditions
    temp = random.uniform(-5, 35)  # Temperature range for Central Europe
    precip = random.uniform(0, 30)  # Precipitation in mm
    
    # Assess risk based on conditions
    risk_factors = []
    
    if temp < 0:
        risk_factors.append("Freezing conditions")
    elif temp > 30:
        risk_factors.append("High temperature")
    
    if precip > 15:
        risk_factors.append("Heavy precipitation")
    elif precip > 5:
        risk_factors.append("Moderate precipitation")
    
    # Determine overall risk level
    if (temp < -2 or temp > 32) or precip > 20:
        risk_level = "HIGH"
        impact = "Significant transport delays expected"
    elif (temp < 2 or temp > 28) or precip > 10:
        risk_level = "MEDIUM"
        impact = "Moderate transport delays possible"
    else:
        risk_level = "LOW"
        impact = "Normal transport conditions"
    
    return {
        "risk_level": risk_level,
        "temp": round(temp, 1),
        "precip": round(precip, 1),
        "risk_factors": risk_factors,
        "impact": impact,
        "delay_factor": 1.0,
        "additional_delay_minutes": 0,
        "recommendation": "Normal operations"
    }

def load_wheat_data():
    """Load wheat data from CSV file"""
    try:
        import pandas as pd
        import os
        
        # Try multiple possible paths for the CSV file
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data-science", "Wheat_estimated_requested.csv"),
            os.path.join("data-science", "Wheat_estimated_requested.csv"),
            os.path.join("..", "data-science", "Wheat_estimated_requested.csv"),
            "data-science/Wheat_estimated_requested.csv"
        ]
        
        csv_path = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break
        
        if not csv_path:
            print(f"❌ CSV file not found. Tried paths: {possible_paths}")
            # Return some mock wheat data for testing
            return [
                {
                    "id": "wheat_test_1",
                    "name": "Test Wheat Farm - Bern",
                    "location": "Bern",
                    "latitude": 46.9481,
                    "longitude": 7.4474,
                    "estimated_yield": 25000,
                    "requested_yield": 27000,
                    "yield_shortage": -2000,
                    "is_risk": True,
                    "ndvi": 0.3,
                    "temperature": 10.5,
                    "precipitation": 5.2
                },
                {
                    "id": "wheat_test_2", 
                    "name": "Test Wheat Farm - Zurich",
                    "location": "Zurich",
                    "latitude": 47.3769,
                    "longitude": 8.5417,
                    "estimated_yield": 30000,
                    "requested_yield": 25000,
                    "yield_shortage": 5000,
                    "is_risk": False,
                    "ndvi": 0.7,
                    "temperature": 12.1,
                    "precipitation": 3.8
                }
            ]
        
        print(f"📂 Loading wheat data from: {csv_path}")
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"📊 CSV loaded with {len(df)} rows")
        
        # Convert to list of dictionaries for easier processing
        wheat_suppliers = []
        for index, row in df.iterrows():
            # Calculate risk based on yield shortage
            estimated_yield = row['estimated_yield']
            requested_yield = row['requested_yield']
            yield_shortage = estimated_yield - requested_yield
            is_risk = yield_shortage < 0
            
            wheat_suppliers.append({
                "id": f"wheat_{index}",
                "name": f"Wheat Farm - {row['Standort']}",
                "location": row['Standort'],
                "latitude": row['Latitude'],
                "longitude": row['Longitude'],
                "estimated_yield": estimated_yield,
                "requested_yield": requested_yield,
                "yield_shortage": yield_shortage,
                "is_risk": is_risk,
                "ndvi": row.get('ndvi', 0),
                "temperature": row.get('tavg', 0),
                "precipitation": row.get('prcp', 0)
            })
        
        # Count risk vs safe for debugging
        risk_count = sum(1 for s in wheat_suppliers if s['is_risk'])
        safe_count = len(wheat_suppliers) - risk_count
        print(f"✅ Loaded {len(wheat_suppliers)} wheat suppliers: {risk_count} RISK (🔴), {safe_count} SAFE (🟢)")
        
        return wheat_suppliers
        
    except Exception as e:
        print(f"❌ Error loading wheat data: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_yield_shortage_risk_for_supplier(supplier_id: int) -> Dict:
    """Get 2026 yield shortage risk prediction for supplier"""
    import random
    
    # Set seed for consistent results per supplier
    random.seed(supplier_id * 2026)
    
    # Define risk factors and affected crops based on supplier characteristics
    risk_factors_pool = [
        "Climate change impact", "Drought conditions", "Soil degradation", 
        "Water scarcity", "Extreme weather events", "Pest pressure increase",
        "Temperature fluctuations", "Seasonal pattern shifts", "Supply chain disruption"
    ]
    
    crops_pool = [
        "wheat", "corn", "soybeans", "rice", "potatoes", "vegetables", 
        "dairy", "grapes", "organic produce", "specialty crops"
    ]
    
    # Generate risk level based on supplier ID patterns
    if supplier_id in [4, 10]:  # Organic Harvest Co, Tyrolean Mountain Farms
        risk_level = "CRITICAL"
        yield_impact = random.randint(35, 50)
        timeline = "Q2 2026 - Immediate action required"
        mitigation = "Diversify suppliers immediately, secure alternative sources"
    elif supplier_id in [2, 7, 9, 25, 31, 42]:  # Various risk suppliers
        risk_level = "HIGH" 
        yield_impact = random.randint(20, 35)
        timeline = "Q3 2026 - Monitor closely"
        mitigation = "Develop contingency plans, increase monitoring"
    elif supplier_id in [18, 23, 34]:  # Some stable suppliers with medium risk
        risk_level = "MEDIUM"
        yield_impact = random.randint(10, 20)
        timeline = "Q4 2026 - Prepare alternatives"
        mitigation = "Regular assessment, backup supplier identification"
    else:  # Most suppliers have low risk
        risk_level = "LOW"
        yield_impact = random.randint(0, 10)
        timeline = "2027+ - Long-term monitoring"
        mitigation = "Continue current practices, periodic review"
    
    # Select random risk factors and crops
    num_factors = random.randint(2, 4)
    selected_factors = random.sample(risk_factors_pool, num_factors)
    
    num_crops = random.randint(1, 3)
    selected_crops = random.sample(crops_pool, num_crops)
    
    return {
        "risk_level": risk_level,
        "yield_impact": yield_impact,
        "affected_crops": selected_crops,
        "risk_factors": selected_factors,
        "timeline": timeline,
        "mitigation": mitigation
    }

def recommendations_panel(recs: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):
    items = []
    for r in recs.get("alternatives", []) or recs.get("recommendations", []):
        supplier_name = r.get("name") or r.get("supplier")
        reasoning = r.get("reasoning", "")

        sup = suppliers_index.get(r.get("supplierId")) or {"Name": supplier_name}
        display_name = sup.get("Name") or supplier_name or "Unknown Supplier"

        items.append(
            dbc.Card(
                dbc.CardBody([
                    html.H6(display_name, className="fw-bold mb-1"),
                    html.Small(reasoning, className="text-muted d-block"),
                ]),
                className="mb-2 shadow-sm border-0"
            )
        )

    if not items:
        items = [dbc.Alert("No recommendations available.", color="secondary", className="mb-0")]

    return html.Div(items)


def alert_card(a: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):
    """Compact alert card for dropdown display."""
    sev_key = (a.get("Severity") or "STABLE").upper()
    sev = SEVERITY_BADGE.get(sev_key, SEVERITY_BADGE["STABLE"])
    sup = suppliers_index.get(a.get("SupplierId")) or {"Name": f"Supplier {a.get('SupplierId')}"}
    
    # Get message
    det = a.get("Details") or {}
    message = det.get("message") or a.get("Title") or "No details available"
    
    return html.Div([
        html.Div([
            dbc.Badge(sev["text"], color=sev["color"], className="me-2", style={"fontSize": "0.7em"}),
            html.Span(a.get("Title", "Alert"), className="fw-semibold text-white", style={"fontSize": "0.9em"})
        ], className="d-flex align-items-center mb-1"),
        
        html.Div([
            html.Small(sup.get('Name', 'Unknown Supplier'), className="text-blue-300 me-2"),
            html.Small(f"• {a.get('CropId', 'Unknown').title()}", className="text-gray-400")
        ], className="d-flex align-items-center mb-1"),
        
        html.P(message, className="text-gray-300 mb-0", style={
            "fontSize": "0.8em",
            "lineHeight": "1.3",
            "maxHeight": "2.6em",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "display": "-webkit-box",
            "WebkitLineClamp": "2",
            "WebkitBoxOrient": "vertical"
        })
    ], style={
        "padding": "12px",
        "borderBottom": "1px solid rgba(59, 130, 246, 0.2)",
        "cursor": "pointer",
        "transition": "all 0.2s ease"
    }, className="alert-dropdown-item")


def risk_timeline_placeholder():
    fig = go.Figure()
    x = [dt.date.today() + dt.timedelta(days=i) for i in range(14)]
    y = [min(100, max(0, 40 + 20*math.sin(i/3))) for i in range(14)]
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name="Risk Index"))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=220, yaxis_title="Risk (0-100)")
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ----------------------------
# Transport params + Routing helpers
# ----------------------------
COST_PER_KM_BY_MODE = {"Truck": 1.2, "Train": 0.6}
CO2_PER_TKM_BY_MODE = {"Truck": 0.12, "Train": 0.04}  # t CO2 per tonne-km
SPEED_KMPH_BY_MODE = {"Truck": 60.0, "Train": 80.0}


# ----------------------------
# Alert building from API data
# ----------------------------

def build_alerts_from_api(company_id: Optional[int], token: str) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []

    mappings = get_company_mappings(token)
    if not isinstance(mappings, list):
        return alerts

    filtered = [m for m in mappings if (company_id is None or m.get("company_id") == company_id)]
    for m in filtered:
        stock_id = m.get("stock_id")
        if stock_id is None:
            continue
        stock = get_stock(stock_id, token)
        if not isinstance(stock, dict) or stock.get("error"):
            continue

        crop_type = stock.get("crop_type")
        risk_class = stock.get("risk_class")
        message = stock.get("message")
        expiry_date = stock.get("expiry_date")
        supplier_id = stock.get("supplier_id")

        created_at = stock.get("created_at") or dt.datetime.utcnow().isoformat()

        alerts.append({
            "AlertId": f"stock-{stock_id}",
            "CompanyId": company_id,
            "SupplierId": supplier_id,
            "CropId": crop_type,
            "CreatedAt": created_at,
            "Severity": risk_class,
            "Title": f"{crop_type.title() if crop_type else 'Crop'} alert",
            "Details": {
                "risk_class": risk_class,
                "why": message,
                "expiry_date": expiry_date,
                "mapping_id": m.get("id"),
                "transportation_mode": m.get("transportation_mode"),
            },
        })
    return alerts



# ----------------------------
# Dash App
# ----------------------------
app = Dash(__name__, 
          external_stylesheets=[
              dbc.themes.BOOTSTRAP,
              "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
              "/assets/custom.css"
          ], 
          suppress_callback_exceptions=True)
server = app.server
app.title = "NASA Supply Chain Analytics Platform"

# Disable dev tools
app.config.suppress_callback_exceptions = True




# Elegant NASA-themed layout with starfield background
app.layout = html.Div([
    dcc.Store(id="token-store", data="mock-token"),  # Auto-login with mock token
    dcc.Store(id="selected-supplier-id"),
    dcc.Store(id="suppliers-data-store"),  # Cache suppliers data
    dcc.Store(id="map-toggle-state"),  # Store toggle states
    dcc.Store(id="analytics-state", data={"show": False}),  # Analytics panel state
    
    # Animated starfield background
    html.Div(id="starfield", children=[
        html.Div(className="star", style={
            "left": f"{i*7 % 100}%", 
            "top": f"{i*11 % 100}%",
            "animationDelay": f"{i*0.1}s"
        }) for i in range(200)
    ]),
    
    # Main dashboard - no login required
    dbc.Container([
        # Header with NASA branding
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-satellite me-3"),
                    "NASA Supply Chain Analytics Platform"
                ], className="text-white fw-bold mb-1", style={"textShadow": "2px 2px 4px rgba(0,0,0,0.5)"}),
                html.H5("Welcome Swiss Corp", className="fw-light mb-0", style={"color": "#60a5fa", "textShadow": "1px 1px 2px rgba(0,0,0,0.5)"})
            ], md=8),
            dbc.Col([
                # Header icons - sleek and elegant
                html.Div([
                    # Bell icon button with count
                    html.Div([
                        dbc.Button([
                            html.I(className="fas fa-bell", style={
                                "color": "#ef4444", 
                                "fontSize": "20px"
                            })
                        ], id="alerts-toggle", 
                        color="link",
                        style={
                            "backgroundColor": "transparent",
                            "border": "none",
                            "padding": "8px",
                            "boxShadow": "none"
                        }),
                        dbc.Badge("7", color="danger", className="position-absolute", style={
                            "fontSize": "0.6em",
                            "top": "0px",
                            "right": "0px",
                            "minWidth": "18px",
                            "height": "18px",
                            "borderRadius": "50%",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "zIndex": "10"
                        })
                    ], className="me-4 position-relative", style={
                        "display": "inline-block"
                    }),
                    
                    # Chat/Message button
                    dbc.Button([
                        html.I(className="fas fa-comment-dots", style={
                            "color": "#10b981", 
                            "fontSize": "20px"
                        })
                    ], id="chat-toggle", className="me-4",
                    color="link",
                    style={
                        "backgroundColor": "transparent",
                        "border": "none",
                        "padding": "8px",
                        "boxShadow": "none"
                    }),
                    
                    # Dropdown/Menu button for indicators
                    dbc.Button([
                        html.I(className="fas fa-bars", style={
                            "color": "#f59e0b", 
                            "fontSize": "20px"
                        })
                    ], id="indicators-toggle", className="me-4",
                    color="link",
                    style={
                        "backgroundColor": "transparent",
                        "border": "none",
                        "padding": "8px",
                        "boxShadow": "none"
                    }),
                    
                    # Analytics/Dashboard button
                    dbc.Button([
                        html.I(className="fas fa-chart-bar", style={
                            "color": "#e5e7eb", 
                            "fontSize": "20px"
                        })
                    ], id="analytics-toggle", className="me-2",
                    color="link",
                    style={
                        "backgroundColor": "transparent",
                        "border": "none",
                        "padding": "8px",
                        "boxShadow": "none"
                    })
                ], className="d-flex justify-content-end align-items-center", style={
                    "paddingRight": "10px"
                })
            ], md=4)
        ], className="mb-3 pt-3"),
        
        # Main content area - Full screen map
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="map-loading",
                    type="default",
                    color="#60a5fa",
                    children=[
                        html.Div(id="map-container", style={"minHeight": "calc(100vh - 80px)"}),
                        
                        # Analytics Dashboard Panel (hidden by default)
                        html.Div(id="analytics-dashboard", style={"display": "none"})
                    ],
                    custom_spinner=html.Div([
                        html.Div([
                            # Rocket with exhaust flames
                            html.Div([
                                html.I(className="fas fa-rocket", style={
                                    "fontSize": "48px",
                                    "color": "#60a5fa",
                                    "position": "relative",
                                    "zIndex": "2"
                                }),
                                # Exhaust flames
                                html.Div(className="rocket-exhaust", style={
                                    "position": "absolute",
                                    "bottom": "-20px",
                                    "left": "50%",
                                    "transform": "translateX(-50%)",
                                    "width": "20px",
                                    "height": "30px",
                                    "background": "linear-gradient(to bottom, #f97316, #ef4444, transparent)",
                                    "borderRadius": "50% 50% 50% 50% / 60% 60% 40% 40%",
                                    "animation": "flameFlicker 0.3s ease-in-out infinite alternate"
                                }),
                                # Smoke trail
                                html.Div(className="smoke-trail", style={
                                    "position": "absolute",
                                    "bottom": "-50px",
                                    "left": "50%",
                                    "transform": "translateX(-50%)",
                                    "width": "8px",
                                    "height": "40px",
                                    "background": "linear-gradient(to bottom, rgba(156, 163, 175, 0.6), transparent)",
                                    "borderRadius": "50%",
                                    "animation": "smokeRise 2s ease-out infinite"
                                })
                            ], style={
                                "position": "relative",
                                "animation": "rocketLaunch 3s ease-in-out infinite"
                            })
                        ], style={
                            "position": "relative",
                            "height": "100px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center"
                        }),
                        html.Div("Launching...", style={
                            "color": "#60a5fa",
                            "marginTop": "30px",
                            "fontSize": "18px",
                            "fontWeight": "300",
                            "letterSpacing": "1px",
                            "animation": "textPulse 2s ease-in-out infinite"
                        })
                    ], style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "height": "250px"
                    })
                )
            ], md=12, className="p-0 position-relative")
        ], className="g-0"),
        
        # Elegant alerts dropdown
        dbc.Collapse([
            html.Div([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-bell me-2", style={"color": "#ef4444"}),
                        "Alerts"
                    ], className="mb-2 text-white fw-bold"),
                    html.Div(id="alerts-list", style={
                        "maxHeight": "350px", 
                        "overflowY": "auto",
                        "overflowX": "hidden"
                    })
                ], style={
                    "padding": "16px",
                    "backgroundColor": "rgba(15, 23, 42, 0.95)",
                    "backdropFilter": "blur(20px)",
                    "border": "1px solid rgba(59, 130, 246, 0.3)",
                    "borderRadius": "12px",
                    "boxShadow": "0 20px 40px rgba(0, 0, 0, 0.3)",
                    "minWidth": "320px",
                    "maxWidth": "400px"
                })
            ], style={
                "position": "fixed",
                "top": "70px",
                "right": "20px",
                "zIndex": "9999",
                "animation": "slideDown 0.3s ease-out"
            })
        ], id="alerts-collapse", is_open=False),
        
        # Risk Factors dropdown
        dbc.Collapse([
            html.Div([
                # Header
                html.H6([
                    html.I(className="fas fa-bars me-2", style={"color": "#f59e0b"}),
                    "Risk Factors"
                ], className="mb-3 text-white fw-bold"),
                
                # 2026 Yield Shortage (NEW - First priority)
                html.Div([
                    dbc.Switch(
                        id="yield-shortage-toggle", 
                        value=False,
                        label="2026 Yield Shortage",
                        style={"color": "white"}
                    )
                ], className="mb-2"),

                # Climate and Transportation Logistics
                html.Div([
                    dbc.Switch(
                        id="climate-toggle", 
                        value=False,
                        label="Climate and Transportation Logistics",
                        style={"color": "white"}
                    )
                ], className="mb-2"),
                

                # Agricultural Monitoring  
                html.Div([
                    dbc.Switch(
                        id="agriculture-toggle", 
                        value=True,
                        label="Agricultural Monitoring",
                        style={"color": "white"}
                    )
                ], className="mb-2"),
                
                # Transportation & Logistics
                html.Div([
                    dbc.Switch(
                        id="transport-toggle", 
                        value=False,
                        label="Transportation & Logistics",
                        style={"color": "white"}
                    )
                ])
                
            ], style={
                "position": "fixed",
                "top": "70px",
                "right": "180px",
                "zIndex": "9999",
                "padding": "16px",
                "backgroundColor": "rgba(15, 23, 42, 0.95)",
                "backdropFilter": "blur(20px)",
                "border": "1px solid rgba(245, 158, 11, 0.3)",
                "borderRadius": "12px",
                "boxShadow": "0 20px 40px rgba(0, 0, 0, 0.3)",
                "minWidth": "320px",
                "animation": "slideDown 0.3s ease-out"
            })
        ], id="indicators-collapse", is_open=False),
        
        # Chat Assistant Panel
        dbc.Collapse([
            html.Div([
                # Chat Header
                html.Div([
                    html.H6([
                        html.I(className="fas fa-comment-dots me-2", style={"color": "#10b981"}),
                        "Swiss Corp Assistant"
                    ], className="mb-0 text-white fw-bold"),
                    dbc.Button([
                        html.I(className="fas fa-times")
                    ], color="link", size="sm", id="chat-close", style={
                        "color": "white", 
                        "padding": "0",
                        "border": "none"
                    })
                ], className="d-flex justify-content-between align-items-center mb-3"),
                
                # Chat Messages Area
                html.Div(id="chat-messages", children=[
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-robot me-2", style={"color": "#10b981"}),
                            html.Div([
                                html.Span("Hello! I'm your Swiss Corp supply chain assistant with real-time risk data.", 
                                         className="text-white", style={"fontSize": "0.9em"}),
                                html.Br(),
                                html.Small("Try these sample questions:", className="text-muted", style={"fontSize": "0.8em"}),
                                html.Div([
                                    # Sample prompt tiles
                                    html.Div([
                                        html.I(className="fas fa-exclamation-triangle me-1", style={"color": "#ef4444"}),
                                        html.Span("Should we replace Organic Harvest Co due to drought?", 
                                                 className="text-white", style={"fontSize": "0.75em"})
                                    ], id="sample-prompt-1", className="sample-prompt-tile", style={
                                        "backgroundColor": "rgba(239, 68, 68, 0.1)",
                                        "border": "1px solid rgba(239, 68, 68, 0.3)",
                                        "borderRadius": "6px",
                                        "padding": "6px 8px",
                                        "margin": "4px 0",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "color": "white"
                                    }),
                                    html.Div([
                                        html.I(className="fas fa-truck me-1", style={"color": "#3b82f6"}),
                                        html.Span("Which suppliers have the best transport reliability?", 
                                                 className="text-white", style={"fontSize": "0.75em"})
                                    ], id="sample-prompt-2", className="sample-prompt-tile", style={
                                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                                        "border": "1px solid rgba(59, 130, 246, 0.3)",
                                        "borderRadius": "6px",
                                        "padding": "6px 8px",
                                        "margin": "4px 0",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "color": "white"
                                    }),
                                    html.Div([
                                        html.I(className="fas fa-clock me-1", style={"color": "#f59e0b"}),
                                        html.Span("What's causing delays from Bavarian Grain Collective?", 
                                                 className="text-white", style={"fontSize": "0.75em"})
                                    ], id="sample-prompt-3", className="sample-prompt-tile", style={
                                        "backgroundColor": "rgba(245, 158, 11, 0.1)",
                                        "border": "1px solid rgba(245, 158, 11, 0.3)",
                                        "borderRadius": "6px",
                                        "padding": "6px 8px",
                                        "margin": "4px 0",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "color": "white"
                                    }),
                                    html.Div([
                                        html.I(className="fas fa-list me-1", style={"color": "#10b981"}),
                                        html.Span("List all 42 suppliers with their risk status", 
                                                 className="text-white", style={"fontSize": "0.75em"})
                                    ], id="sample-prompt-4", className="sample-prompt-tile", style={
                                        "backgroundColor": "rgba(16, 185, 129, 0.1)",
                                        "border": "1px solid rgba(16, 185, 129, 0.3)",
                                        "borderRadius": "6px",
                                        "padding": "6px 8px",
                                        "margin": "4px 0",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "color": "white"
                                    })
                                ], style={"marginTop": "8px"})
                            ])
                        ], className="d-flex align-items-start")
                    ], className="mb-2 p-2", style={
                        "backgroundColor": "rgba(16, 185, 129, 0.1)",
                        "borderRadius": "8px",
                        "border": "1px solid rgba(16, 185, 129, 0.3)"
                    })
                ], style={
                    "height": "300px",
                    "overflowY": "auto",
                    "marginBottom": "12px",
                    "padding": "8px",
                    "backgroundColor": "rgba(0, 0, 0, 0.2)",
                    "borderRadius": "8px",
                    "border": "1px solid rgba(255, 255, 255, 0.1)"
                }),
                
                # Chat Input Area
                html.Div([
                    dbc.InputGroup([
                        dbc.Input(
                            id="chat-input",
                            placeholder="Ask about agriculture risk, climate conditions, transport delays, or specific suppliers...",
                            style={
                                "backgroundColor": "rgba(255, 255, 255, 0.1)",
                                "border": "1px solid rgba(255, 255, 255, 0.2)",
                                "color": "white"
                            }
                        ),
                        dbc.Button([
                            html.I(className="fas fa-paper-plane")
                        ], id="chat-send", color="success", style={
                            "backgroundColor": "#10b981",
                            "border": "none"
                        })
                    ])
                ])
                
            ], style={
                "position": "fixed",
                "bottom": "20px",
                "right": "20px",
                "width": "400px",
                "height": "450px",
                "zIndex": "9999",
                "padding": "20px",
                "backgroundColor": "rgba(15, 23, 42, 0.95)",
                "backdropFilter": "blur(20px)",
                "border": "1px solid rgba(16, 185, 129, 0.3)",
                "borderRadius": "12px",
                "boxShadow": "0 20px 40px rgba(0, 0, 0, 0.3)",
                "animation": "slideUp 0.3s ease-out"
            })
        ], id="chat-collapse", is_open=False),
        

        
    ], fluid=True, className="h-100")
], style={
    "height": "100vh",
    "width": "100vw",
    "background": "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)",
    "position": "relative",
    "overflow": "hidden"
})


@app.callback(
    Output("selected-supplier-id", "data"),
    Input({"type": "supplier-item", "index": ALL}, "n_clicks"),
    State({"type": "supplier-item", "index": ALL}, "id"),
    State("selected-supplier-id", "data"),
    prevent_initial_call=True
)
def select_supplier(n_clicks_list, ids, current_selected):
    if not n_clicks_list:
        return current_selected

    # find the last clicked supplier (highest click count)
    clicked = [
        (n, sid["index"]) for n, sid in zip(n_clicks_list, ids) if n
    ]
    if not clicked:
        return current_selected

    # take the one with max n_clicks (most recent click)
    _, supplier_id = max(clicked, key=lambda x: x[0])

    # toggle if same as before
    if current_selected == supplier_id:
        return None
    return supplier_id

# ----------------------------------
# Alerts toggle callback
# ----------------------------------
@app.callback(
    Output("alerts-collapse", "is_open"),
    Input("alerts-toggle", "n_clicks"),
    State("alerts-collapse", "is_open")
)
def toggle_alerts(n_clicks, is_open):
    """Toggle the alerts panel visibility."""
    print(f"Alert button clicked! n_clicks: {n_clicks}, is_open: {is_open}")
    if n_clicks is None or n_clicks == 0:
        return False
    new_state = not is_open
    print(f"Setting alerts panel to: {new_state}")
    return new_state


# ----------------------------------
# Indicators dropdown callback
# ----------------------------------
@app.callback(
    Output("indicators-collapse", "is_open"),
    Input("indicators-toggle", "n_clicks"),
    State("indicators-collapse", "is_open")
)
def toggle_indicators(n_clicks, is_open):
    """Toggle the indicators dropdown visibility."""
    print(f"Indicators button clicked! n_clicks: {n_clicks}, is_open: {is_open}")
    if n_clicks is None or n_clicks == 0:
        return False
    new_state = not is_open
    print(f"Setting indicators dropdown to: {new_state}")
    return new_state


# ----------------------------------
# Data layer toggle callbacks
# ----------------------------------





# ----------------------------------
# Chat Assistant callbacks
# ----------------------------------
@app.callback(
    Output("chat-collapse", "is_open"),
    [Input("chat-toggle", "n_clicks"), Input("chat-close", "n_clicks")],
    State("chat-collapse", "is_open")
)
def toggle_chat(chat_clicks, close_clicks, is_open):
    """Toggle the chat assistant visibility."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(f"Chat button clicked: {button_id}")
    
    if button_id == "chat-toggle" and chat_clicks:
        return not is_open
    elif button_id == "chat-close" and close_clicks:
        return False
    
    return is_open

# Sample prompt click handlers
@app.callback(
    Output("chat-input", "value", allow_duplicate=True),
    [Input("sample-prompt-1", "n_clicks"),
     Input("sample-prompt-2", "n_clicks"), 
     Input("sample-prompt-3", "n_clicks"),
     Input("sample-prompt-4", "n_clicks")],
    prevent_initial_call=True
)
def handle_sample_prompt_clicks(prompt1_clicks, prompt2_clicks, prompt3_clicks, prompt4_clicks):
    """Handle clicks on sample prompt tiles."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    sample_prompts = {
        "sample-prompt-1": "Should we replace Organic Harvest Co due to drought?",
        "sample-prompt-2": "Which suppliers have the best transport reliability?", 
        "sample-prompt-3": "What's causing delays from Bavarian Grain Collective?",
        "sample-prompt-4": "List all 42 suppliers with their risk status"
    }
    
    return sample_prompts.get(button_id, "")

@app.callback(
    Output("chat-messages", "children"),
    Output("chat-input", "value"),
    [Input("chat-send", "n_clicks"), Input("chat-input", "n_submit")],
    [State("chat-input", "value"), State("chat-messages", "children")]
)
def handle_chat_message(send_clicks, input_submit, message, current_messages):
    """Handle chat messages and LangGraph integration."""
    if not message or message.strip() == "":
        return current_messages, ""
    
    # Add user message
    user_message = html.Div([
        html.Div([
            html.Span(message, className="text-white", style={"fontSize": "0.9em"}),
            html.I(className="fas fa-user ms-2", style={"color": "#60a5fa"})
        ], className="d-flex align-items-start justify-content-end")
    ], className="mb-2 p-2", style={
        "backgroundColor": "rgba(96, 165, 250, 0.1)",
        "borderRadius": "8px",
        "border": "1px solid rgba(96, 165, 250, 0.3)",
        "textAlign": "right"
    })
    
    # Generate AI response (placeholder for LangGraph integration)
    ai_response = generate_ai_response(message)
    
    ai_message = html.Div([
        html.Div([
            html.I(className="fas fa-robot me-2", style={"color": "#10b981"}),
            html.Span(ai_response, className="text-white", style={"fontSize": "0.9em"})
        ], className="d-flex align-items-start")
    ], className="mb-2 p-2", style={
        "backgroundColor": "rgba(16, 185, 129, 0.1)",
        "borderRadius": "8px",
        "border": "1px solid rgba(16, 185, 129, 0.3)"
    })
    
    # Add both messages to the chat
    updated_messages = current_messages + [user_message, ai_message]
    
    return updated_messages, ""

def generate_ai_response(user_message: str) -> str:
    """Generate AI response using OpenAI GPT with RAG context."""
    if not openai_client:
        # Provide helpful setup instructions
        if not OPENAI_AVAILABLE:
            return "🔧 **Setup Required**: OpenAI package not installed. Run: `pip install openai` in your terminal, then restart the app."
        elif not OPENAI_API_KEY:
            return "🔑 **API Key Missing**: Set your OpenAI API key with: `export OPENAI_API_KEY='your-key-here'` then restart the app. Get your key from: https://platform.openai.com/api-keys"
        else:
            return "⚠️ AI assistant is not available. Please check OpenAI configuration."
    
    # Get relevant RAG context based on user query
    rag_context = get_rag_context(user_message)
    
    # Enhanced system context with RAG data
    system_context = f"""You are an AI assistant for Swiss Corp, a supply chain management company specializing in food distribution across Central Europe.

REAL-TIME CONTEXT (from RAG system):
{rag_context}

CURRENT SUPPLY CHAIN STATUS:
- Company: Swiss Corp (HQ in Zurich, Switzerland)
- Active Suppliers: 42 suppliers across Central Europe (Switzerland: 14, Germany: 10, Austria: 8, Italy: 6, France: 6)
- Risk Monitoring: Agriculture (NDVI), Climate (Weather), Transport (Traffic)
- Current alerts: 7 total (2 high-risk, 3 medium-risk, 2 surplus opportunities)
- Crops: soybeans, potatoes, rice, dairy, grapes, wine grapes, corn, organic produce, herbs, specialty items
- Transport modes: Truck and train routes, 2-3 day average delivery

SUPPLIERS WITH RISK STATUS:
1. Fenaco Genossenschaft (Bern, Switzerland) - SURPLUS - Truck,Train
2. Alpine Farms AG (Thurgau, Switzerland) - RISK - Truck  
3. Swiss Valley Produce (Innsbruck, Austria) - SURPLUS - Truck,Train
4. Organic Harvest Co (Lucerne, Switzerland) - HIGHRISK - Truck
5. Bavarian Grain Collective (Munich, Germany) - SURPLUS - Truck,Train
6. Rhône Valley Vineyards (Geneva, Switzerland) - SURPLUS - Truck
7. Lombardy Agricultural Union (Milan, Italy) - RISK - Truck,Train
8. Black Forest Organics (Freiburg, Germany) - SURPLUS - Truck
9. Alsace Premium Produce (Strasbourg, France) - RISK - Truck,Train
10. Tyrolean Mountain Farms (Graz, Austria) - HIGHRISK - Truck

ACTIVE ALERTS:
- Critical drought conditions affecting soybean harvest (40% yield reduction)
- Storage conditions deteriorating for potatoes
- Flooding concerns in Lombardy affecting rice
- Alpine dairy disrupted by extreme weather
- Exceptional grape harvest (25% above average)
- Alsace wine grape surplus available
- Excellent corn harvest with 500t additional capacity

Use the real-time RAG context to provide specific, data-driven advice about supply chain management, risk mitigation, and operational optimization. Reference actual NDVI values, weather conditions, and traffic data when relevant. Keep responses concise and actionable."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using the more cost-effective model
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_message}
            ],
            max_tokens=400,  # Increased for more detailed responses with RAG context
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback to local responses if OpenAI fails
        return get_fallback_response_with_rag(user_message)

def get_fallback_response_with_rag(user_message: str) -> str:
    """Provide intelligent fallback responses with RAG context when OpenAI is not available."""
    message_lower = user_message.lower()
    rag_context = get_rag_context(user_message)
    
    if any(word in message_lower for word in ["agriculture", "crop", "ndvi", "farm", "harvest"]):
        ag_data = RAG_KNOWLEDGE_BASE['agriculture_risk']
        response = "🌱 **Agriculture Risk Analysis (NDVI-based)**:\n"
        response += f"**Healthy**: Fenaco (NDVI: 0.75) - {ag_data['recommendations']['healthy']}\n"
        response += f"**Stressed**: Alpine Farms (NDVI: 0.45), Tyrolean Farms (NDVI: 0.35) - {ag_data['recommendations']['stressed']}\n"
        response += f"**Critical**: Organic Harvest (NDVI: 0.25) - {ag_data['recommendations']['critical']}"
        return response
    
    elif any(word in message_lower for word in ["climate", "weather", "temperature", "rain"]):
        climate_data = RAG_KNOWLEDGE_BASE['climate_risk']
        response = "🌦️ **Climate Risk Assessment**:\n"
        response += "**Low Risk**: Fenaco (15°C, 2.5mm) - Normal operations\n"
        response += "**Medium Risk**: Alpine Farms (8°C, 15.2mm), Alsace (12°C, 8.7mm) - Some delays expected\n"
        response += "**High Risk**: Lombardy (22°C, 45.8mm) - Heavy rainfall disrupting logistics"
        return response
    
    elif any(word in message_lower for word in ["transport", "traffic", "logistics", "delivery"]):
        transport_data = RAG_KNOWLEDGE_BASE['transport_risk']
        response = "🚛 **Transport Risk Status**:\n"
        response += "**Light Traffic**: Fenaco (+3 min delay) - Optimal conditions\n"
        response += "**Moderate Traffic**: Alpine Farms (+12 min), Lombardy (+18 min) - Minor delays\n"
        response += "**Heavy Traffic**: Bavarian Grain (+25 min) - Significant delays on Munich-Zurich route"
        return response
    
    elif any(word in message_lower for word in ["supplier", "suppliers"]):
        return "📊 **Supplier Overview with Risk Data**: You have 10 active suppliers across Central Europe. **Agriculture Risk**: Organic Harvest (NDVI: 0.25, Critical). **Climate Risk**: Lombardy (High, 45.8mm rainfall). **Transport Risk**: Bavarian Grain (Heavy traffic, +25 min). Use the risk dashboards for detailed analysis."
    
    elif any(word in message_lower for word in ["alert", "alerts", "risk"]):
        return "🚨 **Multi-Risk Alert Summary**: **Agriculture**: Critical NDVI at Organic Harvest (0.25). **Climate**: High rainfall risk at Lombardy (45.8mm). **Transport**: Heavy traffic delays from Munich (+25 min). **Recommendation**: Diversify sourcing and monitor real-time conditions."
    
    elif any(word in message_lower for word in ["recommendation", "advice", "help"]):
        return "💡 **RAG-Enhanced Recommendations**: 1) **Agriculture**: Replace Organic Harvest (NDVI: 0.25) with Fenaco (NDVI: 0.75). 2) **Climate**: Avoid Lombardy routes during heavy rainfall (45.8mm). 3) **Transport**: Use alternative routes to bypass Munich traffic (+25 min delays). Real-time data available in risk dashboards."
    
    else:
        return f"🤖 **Swiss Corp RAG Assistant**: I can provide data-driven insights about '{user_message}' using our risk monitoring system. Available data: **Agriculture** (NDVI crop health), **Climate** (weather impacts), **Transport** (traffic conditions). Ask about specific suppliers or risk categories for detailed analysis. *(Note: Enhanced AI responses available with OpenAI integration)*"

def get_fallback_response(user_message: str) -> str:
    """Legacy fallback function - redirects to RAG-enhanced version."""
    return get_fallback_response_with_rag(user_message)









# ----------------------------------
# Data loading callback (only when needed)
# ----------------------------------
@app.callback(
    Output("suppliers-data-store", "data"),
    Input("token-store", "data"),
    prevent_initial_call=False
)
def load_suppliers_data(token):
    """Load suppliers data once and cache it"""
    try:
        # Get real suppliers from backend
        backend_suppliers = get_suppliers(token)
        if isinstance(backend_suppliers, list) and len(backend_suppliers) > 0:
            suppliers = backend_suppliers
            print(f"✅ Loaded {len(suppliers)} real suppliers from backend")
        else:
            suppliers = MOCK_SUPPLIERS
            print(f"⚠️ Backend unavailable, using {len(suppliers)} mock suppliers")
    except Exception as e:
        suppliers = MOCK_SUPPLIERS
        print(f"⚠️ Backend error: {e}, using {len(suppliers)} mock suppliers")
    
    # Normalize data for consistency
    normalized_suppliers = []
    for s in suppliers:
        # Handle different data structures
        supplier_id = s.get("id") or s.get("SupplierId")
        name = s.get("name") or s.get("Name")
        lat = s.get("latitude") or s.get("Lat")
        lon = s.get("longitude") or s.get("Lon")
        city = s.get("city") or s.get("City", "")
        country = s.get("country") or s.get("Country", "")
        
        # Generate a tier based on NDVI if not present
        if "tier" in s:
            tier = s["tier"]
        else:
            ndvi = get_mock_ndvi_for_supplier(supplier_id)
            if ndvi > 0.7:
                tier = "Premium"
            elif ndvi > 0.5:
                tier = "Standard"
            else:
                tier = "Basic"
        
        normalized_suppliers.append({
            "SupplierId": supplier_id,
            "Name": name,
            "Lat": lat,
            "Lon": lon,
            "Location": f"{city}, {country}".strip(", "),
            "CurrentTier": tier,
            "_raw": s
        })
    
    return normalized_suppliers

# ----------------------------------
# Map rendering callback (optimized with heavy caching)
# ----------------------------------
@app.callback(
    Output("map-container", "children"),
    [Input("suppliers-data-store", "data"),
     Input("yield-shortage-toggle", "value"),
     Input("agriculture-toggle", "value"),
     Input("climate-toggle", "value"),
     Input("transport-toggle", "value")],
    prevent_initial_call=False
)
def update_map_with_heavy_caching(suppliers_data, show_yield_shortage, show_agriculture, show_climate, show_transport):
    """Update map with aggressive caching to minimize rebuilds"""
    
    if not suppliers_data:
        return html.Div("Loading suppliers data...", className="text-white text-center p-4")
    
    # Create cache key for this exact configuration
    cache_key = f"map_v3_{len(suppliers_data)}_{show_yield_shortage}_{show_agriculture}_{show_climate}_{show_transport}"
    now = dt.datetime.now().timestamp()
    
    # Check cache first (5 second cache for debugging)
    if cache_key in _API_CACHE:
        cached_map, timestamp = _API_CACHE[cache_key]
        if now - timestamp < 5:
            print(f"🚀 Using cached map for toggles: yield={show_yield_shortage}, agri={show_agriculture}, climate={show_climate}, transport={show_transport}")
            return cached_map
    
    print(f"🔄 Building NEW map for toggles: yield={show_yield_shortage}, agri={show_agriculture}, climate={show_climate}, transport={show_transport}")
    
    # Normalize company data
    normalized_company = {
        "CompanyId": MOCK_COMPANY["id"],
        "Name": MOCK_COMPANY["name"],
        "Lat": MOCK_COMPANY["latitude"],
        "Lon": MOCK_COMPANY["longitude"],
        "City": MOCK_COMPANY["city"],
        "Country": MOCK_COMPANY["country"]
    }
    
    # Build map with current toggle states
    map_component = build_map_with_caching(normalized_company, suppliers_data, MOCK_ALERTS, None, show_yield_shortage, show_agriculture, show_climate, show_transport)
    
    # Cache the result
    _API_CACHE[cache_key] = (map_component, now)
    
    return map_component

# Toggle state management handled by clientside callback below

# ----------------------------------
# Alerts callback (separate from map)
# ----------------------------------
@app.callback(
    Output("alerts-list", "children"),
    Input("suppliers-data-store", "data"),
    prevent_initial_call=False
)
def update_alerts_list(suppliers_data):
    """Update alerts list independently of map"""
    
    if not suppliers_data:
        return []
    
    # Use mock alerts for now
    alerts = MOCK_ALERTS
    normalized_suppliers = suppliers_data
    
    # Create suppliers index for alert cards
    suppliers_index = {s["SupplierId"]: s for s in normalized_suppliers}
    
    # Sort alerts by severity
    SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "STABLE": 0}
    normalized_alerts = []
    for a in alerts:
        normalized_alerts.append({
            "SupplierId": a.get("supplier_id") or a.get("SupplierId"),
            "Severity": a["severity"].upper(),
            "Title": a["title"],
            "Details": {"message": a["message"]},
        })
    
    sorted_alerts = sorted(normalized_alerts, key=lambda x: SEVERITY_ORDER.get(x.get("Severity", "STABLE"), 0), reverse=True)
    alert_cards = [alert_card(a, suppliers_index) for a in sorted_alerts]
    
    return alert_cards

# ----------------------------------
# Clientside callbacks for instant UI updates
# ----------------------------------
# Clientside callback for instant toggle label updates
app.clientside_callback(
    """
    function(yield_value, agriculture_value, climate_value, transport_value) {
        // Update toggle states instantly on client side
        const yield_label = yield_value ? "2026 Yield Shortage: ON" : "2026 Yield Shortage: OFF";
        const agriculture_label = agriculture_value ? "Agricultural Monitoring: ON" : "Agricultural Monitoring: OFF";
        const climate_label = climate_value ? "Climate and Transportation Logistics: ON" : "Climate and Transportation Logistics: OFF";
        const transport_label = transport_value ? "Transportation & Logistics: ON" : "Transportation & Logistics: OFF";
        
        return [yield_label, agriculture_label, climate_label, transport_label];
    }
    """,
    [Output("yield-shortage-toggle", "label"),
     Output("agriculture-toggle", "label"),
     Output("climate-toggle", "label"),
     Output("transport-toggle", "label")],
    [Input("yield-shortage-toggle", "value"),
     Input("agriculture-toggle", "value"),
     Input("climate-toggle", "value"),
     Input("transport-toggle", "value")]
)

# ----------------------------------
# Analytics Dashboard Callbacks
# ----------------------------------
@app.callback(
    [Output("analytics-dashboard", "children"),
     Output("analytics-dashboard", "style")],
    Input("analytics-toggle", "n_clicks"),
    State("suppliers-data-store", "data"),
    prevent_initial_call=True
)
def toggle_analytics_dashboard(n_clicks, suppliers_data):
    """Toggle analytics dashboard visibility and create dashboards"""
    
    if not n_clicks or not suppliers_data:
        return [], {"display": "none"}
    
    # Toggle visibility (odd clicks = show, even clicks = hide)
    if n_clicks % 2 == 1:
        print("📊 Building analytics dashboards...")
        
        # Create 4 key risk dashboards
        dashboards = create_risk_analytics_dashboards(suppliers_data)
        
        return dashboards, {
            "display": "block",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100vw",
            "height": "100vh",
            "backgroundColor": "rgba(0, 0, 0, 0.95)",
            "zIndex": "9999",
            "overflowY": "auto",
            "padding": "20px"
        }
    else:
        return [], {"display": "none"}

def create_risk_analytics_dashboards(suppliers_data):
    """Create 4 comprehensive risk analytics dashboards"""
    
    # Collect data for all suppliers
    all_data = collect_all_risk_data(suppliers_data)
    
    return html.Div([
        # Header with close button
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-chart-line me-3"),
                    "Supply Chain Risk Analytics Dashboard"
                ], className="text-white fw-bold mb-4"),
            ], md=10),
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-times")
                ], id="close-analytics", color="light", size="sm", className="float-end")
            ], md=2)
        ], className="mb-4"),
        
        # 4 Key Risk Dashboards in 2x2 grid
        dbc.Row([
            dbc.Col([
                create_overall_risk_dashboard(all_data)
            ], md=6, className="mb-4"),
            dbc.Col([
                create_climate_risk_dashboard(all_data)
            ], md=6, className="mb-4")
        ]),
        dbc.Row([
            dbc.Col([
                create_transport_risk_dashboard(all_data)
            ], md=6, className="mb-4"),
            dbc.Col([
                create_agriculture_risk_dashboard(all_data)
            ], md=6, className="mb-4")
        ])
    ])

def collect_all_risk_data(suppliers_data):
    """Collect risk data for all suppliers efficiently"""
    
    print("🔄 Collecting risk data for analytics...")
    
    all_data = {
        "suppliers": [],
        "climate_risks": [],
        "transport_risks": [],
        "agriculture_risks": [],
        "overall_stats": {}
    }
    
    # Process each supplier
    for supplier in suppliers_data:
        supplier_id = supplier.get("SupplierId")
        name = supplier.get("Name", f"Supplier {supplier_id}")
        
        # Get risk data (using cached functions)
        climate_data = get_climate_risk_for_supplier(supplier_id)
        transport_data = get_traffic_data_for_supplier(supplier_id)
        ndvi_value = get_mock_ndvi_for_supplier(supplier_id)
        
        # Categorize agriculture risk
        if ndvi_value > 0.7:
            agri_risk = "LOW"
        elif ndvi_value > 0.5:
            agri_risk = "MEDIUM"
        else:
            agri_risk = "HIGH"
        
        supplier_data = {
            "id": supplier_id,
            "name": name,
            "location": supplier.get("Location", ""),
            "climate_risk": climate_data["risk_level"],
            "climate_temp": climate_data["temp"],
            "climate_precip": climate_data["precip"],
            "transport_risk": transport_data["traffic_level"],
            "transport_delay": transport_data["delay_minutes"],
            "agriculture_risk": agri_risk,
            "agriculture_ndvi": ndvi_value
        }
        
        all_data["suppliers"].append(supplier_data)
        all_data["climate_risks"].append(climate_data["risk_level"])
        all_data["transport_risks"].append(transport_data["traffic_level"])
        all_data["agriculture_risks"].append(agri_risk)
    
    # Calculate overall statistics
    total_suppliers = len(suppliers_data)
    high_climate_risk = sum(1 for r in all_data["climate_risks"] if r == "HIGH")
    high_transport_risk = sum(1 for r in all_data["transport_risks"] if r == "HEAVY")
    high_agri_risk = sum(1 for r in all_data["agriculture_risks"] if r == "HIGH")
    
    all_data["overall_stats"] = {
        "total_suppliers": total_suppliers,
        "high_climate_risk_pct": (high_climate_risk / total_suppliers) * 100,
        "high_transport_risk_pct": (high_transport_risk / total_suppliers) * 100,
        "high_agri_risk_pct": (high_agri_risk / total_suppliers) * 100,
        "overall_risk_score": (high_climate_risk + high_transport_risk + high_agri_risk) / (total_suppliers * 3) * 100
    }
    
    return all_data

def create_overall_risk_dashboard(data):
    """Dashboard 1: Overall Risk Overview"""
    
    stats = data["overall_stats"]
    
    # Risk score gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=stats["overall_risk_score"],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Overall Risk Score"},
        delta={'reference': 20},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgreen"},
                {'range': [25, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 75
            }
        }
    ))
    fig_gauge.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    # Risk distribution pie chart
    risk_categories = ['Climate Risk', 'Transport Risk', 'Agriculture Risk']
    risk_values = [
        stats["high_climate_risk_pct"],
        stats["high_transport_risk_pct"], 
        stats["high_agri_risk_pct"]
    ]
    
    fig_pie = px.pie(
        values=risk_values,
        names=risk_categories,
        title="High Risk Distribution by Category",
        color_discrete_sequence=['#ef4444', '#f59e0b', '#22c55e']
    )
    fig_pie.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "Overall Risk Overview"
            ], className="text-white mb-0")
        ], style={"backgroundColor": "#1f2937"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_gauge, config={'displayModeBar': False})
                ], md=6),
                dbc.Col([
                    dcc.Graph(figure=fig_pie, config={'displayModeBar': False})
                ], md=6)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6(f"{stats['total_suppliers']}", className="text-primary mb-0"),
                        html.Small("Total Suppliers", className="text-muted")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H6(f"{stats['high_climate_risk_pct']:.1f}%", className="text-danger mb-0"),
                        html.Small("High Climate Risk", className="text-muted")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H6(f"{stats['high_transport_risk_pct']:.1f}%", className="text-warning mb-0"),
                        html.Small("High Transport Risk", className="text-muted")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H6(f"{stats['high_agri_risk_pct']:.1f}%", className="text-success mb-0"),
                        html.Small("High Agriculture Risk", className="text-muted")
                    ], className="text-center")
                ], md=3)
            ], className="mt-3")
        ], style={"backgroundColor": "#374151"})
    ], style={"backgroundColor": "#374151"})

def create_climate_risk_dashboard(data):
    """Dashboard 2: Climate Risk Analysis"""
    
    suppliers = data["suppliers"]
    df = pd.DataFrame(suppliers)
    
    # Temperature vs Precipitation scatter
    fig_scatter = px.scatter(
        df,
        x='climate_temp',
        y='climate_precip',
        color='climate_risk',
        size=[10]*len(df),
        hover_data=['name'],
        title="Climate Conditions by Supplier",
        color_discrete_map={'LOW': '#22c55e', 'MEDIUM': '#f59e0b', 'HIGH': '#ef4444'},
        labels={'climate_temp': 'Temperature (°C)', 'climate_precip': 'Precipitation (mm)'}
    )
    fig_scatter.update_layout(
        height=250,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    # Climate risk distribution
    climate_counts = df['climate_risk'].value_counts()
    fig_bar = px.bar(
        x=climate_counts.index,
        y=climate_counts.values,
        title="Climate Risk Distribution",
        color=climate_counts.index,
        color_discrete_map={'LOW': '#22c55e', 'MEDIUM': '#f59e0b', 'HIGH': '#ef4444'}
    )
    fig_bar.update_layout(
        height=250,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        showlegend=False
    )
    
    # High risk suppliers table
    high_risk_climate = df[df['climate_risk'] == 'HIGH'].head(5)
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-cloud-rain me-2"),
                "Climate Risk Analysis"
            ], className="text-white mb-0")
        ], style={"backgroundColor": "#1e40af"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_scatter, config={'displayModeBar': False})
                ], md=8),
                dbc.Col([
                    dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
                ], md=4)
            ]),
            html.Hr(style={"borderColor": "rgba(255,255,255,0.3)"}),
            html.H6("🚨 High Climate Risk Suppliers", className="text-white mb-2"),
            html.Div([
                html.Div([
                    html.Strong(row['name'][:20] + "..." if len(row['name']) > 20 else row['name']),
                    html.Br(),
                    html.Small(f"Temp: {row['climate_temp']}°C, Precip: {row['climate_precip']}mm", className="text-muted")
                ], className="mb-2") for _, row in high_risk_climate.iterrows()
            ] if not high_risk_climate.empty else [html.P("No high climate risk suppliers", className="text-success")])
        ], style={"backgroundColor": "#1e3a8a"})
    ], style={"backgroundColor": "#1e3a8a"})

def create_transport_risk_dashboard(data):
    """Dashboard 3: Transport Risk Analysis"""
    
    suppliers = data["suppliers"]
    df = pd.DataFrame(suppliers)
    
    # Transport delay analysis
    fig_delays = px.bar(
        df.sort_values('transport_delay', ascending=True),
        x='transport_delay',
        y='name',
        color='transport_risk',
        title="Transport Delays by Supplier",
        color_discrete_map={'LIGHT': '#22c55e', 'MODERATE': '#f59e0b', 'HEAVY': '#ef4444'},
        orientation='h',
        labels={'transport_delay': 'Delay (minutes)', 'name': 'Supplier'}
    )
    fig_delays.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        yaxis={'tickfont': {'size': 10}}
    )
    
    # Transport risk pie chart
    transport_counts = df['transport_risk'].value_counts()
    fig_transport_pie = px.pie(
        values=transport_counts.values,
        names=transport_counts.index,
        title="Transport Risk Levels",
        color=transport_counts.index,
        color_discrete_map={'LIGHT': '#22c55e', 'MODERATE': '#f59e0b', 'HEAVY': '#ef4444'}
    )
    fig_transport_pie.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-truck me-2"),
                "Transport Risk Analysis"
            ], className="text-white mb-0")
        ], style={"backgroundColor": "#dc2626"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_delays, config={'displayModeBar': False})
                ], md=8),
                dbc.Col([
                    dcc.Graph(figure=fig_transport_pie, config={'displayModeBar': False})
                ], md=4)
            ]),
            html.Hr(style={"borderColor": "rgba(255,255,255,0.3)"}),
            dbc.Row([
                dbc.Col([
                    html.H6("📊 Transport Statistics", className="text-white mb-2"),
                    html.P(f"Average Delay: {df['transport_delay'].mean():.1f} minutes", className="text-light mb-1"),
                    html.P(f"Max Delay: {df['transport_delay'].max():.1f} minutes", className="text-light mb-1"),
                    html.P(f"Heavy Traffic Routes: {len(df[df['transport_risk'] == 'HEAVY'])}", className="text-danger mb-1")
                ])
            ])
        ], style={"backgroundColor": "#b91c1c"})
    ], style={"backgroundColor": "#b91c1c"})

def create_agriculture_risk_dashboard(data):
    """Dashboard 4: Agriculture Risk Analysis"""
    
    suppliers = data["suppliers"]
    df = pd.DataFrame(suppliers)
    
    # NDVI distribution histogram
    fig_ndvi = px.histogram(
        df,
        x='agriculture_ndvi',
        color='agriculture_risk',
        title="NDVI Distribution (Crop Health)",
        color_discrete_map={'LOW': '#22c55e', 'MEDIUM': '#f59e0b', 'HIGH': '#ef4444'},
        nbins=15
    )
    fig_ndvi.update_layout(
        height=250,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        xaxis_title="NDVI Value",
        yaxis_title="Number of Suppliers"
    )
    
    # Agriculture risk by supplier
    fig_agri_bar = px.bar(
        df.sort_values('agriculture_ndvi', ascending=True),
        x='agriculture_ndvi',
        y='name',
        color='agriculture_risk',
        title="Crop Health by Supplier",
        color_discrete_map={'LOW': '#22c55e', 'MEDIUM': '#f59e0b', 'HIGH': '#ef4444'},
        orientation='h'
    )
    fig_agri_bar.update_layout(
        height=250,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        yaxis={'tickfont': {'size': 10}}
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-seedling me-2"),
                "Agriculture Risk Analysis"
            ], className="text-white mb-0")
        ], style={"backgroundColor": "#059669"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_ndvi, config={'displayModeBar': False})
                ], md=6),
                dbc.Col([
                    dcc.Graph(figure=fig_agri_bar, config={'displayModeBar': False})
                ], md=6)
            ]),
            html.Hr(style={"borderColor": "rgba(255,255,255,0.3)"}),
            dbc.Row([
                dbc.Col([
                    html.H6("🌱 Agriculture Health Metrics", className="text-white mb-2"),
                    html.P(f"Average NDVI: {df['agriculture_ndvi'].mean():.3f}", className="text-light mb-1"),
                    html.P(f"Healthy Suppliers (NDVI > 0.7): {len(df[df['agriculture_ndvi'] > 0.7])}", className="text-success mb-1"),
                    html.P(f"At-Risk Suppliers (NDVI < 0.5): {len(df[df['agriculture_ndvi'] < 0.5])}", className="text-warning mb-1"),
                    html.P(f"Critical Suppliers (NDVI < 0.3): {len(df[df['agriculture_ndvi'] < 0.3])}", className="text-danger mb-1")
                ])
            ])
        ], style={"backgroundColor": "#047857"})
    ], style={"backgroundColor": "#047857"})

# Close analytics callback
@app.callback(
    Output("analytics-toggle", "n_clicks"),
    Input("close-analytics", "n_clicks"),
    prevent_initial_call=True
)
def close_analytics_dashboard(n_clicks):
    """Close analytics dashboard by resetting the toggle"""
    if n_clicks:
        return 0
    return 0

# Map updates handled by server-side callback with heavy caching





if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=APP_PORT)