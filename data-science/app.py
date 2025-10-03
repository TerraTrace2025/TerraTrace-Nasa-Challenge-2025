"""
CropPulse Frontend (Option A) — Dash/Plotly + Leaflet MVP

How to run:
1) pip install -r requirements (see list below)
2) export API_BASE=http://localhost:8000  # your FastAPI base
3) python app.py

Requirements (pip):
 dash==2.17.1
 dash-bootstrap-components==1.6.0
 dash-leaflet==0.1.28
 plotly==5.23.0
 requests==2.32.3

Notes:
- Works with the FastAPI contracts provided earlier.
- If API is unavailable, set USE_MOCK=True to use local dummy data.
- Map overlays are placeholder toggles; wire real raster tiles/overlays later.
"""
import os
import json
import math
import time
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
import plotly.graph_objects as go

from dash import Dash, html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# ----------------------------
# Config
# ----------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
REFRESH_MS = int(os.getenv("REFRESH_MS", "30000"))  # 30s for demo
DEFAULT_COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))

# ----------------------------
# Helpers
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
            dl.Tooltip(f"{s['Name']} — {s.get('CurrentTier','?')}") ,
            dl.Popup([
                html.B(s["Name"]), html.Br(),
                html.Div(s.get("Location","")),
                html.Div(f"Tier: {s.get('CurrentTier','?')}")
            ])
        ]
    )


def build_map(suppliers: List[Dict[str, Any]]):
    markers = [marker_for_supplier(s) for s in suppliers if s.get("Lat") and s.get("Lon")]
    return dl.Map(center=(47.0, 8.0), zoom=6, children=[
        dl.TileLayer(),
        dl.LayerGroup(markers, id="supplier-markers")
    ], style={"height": "65vh", "width": "100%"})


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
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=220, yaxis_title="Risk (0-100)")
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
            dbc.CardHeader("Risk Timeline"),
            dbc.CardBody(risk_timeline_placeholder())
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
# Callbacks
# ----------------------------
@app.callback(
    Output("map-container", "children"),
    Output("alerts-list", "children"),
    Output("recs-panel", "children"),
    Input("tick", "n_intervals"),
    Input("company-dd", "value"),
)
def refresh(n, company_id):
    suppliers = api_get("/suppliers")
    if isinstance(suppliers, dict) and "_fallback" in suppliers:
        suppliers = suppliers["_fallback"]
    map_el = build_map(suppliers)

    alerts = api_get(f"/company/{company_id}/alerts")
    if isinstance(alerts, dict) and "_fallback" in alerts:
        alerts = alerts["_fallback"]
    sup_index = {s["SupplierId"]: s for s in suppliers}
    alerts_cards = [alert_card(a, sup_index) for a in alerts]
    if not alerts_cards:
        alerts_cards = [html.Div("No active alerts.")]

    recs = api_get(f"/company/{company_id}/recommendations/latest")
    if isinstance(recs, dict) and "_fallback" in recs:
        recs = recs["_fallback"]
    recs_el = recommendations_panel(recs, sup_index)

    return map_el, alerts_cards, recs_el


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
    # In a real app, resolve crop name -> CropId and region->SupplierId via backend.
    # Here we just echo success.
    payload = {"supplierId": 10, "cropId": 2, "plannedVolumeKg": float(volume), "preferredTransport": "Truck"}
    resp = api_post(f"/company/{company_id}/mapping", payload)
    if isinstance(resp, dict) and resp.get("error"):
        return f"Error: {resp['error']}"
    return "Supply chain mapping added (demo)."


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
