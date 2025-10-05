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

from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_leaflet as dl


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
    det = a.get("Details") or {}

    sev_key = (a.get("Severity") or "STABLE").upper()
    sev = SEVERITY_BADGE.get(sev_key, SEVERITY_BADGE["STABLE"])
    sup = suppliers_index.get(a.get("SupplierId")) or {"Name": f"Supplier {a.get('SupplierId')}"}

    # Why/Message handling
    raw_msg = det.get("why") or det.get("message") or a.get("Title") or ""
    recs = None
    why_node: Any = None

    if raw_msg is not None:
        try:
            msg_json = json.loads(raw_msg) if isinstance(raw_msg, str) else raw_msg
            if isinstance(msg_json, dict) and msg_json.get("recommendations"):
                recs = normalize_recs(msg_json)

            else:
                # Falls kein recs-Objekt drin → zeige Raw JSON formatiert
                why_node = html.Pre(json.dumps(msg_json, indent=2), className="small bg-light p-2 rounded")
        except Exception:
            why_node = html.Div(raw_msg, className="mt-3 text-body")

    body_children = [
        html.Div([
            dbc.Badge(sev["text"], color=sev["color"], className="me-2"),
            html.Span(a.get("Title", ""), className="fw-bold text-dark fs-5"),
        ], className="d-flex align-items-center mb-2"),

        html.Small(f"Supplier: {sup.get('Name','?').capitalize()}", className="text-muted d-block"),
        html.Small(f"Crop: {a.get('CropId','?').capitalize()}", className="text-muted d-block"),
    ]

    # show why/message if present
    if why_node:
        body_children.append(why_node)

    # pretty recommendations panel
    if recs:
        body_children.append(html.Hr())
        body_children.append(html.H6("Recommendations", className="mt-2"))
        body_children.append(recommendations_panel(recs, suppliers_index))

    return dbc.Card(
        dbc.CardBody(body_children),
        className="mb-3 shadow-sm rounded-3 border-0",
        style={"position": "relative", "zIndex": 10}
    )


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
                    # Alert/Notification icon with count
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle", style={
                            "color": "#ef4444", 
                            "fontSize": "20px",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "filter": "drop-shadow(0 2px 4px rgba(0,0,0,0.3))"
                        }),
                        dbc.Badge("7", color="danger", className="position-absolute", style={
                            "fontSize": "0.6em",
                            "top": "-8px",
                            "right": "-8px",
                            "minWidth": "18px",
                            "height": "18px",
                            "borderRadius": "50%",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center"
                        })
                    ], id="alerts-toggle", className="me-4 position-relative d-flex align-items-center justify-content-center", style={
                        "width": "40px", 
                        "height": "40px",
                        "cursor": "pointer"
                    }),
                    
                    # Chat/Message icon
                    html.Div([
                        html.I(className="fas fa-comment-dots", style={
                            "color": "#10b981", 
                            "fontSize": "20px",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "filter": "drop-shadow(0 2px 6px rgba(16, 185, 129, 0.3))"
                        })
                    ], id="chat-toggle", className="me-4 d-flex align-items-center justify-content-center", style={
                        "width": "40px", 
                        "height": "40px",
                        "cursor": "pointer"
                    }),
                    
                    # Dropdown/Menu icon for indicators
                    html.Div([
                        html.I(className="fas fa-bars", style={
                            "color": "#f59e0b", 
                            "fontSize": "20px",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "filter": "drop-shadow(0 2px 6px rgba(245, 158, 11, 0.3))"
                        })
                    ], id="indicators-toggle", className="me-4 d-flex align-items-center justify-content-center", style={
                        "width": "40px", 
                        "height": "40px",
                        "cursor": "pointer"
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
        
        # Collapsible alerts panel
        dbc.Collapse([
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "Supply Chain Alerts"
                    ], className="mb-0 text-white")
                ], className="bg-primary"),
                dbc.CardBody([
                    html.Div(id="alerts-list", style={"maxHeight": "400px", "overflowY": "auto"})
                ], className="p-3")
            ], className="glass-card mt-3", style={"position": "relative", "zIndex": "9999"})
        ], id="alerts-collapse", is_open=False, style={"position": "relative", "zIndex": "9999"}),
        
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
    if n_clicks is None:
        return False
    return not is_open


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