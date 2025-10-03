"""
CropPulse Frontend (Option A) — Dash/Plotly + Leaflet MVP

How to run:
1) pip install -r requirements (see list below)
2) export API_BASE=http://localhost:8000  # your FastAPI base (optional)
3) export USE_MOCK=true                    # für Demo/Offline
4) python app.py

Requirements (pip):
 dash==2.17.1
 dash-bootstrap-components==1.6.0
 dash-leaflet==0.1.28
 plotly==5.23.0
 requests==2.32.3

Notes:
- If API is unavailable, set USE_MOCK=true to use local dummy data.
- USE_OSRM=true (default) tries real road routes from OSRM; otherwise straight lines.
"""
import os
import json
import math
import datetime as dt
from typing import Any, Dict, List, Optional
from math import radians, sin, cos, asin, sqrt

import requests
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# ----------------------------
# Config
# ----------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
USE_OSRM = os.getenv("USE_OSRM", "true").lower() == "true"   # use OSRM routing if available
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"  # use local mock data
REFRESH_MS = int(os.getenv("REFRESH_MS", "30000"))           # 30s for demo
DEFAULT_COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))

# ----------------------------
# Helpers (API)
# ----------------------------
def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    if USE_MOCK:
        return mock_get(path, params)
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "_fallback": mock_get(path, params)}

def api_post(path: str, payload: Dict[str, Any]) -> Any:
    if USE_MOCK:
        return {"status": "ok", "_mock": True}
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ----------------------------
# Mock data (for offline demo)
# ----------------------------
# Retailer (fixed demo location: Zürich)
RETAILER_LOCATION = (47.3769, 8.5417)

# Demo farms per crop (mirror of the idea `locations_dict`)
MOCK_FARM_LOCATIONS = {
    "Wheat": [
        {"name": "Farm A (BE)", "lat": 46.98, "lon": 7.45},
        {"name": "Farm B (SO)", "lat": 47.21, "lon": 7.52}
    ],
    "Potatoes": [
        {"name": "Farm C (TG)", "lat": 47.60, "lon": 9.05},
        {"name": "Farm D (AG)", "lat": 47.42, "lon": 8.24}
    ],
    "Rice": [
        {"name": "Farm E (IT)", "lat": 45.36, "lon": 8.62}
    ]
}

# Demo warehouses
MOCK_WAREHOUSES = [
    {"id": 201, "name": "Warehouse Zürich", "lat": 47.39, "lon": 8.51},
    {"id": 202, "name": "Warehouse Bern", "lat": 46.95, "lon": 7.43}
]

MOCK_SUPPLIERS = [
    {"SupplierId": 10, "Name": "fenaco", "Location": "Bern, CH", "Lat": 46.948, "Lon": 7.447,
     "TransportModes": "Truck,Train", "CurrentTier": "MED"},
    {"SupplierId": 11, "Name": "Supplier Y", "Location": "Thurgau, CH", "Lat": 47.6, "Lon": 9.1,
     "TransportModes": "Truck", "CurrentTier": "LOW"},
    {"SupplierId": 12, "Name": "Supplier Z", "Location": "Tyrol, AT", "Lat": 47.2, "Lon": 11.3,
     "TransportModes": "Truck,Train", "CurrentTier": "HIGH"},
]

MOCK_ALERTS = [
    {"AlertId": 1, "CompanyId": 1, "SupplierId": 12, "CropId": 2, "CreatedAt": "2025-09-29T09:00:00",
     "Severity": "CRIT", "Title": "Potatoes @ Supplier Z high risk",
     "Details": json.dumps({"risk_index": 78, "why": "Heatwave + soil moisture deficit"}), "IsActive": 1},
    {"AlertId": 2, "CompanyId": 1, "SupplierId": 10, "CropId": 2, "CreatedAt": "2025-09-28T08:30:00",
     "Severity": "WARN", "Title": "Potatoes @ fenaco medium risk",
     "Details": json.dumps({"risk_index": 58, "why": "NDVI trend negative"}), "IsActive": 1},
]

MOCK_RECS = {
    "alternatives": [
        {"supplierId": 11, "coverage": 0.8, "cost_delta_pct": -3.5, "co2_tonne_km": 0.12,
         "risk_index": 24, "reasoning": "Low risk; ample potatoes; near expiry in 9d"},
        {"supplierId": 10, "coverage": 0.4, "cost_delta_pct": +0.5, "co2_tonne_km": 0.08,
         "risk_index": 55, "reasoning": "Medium risk; close distance"}
    ]
}

