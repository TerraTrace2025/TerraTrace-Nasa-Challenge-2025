import os
import logging
import uvicorn
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

USE_OSRM = os.getenv("USE_OSRM", "true").lower() == "true"
REFRESH_MS = int(os.getenv("REFRESH_MS", "30000"))  # 30s
DEFAULT_COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))
APP_PORT = int(os.getenv("PORT", "8051"))


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
        norm.append({
            "AlertId": a.get("AlertId") or a.get("alertId"),
            "CompanyId": a.get("CompanyId") or a.get("companyId"),
            "SupplierId": a.get("SupplierId") or a.get("supplierId"),
            "CropId": a.get("CropId") or a.get("cropId"),
            "CreatedAt": a.get("CreatedAt") or a.get("createdAt"),
            "Severity": a.get("Severity") or a.get("severity") or "INFO",
            "Title": a.get("Title") or a.get("title") or "",
            "Details": a.get("Details") or a.get("details") or "",
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
# UI helpers
# ----------------------------
TIER_COLOR = {"LOW": "#22c55e", "MED": "#f59e0b", "HIGH": "#ef4444", None: "#93c5fd"}
SEVERITY_BADGE = {
    "INFO": {"color": "secondary", "text": "INFO"},
    "WARN": {"color": "warning", "text": "WARN"},
    "CRIT": {"color": "danger", "text": "CRIT"},
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
    """Erzeuge Polyline-Layer von jedem Supplier zur Company-Location."""
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
            line = dl.Polyline(positions=routed["coords"], color="#2563eb", weight=3, opacity=0.8)
        else:
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
            "risk": s.get("risk_score") or s.get("risk") or None,
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

    # Routen + Alerts as before...
    route_layers = build_supplier_routes(company, suppliers)

    # Alert overlays (CircleMarkers) at supplier if SupplierId present, else at company
    alert_overlays = []
    suppliers_index = {s.get("SupplierId"): s for s in suppliers}
    for a in alerts:
        sev = (a.get("Severity") or "INFO").upper()
        color = {"INFO": "#3b82f6", "WARN": "#f59e0b", "CRIT": "#ef4444"}.get(sev, "#64748b")
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
        dl.TileLayer(),
        dl.LayerGroup(alert_overlays, id="alert-overlays"),
        dl.LayerGroup(marker_children, id="entity-markers"),
        dl.LayerGroup(route_layers, id="route-layers"),
    ]
    return dl.Map(center=(47.0, 8.0), zoom=6, children=children, style={"height": "65vh", "width": "100%"})


def alert_card(a: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):
    details = a.get("Details")

    try:
        det = json.loads(details) if isinstance(details, str) else (details or {})
    except Exception:
        det = {"risk_index": "?", "why": details}

    # Ensure stable keys for card
    why_text = det.get("why") or det.get("message") or a.get("Title") or ""
    risk_index = det.get("risk_index") if det.get("risk_index") is not None else det.get("risk_score")

    sev = SEVERITY_BADGE.get((a.get("Severity") or "WARN").upper(), SEVERITY_BADGE["WARN"])
    sup = suppliers_index.get(a.get("SupplierId")) or {"Name": f"Supplier {a.get('SupplierId')}"}

    return dbc.Card(
        dbc.CardBody([
            # Header with severity + title
            html.Div([
                dbc.Badge(sev["text"], color=sev["color"], className="me-2"),
                html.Span(a.get("Title", ""), className="fw-bold text-dark fs-5"),
            ], className="d-flex align-items-center mb-2"),

            # Metadata line
            html.Small(
                f"Supplier: {sup.get('Name').capitalize()}\n",
                className="text-muted d-block"
            ),

            html.Small(
                f"Crop: {a.get('CropId').capitalize()}\n",
                className="text-muted d-block"
            ),

            html.Small(
                f"Agreed Volume: {a.get('Details').get('agreed_volume', '?')} t\n",
                className="text-muted d-block"
            ),

            # Why text / description
            html.Div(why_text, className="mt-3 text-body"),

            # Risk index
            html.Div(
                f"Risk Index: {risk_index if risk_index is not None else '?'}",
                className="mt-3 fw-semibold text-danger"
            ),
        ]),
        className="mb-3 shadow-sm rounded-3 border-0"
    )


def recommendations_panel(recs: Dict[str, Any], suppliers_index: Dict[Any, Dict[str, Any]]):
    items = []
    for r in recs.get("alternatives", []):
        sup = suppliers_index.get(r.get("supplierId")) or {"Name": f"Supplier {r.get('supplierId')}"}
        items.append(dbc.ListGroupItem([
            html.Div([html.B(sup.get("Name")), html.Span(f" — coverage {int(100*(r.get('coverage') or 0))}%")]),
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
def severity_from_risk(risk_score: Optional[float]) -> str:
    if risk_score is None:
        return "INFO"
    try:
        r = float(risk_score)
    except Exception:
        return "INFO"
    if r >= 3:
        return "CRIT"
    if r >= 1:
        return "WARN"
    return "INFO"

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
        risk_score = stock.get("risk_score")
        message = stock.get("message") or f"Stock #{stock_id} update"
        expiry_date = stock.get("expiry_date")
        supplier_id = stock.get("supplier_id")

        severity = severity_from_risk(risk_score)
        created_at = stock.get("created_at") or dt.datetime.utcnow().isoformat()

        alerts.append({
            "AlertId": f"stock-{stock_id}",
            "CompanyId": company_id,
            "SupplierId": supplier_id,
            "CropId": crop_type,
            "CreatedAt": created_at,
            "Severity": severity,
            "Title": f"{crop_type.title() if crop_type else 'Crop'} alert",
            "Details": {
                "risk_score": risk_score,
                "why": message,
                "expiry_date": expiry_date,
                "mapping_id": m.get("id"),
                "transportation_mode": m.get("transportation_mode"),
                "agreed_volume": m.get("agreed_volume"),
            },
        })
    return alerts



# ----------------------------
# Dash App
# ----------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "TerraTrace - Climate-Smart Supply Chains"

sidebar = dbc.Card([
    dbc.CardBody([
        html.H5("Available Suppliers"),
        html.Div(id="suppliers-list", style={"maxHeight": "35vh", "overflowY": "auto"}),
        html.Hr(),
        html.H5("Available Stock"),
        html.Div(id="stocks-list", style={"maxHeight": "35vh", "overflowY": "auto"})
    ])
], className="h-100")



content = dbc.Row([
            dbc.Col(html.Div(id="map-container"), md=8),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Alerts"),
                    dbc.CardBody(
                        html.Div(
                            id="alerts-list",
                            style={
                                "maxHeight": "65vh",   # same as map height
                                "overflowY": "auto"   # enable vertical scrolling
                            }
                        )
                    )
                ]),
                md=4
            ),
        ], className="mt-2"), dcc.Interval(id="tick", interval=REFRESH_MS, n_intervals=0)


app.layout = html.Div([
    dcc.Store(id="token-store"),
    dcc.Store(id="selected-supplier-id"),


    # Login Card
    dbc.Card([
        html.H3("Login", className="text-center mb-4"),
        dbc.Label("Company Name"),
        dbc.Input(id="company-name", type="text", placeholder="Enter company name", className="mb-3"),
        dbc.Label("Password"),
        dbc.Input(id="password", type="password", placeholder="Enter password", className="mb-3"),
        dbc.Button("Login", id="login-button", color="primary", className="d-block w-100"),
        html.Div(id="login-feedback", className="mt-3 text-center text-danger")
    ], style=CARD_STYLE, id="login-card"),

    # Dashboard container (hidden until login)
    dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("TerraTrace — Climate-Smart Supply Chains"), md=8),
        ], className="mt-2"),
        dbc.Row([
            dbc.Col(sidebar, md=3, style={"height": "100%"}),
            dbc.Col(content, md=9, style={"height": "100%"}),
        ], style={"height": "90%"}, className="mt-2"),
    ], id="dashboard-container", style={"display": "none", **CONTAINER_STYLE})
])


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
# Login Callback
# ----------------------------------
@app.callback(
    Output("token-store", "data"),
    Output("login-feedback", "children"),
    Output("login-card", "style"),
    Output("dashboard-container", "style"),
    Input("login-button", "n_clicks"),
    State("company-name", "value"),
    State("password", "value"),
    prevent_initial_call=True
)
def login(n_clicks, company_name, password):
    """Handles user login via API and shows dashboard after success."""
    if not company_name or not password:
        return None, "Please enter both fields", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}

    try:
        response = requests.post(f"{API_BASE_URL}/auth/login", json={
            "company_name": company_name,
            "password": password
        })
        if response.status_code != 200:
            logger.warning(f"Login failed for {company_name}: {response.text}")
            return None, "Invalid credentials", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}

        token = response.json().get("access_token")
        logger.info(f"Login successful for company '{company_name}'")

        # Hide login card, show dashboard
        return token, "", {"display": "none"}, {"display": "block", **CONTAINER_STYLE}

    except Exception as e:
        logger.exception("Login error")
        return None, f"Error: {str(e)}", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}


