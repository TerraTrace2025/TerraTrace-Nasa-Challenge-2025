"""

TerraTrace / CropPulse — Dash + Leaflet Frontend (Cloud-Backend ready)

- Standardmäßig an das deployte Backend angebunden.

- Robust gegen API-Feldschema (SupplierId vs supplierId, Lat/Lon vs lat/lon, …).

- Optional: lädt Farm-Standorte aus harvest_locations.xlsx (falls vorhanden).

- OSRM-Routing (driving) optional mit Fallback auf Luftlinie.

"""

 

import os

import json

import math

import datetime as dt

from typing import Any, Dict, List, Optional

 

import requests

import plotly.graph_objects as go

 

from dash import Dash, html, dcc, Input, Output, State

import dash_bootstrap_components as dbc

import dash_leaflet as dl

 

# ----------------------------

# Config

# ----------------------------

API_BASE = os.getenv(

    "API_BASE",

    "https://upmc2drqpn.eu-central-1.awsapprunner.com/api"

)

USE_OSRM = os.getenv("USE_OSRM", "true").lower() == "true"

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

REFRESH_MS = int(os.getenv("REFRESH_MS", "30000"))  # 30s

DEFAULT_COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))

APP_PORT = int(os.getenv("PORT", "8051"))

 

# ----------------------------

# Helpers: HTTP

# ----------------------------

def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:

    """GET helper with graceful fallback to mock_get when USE_MOCK=true or on error."""

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

    """POST helper with graceful errors; mock when USE_MOCK=true."""

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

# Mock / Defaults for offline demo

# ----------------------------

RETAILER_LOCATION = (47.3769, 8.5417)  # Zürich

DEFAULT_LOCATIONS_DICT: Dict[str, List[Dict[str, Any]]]={

    "Wheat": [

        {"name": "Farm A (BE)", "lat": 46.98, "lon": 7.45},

        {"name": "Farm B (SO)", "lat": 47.21, "lon": 7.52}

    ],

    "Potatoes": [

        {"name": "Farm C (TG)", "lat": 47.60, "lon": 9.05},

        {"name": "Farm D (AG)", "lat": 47.42, "lon": 8.24}

    ],

}

 

MOCK_WAREHOUSES = [

    {"id": 201, "name": "Warehouse Zürich", "lat": 47.39, "lon": 8.51},

    {"id": 202, "name": "Warehouse Bern",   "lat": 46.95, "lon": 7.43},

]

 

MOCK_SUPPLIERS = [

    {"SupplierId": 10, "Name": "fenaco",     "Location": "Bern, CH",    "Lat": 46.948, "Lon": 7.447, "TransportModes": "Truck,Train", "CurrentTier": "MED"},

    {"SupplierId": 11, "Name": "Supplier Y", "Location": "Thurgau, CH", "Lat": 47.6,   "Lon": 9.1,   "TransportModes": "Truck",       "CurrentTier": "LOW"},

    {"SupplierId": 12, "Name": "Supplier Z", "Location": "Tyrol, AT",   "Lat": 47.2,   "Lon": 11.3,  "TransportModes": "Truck,Train", "CurrentTier": "HIGH"},

]

MOCK_ALERTS = [

    {"AlertId": 1, "CompanyId": 1, "SupplierId": 12, "CropId": 2, "CreatedAt": "2025-09-29T09:00:00",

     "Severity": "CRIT", "Title": "Potatoes @ Supplier Z high risk",

     "Details": json.dumps({"risk_index": 78, "why": "Heatwave + soil moisture deficit"}), "IsActive": 1},

]

MOCK_RECS = {

    "alternatives": [

        {"supplierId": 11, "coverage": 0.8, "cost_delta_pct": -3.5, "co2_tonne_km": 0.12,

         "risk_index": 24, "reasoning": "Low risk; ample potatoes; near expiry in 9d"},

        {"supplierId": 10, "coverage": 0.4, "cost_delta_pct": +0.5, "co2_tonne_km": 0.08,

         "risk_index": 55, "reasoning": "Medium risk; close distance"}

    ]

}

def mock_get(path: str, _params: Optional[Dict[str, Any]] = None):

    if path.startswith("/suppliers"): return MOCK_SUPPLIERS

    if path.startswith(f"/company/{DEFAULT_COMPANY_ID}/alerts"): return MOCK_ALERTS

    if path.startswith(f"/company/{DEFAULT_COMPANY_ID}/recommendations"): return MOCK_RECS

    return {}

 

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

        try: lat = float(lat) if lat is not None else None

        except: lat = None

        try: lon = float(lon) if lon is not None else None

        except: lon = None

        norm.append({

            "SupplierId": sid, "Name": name, "Lat": lat, "Lon": lon,

            "CurrentTier": tier, "Location": loc, "TransportModes": modes, "_raw": s

        })

    return norm

 