def mock_get(path: str, params: Optional[Dict[str, Any]] = None):
    if path.startswith("/suppliers"):
        return MOCK_SUPPLIERS
    if path.startswith(f"/company/{DEFAULT_COMPANY_ID}/alerts"):
        return MOCK_ALERTS
    if path.startswith(f"/company/{DEFAULT_COMPANY_ID}/recommendations"):
        return MOCK_RECS
    return {}

# ----------------------------
# UI Components
# ----------------------------
TIER_COLOR = {"LOW": "#22c55e", "MED": "#f59e0b", "HIGH": "#ef4444", None: "#93c5fd"}
SEVERITY_BADGE = {
    "INFO": {"color": "secondary", "text": "INFO"},
    "WARN": {"color": "warning", "text": "WARN"},
    "CRIT": {"color": "danger", "text": "CRIT"},
}

def marker_for_supplier(s):
    color = TIER_COLOR.get((s.get("CurrentTier") or "").upper(), "#3b82f6")
    return dl.CircleMarker(
        center=(s.get("Lat", 0), s.get("Lon", 0)),
        radius=10,
        color=color,
        children=[
            dl.Tooltip(f"{s['Name']} — {s.get('CurrentTier','?')}"),
            dl.Popup([
                html.B(s["Name"]), html.Br(),
                html.Div(s.get("Location","")),
                html.Div(f"Tier: {s.get('CurrentTier','?')}")
            ])
        ]
    )

def build_map(suppliers: List[Dict[str, Any]], extra_layers: Optional[List[Any]] = None):
    markers = [marker_for_supplier(s) for s in suppliers if s.get("Lat") and s.get("Lon")]
    children = [dl.TileLayer(), dl.LayerGroup(markers, id="supplier-markers")]
    if extra_layers:
        children.extend(extra_layers)
    return dl.Map(center=(47.0, 8.0), zoom=6, children=children, style={"height": "65vh", "width": "100%"})

def alert_card(a: Dict[str, Any], suppliers_index: Dict[int, Dict[str, Any]]):
    sev = SEVERITY_BADGE.get(a.get("Severity","WARN"), SEVERITY_BADGE["WARN"])
    sup = suppliers_index.get(a.get("SupplierId"), {"Name": f"Supplier {a.get('SupplierId')}"})
    details = a.get("Details")
    try:
        det = json.loads(details) if isinstance(details, str) else details
    except Exception:
        det = {"risk_index": "?", "why": details}
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                dbc.Badge(sev["text"], color=sev["color"], className="me-2"),
                html.Span(a.get("Title",""), className="fw-bold")
            ]),
            html.Small(f"Supplier: {sup.get('Name')} • CropId: {a.get('CropId')} • {a.get('CreatedAt')}",
                       className="text-muted d-block mt-1"),
            html.Div(det.get("why",""), className="mt-2"),
            html.Div(f"Risk Index: {det.get('risk_index','?')}", className="mt-1")
        ])
    ], className="mb-2")

def recommendations_panel(recs: Dict[str, Any], suppliers_index: Dict[int, Dict[str, Any]]):
    items = []
    for r in recs.get("alternatives", []):
        sup = suppliers_index.get(r.get("supplierId"), {"Name": f"Supplier {r.get('supplierId')}"})
        items.append(dbc.ListGroupItem([
            html.Div([html.B(sup.get("Name")), html.Span(f" — coverage {int(100*r.get('coverage',0))}%")]),
            html.Div(f"Risk {r.get('risk_index','?')} | ΔCost {r.get('cost_delta_pct',0)}% | CO₂ {r.get('co2_tonne_km',0)} t·km"),
            html.Div(r.get("reasoning",""), className="text-muted")
        ]))
    if not items:
        items = [dbc.ListGroupItem("No recommendations yet.")]
    return dbc.ListGroup(items)

def risk_timeline_placeholder():
    fig = go.Figure()
    x = [dt.date.today() + dt.timedelta(days=i) for i in range(14)]
    y = [min(100, max(0, 40 + 20*math.sin(i/3))) for i in range(14)]
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name="Risk Index"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=220, yaxis_title="Risk (0-100)")
    return dcc.Graph(figure=fig, config={"displayModeBar": False})

# ----------------------------
# App & Layout
# ----------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "CropPulse"