@app.callback(
    Output("suppliers-list", "children"),
    Input("token-store", "data"),
    prevent_initial_call=True
)
def load_suppliers(token):
    if not token:
        return dbc.ListGroup([dbc.ListGroupItem("Please login.")])
    suppliers_raw = get_suppliers(token)
    suppliers = normalize_suppliers(suppliers_raw if isinstance(suppliers_raw, list) else [])
    supplier_items = [
        dbc.ListGroupItem(
            f"{s.get('Name','Unknown')} — Tier {s.get('CurrentTier','?')}",
            id={"type": "supplier-item", "index": s.get("SupplierId")},
            action=True
        ) for s in suppliers
    ]
    return dbc.ListGroup(supplier_items, flush=True)



# ----------------------------------
# Stocks list: refresh when a supplier is selected
# ----------------------------------
@app.callback(
    Output("stocks-list", "children"),
    Input("selected-supplier-id", "data"),
    Input("token-store", "data"),
    prevent_initial_call=True
)
def show_supplier_stocks(selected_supplier_id, token):
    if not token:
        return dbc.Alert("Please login to see stocks.", color="warning", className="mb-0")
    if not selected_supplier_id:
        return dbc.ListGroup([dbc.ListGroupItem("Select a supplier to see available stock.")], flush=True)

    data = get_supplier_stocks(selected_supplier_id, token)

    # handle API errors
    if not isinstance(data, list):
        if isinstance(data, dict) and data.get("error"):
            return dbc.Alert(f"Could not load stocks: {data['error']}", color="danger", className="mb-0")
        # unexpected shape
        return dbc.Alert("No stock data available for this supplier.", color="secondary", className="mb-0")

    stocks = normalize_stocks(data)
    if not stocks:
        return dbc.ListGroup([dbc.ListGroupItem("No available stock for this supplier.")], flush=True)

    items = [stock_item_card(s) for s in stocks]
    return dbc.ListGroup(items, flush=True)