def normalize_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    norm = []

    for a in alerts or []:

        norm.append({

            "AlertId": a.get("AlertId") or a.get("alertId"),

            "CompanyId": a.get("CompanyId") or a.get("companyId"),

            "SupplierId": a.get("SupplierId") or a.get("supplierId"),

            "CropId": a.get("CropId") or a.get("cropId"),

            "CreatedAt": a.get("CreatedAt") or a.get("createdAt"),

            "Severity": a.get("Severity") or a.get("severity") or "INFO",

            "Title": a.get("Title") or a.get("title") or "",

            "Details": a.get("Details") or a.get("details") or "",

            "IsActive": a.get("IsActive") or a.get("isActive") or 0,

        })

    return norm

 

def normalize_recs(recs: Dict[str, Any]) -> Dict[str, Any]:

    out = {"alternatives": []}

    alts = recs.get("alternatives") or recs.get("Alternatives") or []

    for r in alts:

        out["alternatives"].append({

            "supplierId": r.get("supplierId") or r.get("SupplierId") or r.get("id"),

            "coverage": r.get("coverage") or r.get("Coverage") or 0,

            "cost_delta_pct": r.get("cost_delta_pct") or r.get("costDeltaPct") or 0,

            "co2_tonne_km": r.get("co2_tonne_km") or r.get("co2TonneKm") or 0,

            "risk_index": r.get("risk_index") or r.get("riskIndex") or None,

            "reasoning": r.get("reasoning") or "",

        })

    return out

 

# ----------------------------

# Optional: Farm-Locations aus Excel laden

# ----------------------------

def load_locations_from_excel(path="harvest_locations.xlsx") -> Dict[str, List[Dict[str, Any]]]:

    if not os.path.exists(path):

        return DEFAULT_LOCATIONS_DICT

    try:

        import pandas as pd

        df = pd.read_excel(path)

        # Erwartete Spalten: Crop, Name, Lat, Lon (case-insensitive tolerant)

        cols = {c.lower(): c for c in df.columns}

        crop_col = cols.get("crop") or "Crop"

        name_col = cols.get("name") or "Name"

        lat_col  = cols.get("lat")  or "Lat"

        lon_col  = cols.get("lon")  or "Lon"

        locations: Dict[str, List[Dict[str, Any]]] = {}

        for _, row in df.iterrows():

            crop = str(row[crop_col]).strip()

            if not crop:

                continue

            entry = {

                "name": str(row[name_col]),

                "lat": float(row[lat_col]),

                "lon": float(row[lon_col]),

            }

            locations.setdefault(crop, []).append(entry)

        return locations or DEFAULT_LOCATIONS_DICT

    except Exception:

        return DEFAULT_LOCATIONS_DICT

 

LOCATIONS_DICT = load_locations_from_excel()

 

# ----------------------------

# UI helpers

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

        center=(s.get("Lat") or 0, s.get("Lon") or 0),

        radius=10,

        color=color,

        children=[

            dl.Tooltip(f"{s.get('Name') or 'Supplier'} — {s.get('CurrentTier','?')}"),

            dl.Popup([

                html.B(s.get("Name") or "Supplier"), html.Br(),

                html.Div(s.get("Location","")),

                html.Div(f"Tier: {s.get('CurrentTier','?')}")

            ])

        ]

    )

 

def build_map(suppliers: List[Dict[str, Any]], extra_layers: Optional[List[Any]] = None):

    markers = [marker_for_supplier(s) for s in suppliers if s.get("Lat") and s.get("Lon")]

    children = [dl.TileLayer(), dl.LayerGroup(markers, id="supplier-markers")]

    if extra_layers: children.extend(extra_layers)

    return dl.Map(center=(47.0, 8.0), zoom=6, children=children, style={"height": "65vh", "width": "100%"})

 

def alert_card(a: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):

    sev = SEVERITY_BADGE.get((a.get("Severity") or "WARN"), SEVERITY_BADGE["WARN"])

    sup = suppliers_index.get(a.get("SupplierId")) or {"Name": f"Supplier {a.get('SupplierId')}"}

    details = a.get("Details")

    try:

        det = json.loads(details) if isinstance(details, str) else details

    except Exception:

        det = {"risk_index": "?", "why": details}

    return dbc.Card([

        dbc.CardBody([

            html.Div([dbc.Badge(sev["text"], color=sev["color"], className="me-2"), html.Span(a.get("Title",""), className="fw-bold")]),

            html.Small(f"Supplier: {sup.get('Name')} • CropId: {a.get('CropId')} • {a.get('CreatedAt')}", className="text-muted d-block mt-1"),

            html.Div(det.get("why",""), className="mt-2"),

            html.Div(f"Risk Index: {det.get('risk_index','?')}", className="mt-1"),

        ])

    ], className="mb-2")

 