sidebar = dbc.Card([
    dbc.CardBody([
        html.H5("Filters"),
        dbc.Label("Company"),
        dcc.Dropdown(id="company-dd",
                     options=[{"label": "LANDI", "value": 1}],
                     value=DEFAULT_COMPANY_ID,
                     clearable=False),
        dbc.Label("Overlay"),
        dcc.Checklist(id="overlay-checks",
                      options=[
                          {"label": "Temperature", "value": "TEMP"},
                          {"label": "Precipitation", "value": "PRECIP"},
                          {"label": "Soil Moisture", "value": "SOIL"},
                          {"label": "NDVI", "value": "NDVI"},
                      ],
                      value=["TEMP"],
                      inputStyle={"marginRight": "6px"}),
        html.Hr(),
        html.H6("Route Planner"),
        dbc.Label("Crop"),
        dcc.Dropdown(id="route-crop-dd",
                     options=[{"label": c, "value": c} for c in sorted(MOCK_FARM_LOCATIONS.keys())],
                     placeholder="Select crop…"),
        dbc.Label("Farm"),
        dcc.Dropdown(id="route-farm-dd", placeholder="Select farm…"),
        dbc.Label("Warehouse"),
        dcc.Dropdown(id="route-warehouse-dd",
                     options=[{"label": w["name"], "value": w["id"]} for w in MOCK_WAREHOUSES],
                     placeholder="Select warehouse…"),
        dbc.Label("Volume (kg)"),
        dbc.Input(id="route-volume", type="number", value=1000, min=1),
        dbc.Label("Mode"),
        dcc.Dropdown(id="route-mode",
                     options=[{"label":"Truck","value":"Truck"}, {"label":"Train","value":"Train"}],
                     value="Truck", clearable=False),
        html.Small(f"Retailer fixed: Zürich {RETAILER_LOCATION}", className="text-muted d-block mb-2"),
        html.Div(id="route-msg", className="mt-1 text-info"),
        html.Hr(),
        html.H6("Add Supply Chain"),
        dbc.Input(id="inp-product", placeholder="Crop (e.g., Potatoes)", type="text"),
        dbc.Input(id="inp-region", placeholder="Region (e.g., Thurgau, CH)", type="text", className="mt-1"),
        dbc.Input(id="inp-volume", placeholder="Planned Volume (kg)", type="number", className="mt-1"),
        dbc.Button("Add", id="btn-add", color="primary", className="mt-2", n_clicks=0),
        html.Div(id="add-msg", className="mt-1 text-success")
    ])
], className="h-100")

content = html.Div([
    dbc.Row([
        dbc.Col(html.Div(id="map-container"), md=8),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Alerts"),
            dbc.CardBody(html.Div(id="alerts-list"))
        ]), md=4)
    ], className="mt-2"),
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Recommendations"),
            dbc.CardBody(html.Div(id="recs-panel"))
        ]), md=6),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Route KPIs"),
            dbc.CardBody(html.Div(id="kpi-panel"))
        ]), md=6)
    ], className="mt-2"),
    dcc.Interval(id="tick", interval=REFRESH_MS, n_intervals=0)
])

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col(html.H3("CropPulse — Climate-Smart Supply Chains"), md=8),
        dbc.Col(html.Div([html.Small(f"API: {API_BASE}")], className="text-end"), md=4)
    ], className="mt-2"),
    dbc.Row([
        dbc.Col(sidebar, md=3),
        dbc.Col(content, md=9)
    ], className="mt-2")
])

# ----------------------------
# Transport cost/CO₂ parameters (simple demo values)
# ----------------------------
COST_PER_KM_BY_MODE = {"Truck": 1.2, "Train": 0.6}
CO2_PER_TKM_BY_MODE = {"Truck": 0.12, "Train": 0.04}  # t CO2 per tonne-km
SPEED_KMPH_BY_MODE = {"Truck": 60.0, "Train": 80.0}

# ----------------------------
# Routing helpers (Haversine + optional OSRM)
# ----------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

def build_route_layers(
    farm: Optional[Dict[str, Any]],
    warehouse: Optional[Dict[str, Any]],
    route_polylines: Optional[List[List[tuple]]] = None
):
    layers = []
    markers = []
    if farm:
        markers.append(dl.Marker(position=(farm["lat"], farm["lon"]),
                                 children=[dl.Tooltip(f"Farm: {farm['name']}")]))
    if warehouse:
        markers.append(dl.Marker(position=(warehouse["lat"], warehouse["lon"]),
                                 children=[dl.Tooltip(f"Warehouse: {warehouse['name']}")]))
    # retailer fixed
    markers.append(dl.Marker(position=RETAILER_LOCATION, children=[dl.Tooltip("Retailer (Zürich)")]))
    # Fallback: straight legs if no polylines provided
    legs = []
    if farm and warehouse:
        legs.append([(farm["lat"], farm["lon"]), (warehouse["lat"], warehouse["lon"])])
    if warehouse:
        legs.append([(warehouse["lat"], warehouse["lon"]), RETAILER_LOCATION])
    elif farm:
        legs.append([(farm["lat"], farm["lon"]), RETAILER_LOCATION])
    poly_src = route_polylines if route_polylines else legs
    polylines = [dl.Polyline(positions=leg, weight=4, opacity=0.8) for leg in poly_src]
    layers.append(dl.LayerGroup(markers + polylines, id="route-layer"))
    return layers