# ----------------------------------
# Live refresh: map + alerts
# ----------------------------------
@app.callback(
    Output("map-container", "children"),
    Output("alerts-list", "children"),
    Input("tick", "n_intervals"),
    Input("token-store", "data"),
    Input("selected-supplier-id", "data"),
    prevent_initial_call=True
)
def refresh_dashboard(n, token, selected_supplier_id):
    # if no token yet
    if not token:
        return (
            html.Div("Please login first."),
            [html.Div("No alerts (not logged in).")]
        )

    # run the API calls once (either immediately after login or every tick)
    company_raw = get_company(token)
    company = normalize_company(company_raw)
    company_id = company.get("CompanyId") or DEFAULT_COMPANY_ID

    suppliers_raw = get_suppliers(token)
    suppliers = normalize_suppliers(suppliers_raw if isinstance(suppliers_raw, list) else [])

    # 🔑 get mappings and filter suppliers
    mappings = get_company_mappings(token)
    supplier_ids_in_use = {
        m.get("supplier_id") for m in mappings if m.get("company_id") == company_id
    }
    suppliers_in_use = [s for s in suppliers if s.get("SupplierId") in supplier_ids_in_use]

    alerts_raw = build_alerts_from_api(company_id, token)
    alerts = normalize_alerts(alerts_raw)

    suppliers_index = {s.get("SupplierId"): s for s in suppliers_in_use}
    alert_cards = (
        [alert_card(a, suppliers_index) for a in alerts]
        if alerts
        else [html.Div("No alerts at this time.", className="text-muted")]
    )

    map_obj = build_map(company, suppliers_in_use, alerts, selected_supplier_id)

    # highlight selected supplier if any
    if selected_supplier_id:
        sel = next((s for s in suppliers if s.get("SupplierId") == selected_supplier_id), None)
        if sel and sel.get("Lat") and sel.get("Lon"):
            map_obj.children.append(
                dl.CircleMarker(
                    center=(sel["Lat"], sel["Lon"]),
                    radius=8,
                    color='#3b82f6',
                )
            )

    return map_obj, alert_cards



# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "127.0.0.1")
    reload_flag = os.getenv("FASTAPI_RELOAD", "True").lower() in ("true", "1", "yes")

    logger.info("Starting Food-waste frontend...")
    logger.info(f"Host: {host}, Reload: {reload_flag}")

    if reload_flag:
        app.run(host=host, port=8050, debug=True)
    else:
        uvicorn.run("src.app:app.server", host=host, port=8050, reload=reload_flag)