def recommendations_panel(recs: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):

    items = []

    for r in recs.get("alternatives", []):

        sup = suppliers_index.get(r.get("supplierId")) or {"Name": f"Supplier {r.get('supplierId')}"}

        items.append(dbc.ListGroupItem([

            html.Div([html.B(sup.get("Name")), html.Span(f" — coverage {int(100*(r.get('coverage') or 0))}%")]),

            html.Div(f"Risk {r.get('risk_index','?')} | ΔCost {r.get('cost_delta_pct',0)}% | CO₂ {r.get('co2_tonne_km',0)} t·km"),

            html.Div(r.get("reasoning",""), className="text-muted")

        ]))

    if not items: items = [dbc.ListGroupItem("No recommendations yet.")]

    return dbc.ListGroup(items)

 

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

 

from math import radians, sin, cos, asin, sqrt

def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0

    dlat = radians(lat2-lat1)

    dlon = radians(lon2-lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2

    return 2*R*asin(sqrt(a))

 

def _decode_polyline5(polyline: str) -> List[tuple]:

    coords=[]; index=0; lat=0; lon=0; length=len(polyline)

    while index<length:

        shift=0; result=0

        while True:

            b=ord(polyline[index])-63; index+=1

            result |= (b&0x1f) << shift; shift += 5

            if b<0x20: break

        dlat = ~(result>>1) if (result & 1) else (result>>1)

        lat += dlat

        shift=0; result=0

        while True:

            b=ord(polyline[index])-63; index+=1

            result |= (b&0x1f) << shift; shift += 5

            if b<0x20: break

        dlon = ~(result>>1) if (result & 1) else (result>>1)

        lon += dlon

        coords.append((lat/1e5, lon/1e5))

    return coords

 

def osrm_route(a: tuple, b: tuple) -> Optional[Dict[str, Any]]:

    if not USE_OSRM: return None

    url = f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}"

    params = {"overview":"full","geometries":"polyline","alternatives":"false"}

    try:

        r = requests.get(url, params=params, timeout=8)

        r.raise_for_status()

        data = r.json()

        routes = data.get("routes") or []

        if not routes: return None

        route = routes[0]

        coords = _decode_polyline5(route.get("geometry",""))

        return {

            "coords": coords,

            "distance_km": (route.get("distance") or 0)/1000.0,

            "duration_h":  (route.get("duration") or 0)/3600.0

        }

    except Exception:

        return None

 

def build_route_layers(farm: Optional[Dict[str, Any]], warehouse: Optional[Dict[str, Any]], route_polylines: Optional[List[List[tuple]]]=None):

    markers=[]

    if farm:

        markers.append(dl.Marker(position=(farm["lat"], farm["lon"]), children=[dl.Tooltip(f"Farm: {farm['name']}")]))

    if warehouse:

        markers.append(dl.Marker(position=(warehouse["lat"], warehouse["lon"]), children=[dl.Tooltip(f"Warehouse: {warehouse['name']}")]))

    markers.append(dl.Marker(position=RETAILER_LOCATION, children=[dl.Tooltip("Retailer (Zürich)")]))

 

    legs=[]

    if farm and warehouse: legs.append([(farm["lat"], farm["lon"]), (warehouse["lat"], warehouse["lon"])])

    if warehouse:           legs.append([(warehouse["lat"], warehouse["lon"]), RETAILER_LOCATION])

    elif farm:              legs.append([(farm["lat"], farm["lon"]), RETAILER_LOCATION])

 

    poly_src = route_polylines if route_polylines else legs

    polylines = [dl.Polyline(positions=leg, weight=4, opacity=0.8) for leg in poly_src]

    return [dl.LayerGroup(markers + polylines, id="route-layer")]

 