# ---- OSRM helpers ----
def _decode_polyline5(polyline: str) -> List[tuple]:
    coords = []
    index = 0
    lat = 0
    lon = 0
    length = len(polyline)
    while index < length:
        shift = 0; result = 0
        while True:
            b = ord(polyline[index]) - 63; index += 1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        shift = 0; result = 0
        while True:
            b = ord(polyline[index]) - 63; index += 1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        dlon = ~(result >> 1) if (result & 1) else (result >> 1)
        lon += dlon
        coords.append((lat / 1e5, lon / 1e5))
    return coords

def osrm_route(a: tuple, b: tuple, mode: str = "Truck") -> Optional[Dict[str, Any]]:
    if not USE_OSRM:
        return None
    profile = "driving"  # for Truck/Train we still use 'driving'
    url = f"https://router.project-osrm.org/route/v1/{profile}/{a[1]},{a[0]};{b[1]},{b[0]}"
    params = {"overview": "full", "geometries": "polyline", "alternatives": "false"}
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        route = routes[0]
        coords = _decode_polyline5(route.get("geometry", ""))
        distance_km = (route.get("distance", 0.0) or 0.0) / 1000.0
        duration_h = (route.get("duration", 0.0) or 0.0) / 3600.0
        return {"coords": coords, "distance_km": distance_km, "duration_h": duration_h}
    except Exception:
        return None

def compute_kpis(farm: Optional[Dict[str, Any]], warehouse: Optional[Dict[str, Any]],
                 mode: str = "Truck", volume_kg: float = 1000.0):
    legs = []
    labels = []
    if farm and warehouse:
        legs.append(((farm["lat"], farm["lon"]), (warehouse["lat"], warehouse["lon"])))
        labels.append("Farm → Warehouse")
    if warehouse:
        legs.append(((warehouse["lat"], warehouse["lon"]), RETAILER_LOCATION))
        labels.append("Warehouse → Retailer")
    elif farm:
        legs.append(((farm["lat"], farm["lon"]), RETAILER_LOCATION))
        labels.append("Farm → Retailer")

    if not legs:
        return {"total": {"distance_km": 0.0, "time_h": 0.0, "budget_chf": 0.0, "co2_t": 0.0}, "legs": []}

    cost_per_km = COST_PER_KM_BY_MODE.get(mode, 1.2)
    co2_per_tkm = CO2_PER_TKM_BY_MODE.get(mode, 0.12)
    speed = SPEED_KMPH_BY_MODE.get(mode, 60.0)

    legs_out = []
    total_dist = 0.0
    total_time = 0.0
    for idx, (a, b) in enumerate(legs):
        routed = osrm_route(a, b, mode)
        if routed:
            dist_km = routed["distance_km"]; dur_h = routed["duration_h"]
        else:
            dist_km = haversine_km(a[0], a[1], b[0], b[1]); dur_h = dist_km / speed if speed > 0 else 0.0
        total_dist += dist_km; total_time += dur_h
        legs_out.append({"label": labels[idx], "distance_km": dist_km, "time_h": dur_h})

    budget = total_dist * cost_per_km
    co2 = (volume_kg / 1000.0) * total_dist * co2_per_tkm
    return {"total": {"distance_km": total_dist, "time_h": total_time, "budget_chf": budget, "co2_t": co2}, "legs": legs_out}

