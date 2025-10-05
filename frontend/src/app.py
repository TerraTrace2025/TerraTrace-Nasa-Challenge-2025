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
    {"id": 1, "name": "Fenaco Genossenschaft", "latitude": 46.9481, "longitude": 7.4474, "city": "Bern", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 2, "name": "Alpine Farms AG", "latitude": 47.6062, "longitude": 8.1090, "city": "Thurgau", "country": "Switzerland", "tier": "RISK", "transport_modes": "Truck"},
    {"id": 3, "name": "Swiss Valley Produce", "latitude": 47.2692, "longitude": 11.4041, "city": "Innsbruck", "country": "Austria", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 4, "name": "Organic Harvest Co", "latitude": 47.0502, "longitude": 8.3093, "city": "Lucerne", "country": "Switzerland", "tier": "HIGHRISK", "transport_modes": "Truck"},
    {"id": 5, "name": "Bavarian Grain Collective", "latitude": 48.1351, "longitude": 11.5820, "city": "Munich", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck,Train"},
    {"id": 6, "name": "Rhône Valley Vineyards", "latitude": 46.2044, "longitude": 6.1432, "city": "Geneva", "country": "Switzerland", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 7, "name": "Lombardy Agricultural Union", "latitude": 45.4642, "longitude": 9.1900, "city": "Milan", "country": "Italy", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 8, "name": "Black Forest Organics", "latitude": 48.0196, "longitude": 7.8421, "city": "Freiburg", "country": "Germany", "tier": "SURPLUS", "transport_modes": "Truck"},
    {"id": 9, "name": "Alsace Premium Produce", "latitude": 48.5734, "longitude": 7.7521, "city": "Strasbourg", "country": "France", "tier": "RISK", "transport_modes": "Truck,Train"},
    {"id": 10, "name": "Tyrolean Mountain Farms", "latitude": 47.0707, "longitude": 15.4395, "city": "Graz", "country": "Austria", "tier": "HIGHRISK", "transport_modes": "Truck"}
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

def marker_for_supplier(s, selected_supplier_id=None):
    is_selected = s.get("SupplierId") == selected_supplier_id
    color = "#2563eb" if is_selected else TIER_COLOR.get((s.get("CurrentTier") or "").upper(), "#3b82f6")
    radius = 14 if is_selected else 10
    weight = 3 if is_selected else 1

    return dl.CircleMarker(
        center=(s.get("Lat") or 0, s.get("Lon") or 0),
        radius=radius,
        color=color,
        weight=weight,
        fill=True,
        fillOpacity=0.7 if is_selected else 0.5,
        children=[
            dl.Tooltip(f"{s.get('Name') or 'Supplier'} - {s.get('_raw').get('city','')}"),
            dl.Popup([
                html.B(s.get("Name") or "Supplier"), html.Br(),
                html.Div(s.get("Location","")),
                html.Div(f"Tier: {s.get('CurrentTier','?')}")
            ])
        ]
    )

def marker_for_company(c):
    if not c or not c.get("Lat") or not c.get("Lon"):
        return None
    # Use a simple default marker (no external icon dependency)
    return dl.Marker(
        position=(c["Lat"], c["Lon"]),
        children=[
            dl.Tooltip(f"{c.get('Name','Company')} (HQ)"),
            dl.Popup([
                html.B(c.get("Name","Company")), html.Br(),
                html.Div(f"{c.get('City','')}, {c.get('Country','')}")
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

def build_supplier_routes(company: Dict[str, Any], suppliers: List[Dict[str, Any]]) -> List[Any]:
    """Build polyline routes from each supplier to company location using OSRM routing."""
    if not company or not company.get("Lat") or not company.get("Lon"):
        return []

    target = (company["Lat"], company["Lon"])
    polylines = []
    for s in suppliers:
        if not s.get("Lat") or not s.get("Lon"):
            continue
        src = (s["Lat"], s["Lon"])
        routed = osrm_route(src, target)
        if routed and routed.get("coords"):
            # Use actual routed path
            line = dl.Polyline(positions=routed["coords"], color="#2563eb", weight=3, opacity=0.8)
        else:
            # Fallback to straight line if routing fails
            line = dl.Polyline(positions=[src, target], color="#2563eb", weight=3, dashArray="5,5")
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


def build_map(company: Dict[str, Any], suppliers: List[Dict[str, Any]], alerts: List[Dict[str, Any]], selected_supplier_id=None):
    # Base markers
    marker_children = []
    comp_marker = marker_for_company(company)
    if comp_marker:
        marker_children.append(comp_marker)
    marker_children.extend([marker_for_supplier(s, selected_supplier_id) for s in suppliers if s.get("Lat") and s.get("Lon")])

    # Routes with proper OSRM routing
    route_layers = build_supplier_routes(company, suppliers)

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

    children = [
        dl.TileLayer(
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        ),
        dl.LayerGroup(alert_overlays, id="alert-overlays"),
        dl.LayerGroup(marker_children, id="entity-markers"),
        dl.LayerGroup(route_layers, id="route-layers"),
    ]
    # Center on Zurich with appropriate zoom level
    return dl.Map(center=(47.3769, 8.5417), zoom=8, children=children, style={"height": "calc(100vh - 80px)", "width": "100%"})

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
                    
                    # Analytics/Dashboard icon
                    html.Div([
                        html.I(className="fas fa-chart-bar", style={
                            "color": "#e5e7eb", 
                            "fontSize": "20px",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "filter": "drop-shadow(0 2px 6px rgba(229, 231, 235, 0.4))"
                        })
                    ], id="analytics-toggle", className="me-2 d-flex align-items-center justify-content-center", style={
                        "width": "40px", 
                        "height": "40px",
                        "cursor": "pointer"
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
                        html.Div(id="map-container", style={"minHeight": "calc(100vh - 80px)"})
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
                
                # Climate & Weather
                html.Div([
                    dbc.Switch(
                        id="climate-toggle", 
                        value=False,
                        label="Climate & Weather",
                        style={"color": "white"}
                    )
                ], className="mb-2"),
                
                # Agricultural Monitoring  
                html.Div([
                    dbc.Switch(
                        id="agriculture-toggle", 
                        value=False,
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
                            html.Span("Hello! I'm your Swiss Corp supply chain assistant. How can I help you today?", 
                                     className="text-white", style={"fontSize": "0.9em"})
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
                            placeholder="Ask about your supply chain...",
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
@app.callback(
    Output("climate-toggle", "label"),
    Input("climate-toggle", "value")
)
def update_climate_label(value):
    return "Climate & Weather: ON" if value else "Climate & Weather: OFF"

@app.callback(
    Output("agriculture-toggle", "label"), 
    Input("agriculture-toggle", "value")
)
def update_agriculture_label(value):
    return "Agricultural Monitoring: ON" if value else "Agricultural Monitoring: OFF"

@app.callback(
    Output("transport-toggle", "label"),
    Input("transport-toggle", "value") 
)
def update_transport_label(value):
    return "Transportation & Logistics: ON" if value else "Transportation & Logistics: OFF"


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
    """Generate AI response using OpenAI GPT."""
    if not openai_client:
        # Provide helpful setup instructions
        if not OPENAI_AVAILABLE:
            return "🔧 **Setup Required**: OpenAI package not installed. Run: `pip install openai` in your terminal, then restart the app."
        elif not OPENAI_API_KEY:
            return "🔑 **API Key Missing**: Set your OpenAI API key with: `export OPENAI_API_KEY='your-key-here'` then restart the app. Get your key from: https://platform.openai.com/api-keys"
        else:
            return "⚠️ AI assistant is not available. Please check OpenAI configuration."
    
    # Swiss Corp supply chain context
    system_context = """You are an AI assistant for Swiss Corp, a supply chain management company. 

CURRENT SUPPLY CHAIN STATUS:
- Company: Swiss Corp (HQ in Zurich, Switzerland)
- Active Suppliers: 10 suppliers across Central Europe
- High-risk suppliers: Organic Harvest Co (Lucerne), Tyrolean Mountain Farms (Graz)
- Current alerts: 7 total (2 high-risk, 3 medium-risk, 2 surplus opportunities)
- Crops: soybeans, potatoes, rice, dairy, grapes, wine grapes, corn
- Transport: Truck and train routes, 2-3 day average delivery
- Climate issues: Drought in Lucerne affecting soybeans, heavy rainfall in Lombardy affecting rice

SUPPLIERS:
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

Provide helpful, specific advice about supply chain management, risk mitigation, and operational optimization. Keep responses concise and actionable."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using the more cost-effective model
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback to local responses if OpenAI fails
        return get_fallback_response(user_message)

def get_fallback_response(user_message: str) -> str:
    """Provide intelligent fallback responses when OpenAI is not available."""
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ["supplier", "suppliers"]):
        return "📊 **Supplier Overview**: You have 10 active suppliers across Central Europe. **High-risk suppliers**: Organic Harvest Co (Lucerne) and Tyrolean Mountain Farms (Graz) due to drought and alpine weather. **Surplus suppliers**: Fenaco (Bern), Swiss Valley (Innsbruck), Bavarian Grain (Munich). Would you like details on any specific supplier?"
    
    elif any(word in message_lower for word in ["alert", "alerts", "risk"]):
        return "🚨 **Active Alerts (7 total)**: **HIGH RISK**: Drought affecting soybeans (40% yield loss), Alpine dairy disruption. **MEDIUM RISK**: Storage issues (potatoes), Lombardy flooding (rice), Alsace transport delays. **SURPLUS**: Exceptional grape harvest (+25%), Corn surplus (500t available). Priority: Address drought and dairy issues first."
    
    elif any(word in message_lower for word in ["weather", "climate"]):
        return "🌦️ **Climate Impact**: **Drought** in Lucerne affecting soybean harvest (40% reduction). **Heavy rainfall** in Lombardy impacting rice production. **Recommendation**: Activate alternative suppliers - Bavarian Grain (Munich) for soybeans, Swiss Valley (Innsbruck) for rice alternatives. Monitor weather forecasts for next 2 weeks."
    
    elif any(word in message_lower for word in ["transport", "logistics", "delivery"]):
        return "🚛 **Logistics Status**: Average delivery time: 2-3 days. **Routes**: Munich-Zurich (truck/train), Milan-Zurich (minor weather delays), Geneva-Zurich (optimal). **Recommendation**: Use train routes during weather disruptions. Bavarian Grain and Black Forest Organics have best transport reliability."
    
    elif any(word in message_lower for word in ["crop", "crops", "harvest"]):
        return "🌾 **Crop Portfolio**: **At Risk**: Soybeans (drought), Rice (flooding), Dairy (alpine weather). **Surplus**: Grapes (+25% harvest), Wine grapes (premium available), Corn (+500t capacity). **Stable**: Potatoes (storage issues resolved). Focus on securing alternative soybean sources immediately."
    
    elif any(word in message_lower for word in ["recommendation", "advice", "help"]):
        return "💡 **Priority Actions**: 1) **Immediate**: Source soybeans from Bavarian Grain to offset Lucerne drought. 2) **This week**: Secure dairy alternatives for Tyrolean disruption. 3) **Opportunity**: Lock in surplus grape pricing from Rhône Valley. 4) **Monitor**: Lombardy flooding impact on rice supply. Need specific help with any of these?"
    
    else:
        return f"🤖 **Swiss Corp Assistant**: I understand you're asking about '{user_message}'. I can help with: **Suppliers** (risk analysis, alternatives), **Alerts** (prioritization, actions), **Weather** (impact assessment), **Logistics** (route optimization), **Crops** (harvest status, alternatives). What would you like to explore? *(Note: For enhanced AI responses, set up OpenAI integration)*"


# ----------------------------------
# Live refresh: map + alerts
# ----------------------------------
@app.callback(
    Output("map-container", "children"),
    Output("alerts-list", "children"),
    Input("token-store", "data"),
    Input("selected-supplier-id", "data")
)
def refresh_dashboard(token, selected_supplier_id):
    """Refresh dashboard with elegant full-screen map and alerts."""
    
    # Use mock data for Swiss Corp - no login required
    company = MOCK_COMPANY
    suppliers = MOCK_SUPPLIERS
    alerts = MOCK_ALERTS

    # Normalize data for consistency
    normalized_suppliers = []
    for s in suppliers:
        normalized_suppliers.append({
            "SupplierId": s["id"],
            "Name": s["name"],
            "Lat": s["latitude"],
            "Lon": s["longitude"],
            "CurrentTier": s["tier"],
            "Location": f"{s['city']}, {s['country']}",
            "_raw": s
        })

    normalized_company = {
        "CompanyId": company["id"],
        "Name": company["name"],
        "Lat": company["latitude"],
        "Lon": company["longitude"],
        "City": company["city"],
        "Country": company["country"]
    }

    # Build elegant full-screen map with proper routing
    map_component = build_map(normalized_company, normalized_suppliers, alerts, selected_supplier_id)
    
    # Build alerts list
    normalized_alerts = []
    for a in alerts:
        normalized_alerts.append({
            "AlertId": a["id"],
            "CompanyId": a["company_id"],
            "SupplierId": a["supplier_id"],
            "CropId": a["crop_type"],
            "CreatedAt": a["created_at"],
            "Severity": a["severity"].upper(),
            "Title": a["title"],
            "Details": {"message": a["message"]},
        })

    # Create suppliers index for alert cards
    suppliers_index = {s["SupplierId"]: s for s in normalized_suppliers}
    
    # Sort alerts by severity
    sorted_alerts = sorted(normalized_alerts, key=lambda x: SEVERITY_ORDER.get(x.get("Severity", "STABLE"), 0), reverse=True)
    
    alert_cards = [alert_card(a, suppliers_index) for a in sorted_alerts]
    
    return map_component, alert_cards


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=APP_PORT)