def compute_kpis(farm: Optional[Dict[str, Any]], warehouse: Optional[Dict[str, Any]], mode: str="Truck", volume_kg: float=1000.0):

    legs=[]; labels=[]

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

        return {"total":{"distance_km":0.0,"time_h":0.0,"budget_chf":0.0,"co2_t":0.0},"legs":[]}

 

    cost_per_km = COST_PER_KM_BY_MODE.get(mode, 1.2)

    co2_per_tkm = CO2_PER_TKM_BY_MODE.get(mode, 0.12)

    speed       = SPEED_KMPH_BY_MODE.get(mode, 60.0)

 

    total_dist=0.0; total_time=0.0; legs_out=[]

    for idx, (a,b) in enumerate(legs):

        routed = osrm_route(a,b)

        if routed:

            dist_km = routed["distance_km"]; dur_h = routed["duration_h"]

        else:

            dist_km = haversine_km(a[0],a[1],b[0],b[1]); dur_h = dist_km/speed if speed>0 else 0.0

        total_dist += dist_km; total_time += dur_h

        legs_out.append({"label": labels[idx], "distance_km": dist_km, "time_h": dur_h})

 

    budget = total_dist * cost_per_km

    co2    = (volume_kg/1000.0) * total_dist * co2_per_tkm

    return {"total":{"distance_km":total_dist,"time_h":total_time,"budget_chf":budget,"co2_t":co2},"legs":legs_out}

 

# ----------------------------

# Dash App

# ----------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.title = "TerraTrace — Climate-Smart Supply Chains"

 

sidebar = dbc.Card([

    dbc.CardBody([

        html.H5("Filters"),

        dbc.Label("Company"),

        dcc.Dropdown(id="company-dd", options=[{"label":"LANDI","value":1}], value=DEFAULT_COMPANY_ID, clearable=False),

 

        dbc.Label("Overlay"),

        dcc.Checklist(

            id="overlay-checks",

            options=[{"label":"Temperature","value":"TEMP"},{"label":"Precipitation","value":"PRECIP"},{"label":"Soil Moisture","value":"SOIL"},{"label":"NDVI","value":"NDVI"}],

            value=["TEMP"], inputStyle={"marginRight":"6px"}

        ),

        html.Hr(),

        html.H6("Route Planner"),

        dbc.Label("Crop"),

        dcc.Dropdown(id="route-crop-dd", options=[{"label":c,"value":c} for c in sorted(LOCATIONS_DICT.keys())], placeholder="Select crop…"),

        dbc.Label("Farm"),

        dcc.Dropdown(id="route-farm-dd", placeholder="Select farm…"),

        dbc.Label("Warehouse"),

        dcc.Dropdown(id="route-warehouse-dd", options=[{"label":w["name"],"value":w["id"]} for w in MOCK_WAREHOUSES], placeholder="Select warehouse…"),

        dbc.Label("Volume (kg)"),

        dbc.Input(id="route-volume", type="number", value=1000, min=1),

        dbc.Label("Mode"),

        dcc.Dropdown(id="route-mode", options=[{"label":"Truck","value":"Truck"},{"label":"Train","value":"Train"}], value="Truck", clearable=False),

 

        html.Small(f"Retailer fixed: Zürich {RETAILER_LOCATION}", className="text-muted d-block mb-2"),

        html.Div(id="route-msg", className="mt-1 text-info"),

        html.Hr(),

        html.H6("Add Supply Chain"),

        dbc.Input(id="inp-product", placeholder="Crop (e.g., Potatoes)", type="text"),

        dbc.Input(id="inp-region", placeholder="Region (e.g., Thurgau, CH)", type="text", className="mt-1"),

        dbc.Input(id="inp-volume", placeholder="Planned Volume (kg)", type="number", className="mt-1"),

        dbc.Button("Add", id="btn-add", color="primary", className="mt-2", n_clicks=0),

        html.Div(id="add-msg", className="mt-1 text-success"),

    ])

], className="h-100")

 

content = html.Div([

    dbc.Row([

        dbc.Col(html.Div(id="map-container"), md=8),

        dbc.Col(dbc.Card([dbc.CardHeader("Alerts"), dbc.CardBody(html.Div(id="alerts-list"))]), md=4),

    ], className="mt-2"),

    dbc.Row([

        dbc.Col(dbc.Card([dbc.CardHeader("Recommendations"), dbc.CardBody(html.Div(id="recs-panel"))]), md=6),

        dbc.Col(dbc.Card([dbc.CardHeader("Route KPIs"), dbc.CardBody(html.Div(id="kpi-panel"))]), md=6),

    ], className="mt-2"),

    dcc.Interval(id="tick", interval=REFRESH_MS, n_intervals=0)

])

 

app.layout = dbc.Container(fluid=True, children=[

    dbc.Row([

        dbc.Col(html.H3("TerraTrace — Climate-Smart Supply Chains"), md=8),

        dbc.Col(html.Div([html.Small(f"API: {API_BASE} | Mock: {USE_MOCK}")], className="text-end"), md=4)

    ], className="mt-2"),

    dbc.Row([dbc.Col(sidebar, md=3), dbc.Col(content, md=9)], className="mt-2")

])

 

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