# ----------------------------
# Callbacks
# ----------------------------
@app.callback(
    Output("map-container", "children"),
    Output("alerts-list", "children"),
    Output("recs-panel", "children"),
    Output("route-farm-dd", "options"),
    Output("route-msg", "children"),
    Output("kpi-panel", "children"),
    Input("tick", "n_intervals"),
    Input("company-dd", "value"),
    Input("route-crop-dd", "value"),
    Input("route-farm-dd", "value"),
    Input("route-warehouse-dd", "value"),
    Input("route-volume", "value"),
    Input("route-mode", "value"),
)
def refresh(n, company_id, crop_value, farm_value, warehouse_value, route_volume, route_mode):
    suppliers = api_get("/suppliers")
    if isinstance(suppliers, dict) and "_fallback" in suppliers:
        suppliers = suppliers["_fallback"]

    # Farm/Warehouse Auswahl
    farm = None
    farm_options = []
    if crop_value:
        farms = MOCK_FARM_LOCATIONS.get(crop_value, [])
        farm_options = [{"label": f["name"], "value": f["name"]} for f in farms]
        if farm_value:
            for f in farms:
                if f["name"] == farm_value:
                    farm = f
                    break
    warehouse = None
    if warehouse_value:
        for w in MOCK_WAREHOUSES:
            if w["id"] == warehouse_value:
                warehouse = w
                break

    # Route-Polylines per Leg (OSRM → Fallback straight)
    poly_routes: List[List[tuple]] = []
    if farm or warehouse:
        legs2 = []
        if farm and warehouse:
            legs2.append(((farm["lat"], farm["lon"]), (warehouse["lat"], warehouse["lon"])))
        if warehouse:
            legs2.append(((warehouse["lat"], warehouse["lon"]), RETAILER_LOCATION))
        elif farm:
            legs2.append(((farm["lat"], farm["lon"]), RETAILER_LOCATION))
        for (a, b) in legs2:
            routed = osrm_route(a, b, route_mode or "Truck")
            if routed and routed.get("coords"):
                poly_routes.append(routed["coords"])
            else:
                poly_routes.append([a, b])

    route_layers = build_route_layers(farm, warehouse, route_polylines=poly_routes if poly_routes else None)
    map_el = build_map(suppliers, extra_layers=route_layers)

    # Alerts & Recs
    alerts = api_get(f"/company/{company_id}/alerts")
    if isinstance(alerts, dict) and "_fallback" in alerts:
        alerts = alerts["_fallback"]
    sup_index = {s["SupplierId"]: s for s in suppliers}
    alerts_cards = [alert_card(a, sup_index) for a in alerts] or [html.Div("No active alerts.")]

    recs = api_get(f"/company/{company_id}/recommendations/latest")
    if isinstance(recs, dict) and "_fallback" in recs:
        recs = recs["_fallback"]
    recs_el = recommendations_panel(recs, sup_index)

    # Route-Validation + KPI-Panel
    if crop_value and not farm:
        route_msg = "Bitte wähle eine Farm aus."
    else:
        route_msg = ""

    kpi_children = []
    if farm or warehouse:
        k = compute_kpis(farm, warehouse, mode=(route_mode or "Truck"), volume_kg=(route_volume or 1000))
        total = k["total"]
        rows = [
            html.Tr([
                html.Th("Total"),
                html.Td(f"{total['distance_km']:.1f} km"),
                html.Td(f"{total['time_h']:.1f} h"),
                html.Td(f"CHF {total['budget_chf']:.0f}"),
                html.Td(f"{total['co2_t']:.2f} t"),
            ])
        ]
        for leg in k["legs"]:
            rows.append(html.Tr([
                html.Td(leg["label"]),
                html.Td(f"{leg['distance_km']:.1f} km"),
                html.Td(f"{leg['time_h']:.1f} h"),
                html.Td("—"), html.Td("—")
            ]))
        kpi_children = [
            dbc.Table([
                html.Thead(html.Tr([html.Th("Leg"), html.Th("Dist"), html.Th("Time"), html.Th("Budget"), html.Th("CO₂")])),
                html.Tbody(rows)
            ], bordered=True, hover=True, size="sm")
        ]

    return map_el, alerts_cards, recs_el, farm_options, route_msg, kpi_children

@app.callback(
    Output("add-msg", "children"),
    Input("btn-add", "n_clicks"),
    State("company-dd", "value"),
    State("inp-product", "value"),
    State("inp-region", "value"),
    State("inp-volume", "value"),
    prevent_initial_call=True
)
def add_supply_chain(n_clicks, company_id, crop, region, volume):
    if not crop or not region or not volume:
        return "Please fill all fields."
    payload = {"supplierId": 10, "cropId": 2, "plannedVolumeKg": float(volume), "preferredTransport": "Truck"}
    resp = api_post(f"/company/{company_id}/mapping", payload)
    if isinstance(resp, dict) and resp.get("error"):
        return f"Error: {resp['error']}"
    return "Supply chain mapping added (demo)."

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