def refresh(_n, company_id, crop_value, farm_value, warehouse_value, route_volume, route_mode):

    # --- Suppliers

    suppliers = api_get("/suppliers")

    if isinstance(suppliers, dict) and "_fallback" in suppliers:

        suppliers = suppliers["_fallback"]

    suppliers = normalize_suppliers(suppliers)

 

    # --- Route selections

    farm = None; farm_options=[]

    if crop_value:

        farms = LOCATIONS_DICT.get(crop_value, [])

        farm_options = [{"label": f["name"], "value": f["name"]} for f in farms]

        if farm_value:

            for f in farms:

                if f["name"] == farm_value:

                    farm = f; break

 

    warehouse = None

    if warehouse_value:

        for w in MOCK_WAREHOUSES:

            if w["id"] == warehouse_value:

                warehouse = w; break

 

    # --- Build route polylines via OSRM (fallback)

    poly_routes=[]

    if farm or warehouse:

        legs=[]

        if farm and warehouse: legs.append(((farm["lat"], farm["lon"]), (warehouse["lat"], warehouse["lon"])))

        if warehouse:           legs.append(((warehouse["lat"], warehouse["lon"]), RETAILER_LOCATION))

        elif farm:              legs.append(((farm["lat"], farm["lon"]), RETAILER_LOCATION))

        for (a,b) in legs:

            routed = osrm_route(a,b)

            if routed and routed.get("coords"): poly_routes.append(routed["coords"])

            else:                               poly_routes.append([a,b])

 

    route_layers = build_route_layers(farm, warehouse, route_polylines=poly_routes if poly_routes else None)

    map_el = build_map(suppliers, extra_layers=route_layers)

 

    # --- Alerts & Recommendations

    alerts = api_get(f"/company/{company_id}/alerts")

    if isinstance(alerts, dict) and "_fallback" in alerts:

        alerts = alerts["_fallback"]

    alerts = normalize_alerts(alerts)

 

    sup_index = {s["SupplierId"]: s for s in suppliers if s.get("SupplierId") is not None}

    alerts_cards = [alert_card(a, sup_index) for a in alerts] or [html.Div("No active alerts.")]

 

    recs = api_get(f"/company/{company_id}/recommendations/latest")

    if isinstance(recs, dict) and "_fallback" in recs:

        recs = recs["_fallback"]

    recs_el = recommendations_panel(normalize_recs(recs), sup_index)

 

    # --- KPI & Validation

    route_msg = "Bitte wähle eine Farm aus." if (crop_value and not farm) else ""

    kpi_children=[]

    if farm or warehouse:

        k = compute_kpis(farm, warehouse, mode=(route_mode or "Truck"), volume_kg=(route_volume or 1000))

        total = k["total"]

        rows = [html.Tr([html.Th("Total"), html.Td(f"{total['distance_km']:.1f} km"),

                         html.Td(f"{total['time_h']:.1f} h"), html.Td(f"CHF {total['budget_chf']:.0f}"),

                         html.Td(f"{total['co2_t']:.2f} t")])]

        for leg in k["legs"]:

            rows.append(html.Tr([html.Td(leg["label"]), html.Td(f"{leg['distance_km']:.1f} km"),

                                 html.Td(f"{leg['time_h']:.1f} h"), html.Td("—"), html.Td("—")]))

        kpi_children = [dbc.Table([html.Thead(html.Tr([html.Th("Leg"), html.Th("Dist"), html.Th("Time"), html.Th("Budget"), html.Th("CO₂")])),

                                   html.Tbody(rows)], bordered=True, hover=True, size="sm")]

 

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

def add_supply_chain(_n_clicks, company_id, crop, region, volume):

    if not crop or not region or not volume:

        return "Please fill all fields."

    payload = {"supplierId": 10, "cropId": 2, "plannedVolumeKg": float(volume), "preferredTransport": "Truck"}

    resp = api_post(f"/company/{company_id}/mapping", payload)

    if isinstance(resp, dict) and resp.get("error"):

        return f"Error: {resp['error']}"

    return "Supply chain mapping added (demo)."

 

# ----------------------------

# Main

# ----------------------------

# ---------- Dev Server ----------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("FASTAPI_HOST", "127.0.0.1")
    reload_flag = os.getenv("FASTAPI_RELOAD", "True").lower() in ("true", "1", "yes")

    #logger.info("Starting Food-waste frontend...")
    #logger.info(f"Host: {host}, Reload: {reload_flag}")

    uvicorn.run("src.app:app.server", host=host, port=8050, reload=reload_flag)
