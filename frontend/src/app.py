import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import dash_table
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY], suppress_callback_exceptions=True)
server = app.server

# ---------- Styles ----------
CARD_STYLE = {"width": "400px", "margin": "auto", "marginTop": "150px", "padding": "20px"}
CONTAINER_STYLE = {"height": "100vh", "overflow": "hidden", "padding": "0"}

# ---------- Layout ----------
app.layout = html.Div([
    dcc.Store(id="token-store"),

    # Login Card (reverting to old styling)
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

            # Left: Map
            dbc.Col([
                dl.Map(
                    dl.TileLayer(),
                    id="company-map",
                    style={"width": "100%", "height": "100%"}
                )
            ], width=6, style={"height": "100%"}),

            # Right: Panels
            dbc.Col([
                dbc.Card(id="company-card", style={"marginBottom": "10px"}),
                dbc.Card([
                    html.H5("Suppliers", className="card-title"),
                    dash_table.DataTable(
                        id="suppliers-table",
                        columns=[
                            {"name": "Name", "id": "name"},
                            {"name": "City", "id": "city"},
                            {"name": "Country", "id": "country"},
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left"},
                        style_header={"fontWeight": "bold"}
                    )
                ], style={"marginBottom": "10px"}),

                dbc.Card([
                    html.H5("Mappings", className="card-title"),
                    dash_table.DataTable(
                        id="mappings-table",
                        columns=[
                            {"name": "Supplier", "id": "supplier_name"},
                            {"name": "Crop Type", "id": "crop_type"},
                            {"name": "Agreed Volume", "id": "agreed_volume"}
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left"},
                        style_header={"fontWeight": "bold"}
                    )
                ], style={"marginBottom": "10px"})
            ], width=6, style={"height": "100%", "overflowY": "auto"})
        ], style={"height": "100%"})
    ], id="dashboard-container", style={"display": "none", **CONTAINER_STYLE})
])

# ---------- Callbacks ----------
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
    if not company_name or not password:
        return None, "Please enter both fields", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}

    try:
        response = requests.post(f"{API_BASE_URL}/auth/login", json={
            "company_name": company_name,
            "password": password
        })
        if response.status_code != 200:
            return None, "Invalid credentials", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}
        token = response.json()["access_token"]
        return token, "", {"display": "none"}, {"display": "block", **CONTAINER_STYLE}
    except Exception as e:
        return None, f"Error: {str(e)}", CARD_STYLE, {"display": "none", **CONTAINER_STYLE}

@app.callback(
    Output("company-card", "children"),
    Output("suppliers-table", "data"),
    Output("mappings-table", "data"),
    Output("company-map", "children"),
    Input("token-store", "data"),
    prevent_initial_call=True
)
def load_dashboard(token):
    if not token:
        return "", [], [], [dl.TileLayer()]

    headers = {"Authorization": f"Bearer {token}"}

    # --- Company info ---
    comp_res = requests.get(f"{API_BASE_URL}/companies/", headers=headers)
    company = comp_res.json()
    company_card = dbc.CardBody([
        html.H4(company["name"], className="card-title"),
        html.P(f"Budget Limit: {company['budget_limit']}"),
        html.P(f"City: {company['city']}, {company['country']}"),
        html.P(f"Transport: {company['preferred_transport_modes']}")
    ])

    # --- Suppliers ---
    sup_res = requests.get(f"{API_BASE_URL}/suppliers/", headers=headers)
    suppliers = sup_res.json()

    # --- Mappings ---
    maps_res = requests.get(f"{API_BASE_URL}/mappings/", headers=headers)
    all_mappings = maps_res.json()

    # Filter mappings for this company
    company_mappings = [m for m in all_mappings if m["company_id"] == company["id"]]

    # Join supplier names
    mappings = []
    for m in company_mappings:
        # Find supplier name from suppliers list
        supplier_name = next((s["name"] for s in suppliers if s["id"] == m["supplier_id"]), "Unknown")
        mappings.append({
            "supplier_name": supplier_name,
            "crop_type": m.get("crop_type", ""),
            "agreed_volume": m.get("agreed_volume", "")
        })

    # --- Map markers ---
    markers = [
        dl.Marker(position=[company["latitude"], company["longitude"]],
                  children=dl.Popup(html.B(f"Company: {company['name']}"))),
    ]
    for s in suppliers:
        markers.append(dl.Marker(position=[s["latitude"], s["longitude"]],
                                 children=dl.Popup(html.B(f"Supplier: {s['name']}"))))

    # --- Calculate bounds to fit all markers ---
    all_coords = [[company["latitude"], company["longitude"]]] + \
                 [[s["latitude"], s["longitude"]] for s in suppliers]
    min_lat = min(c[0] for c in all_coords)
    max_lat = max(c[0] for c in all_coords)
    min_lon = min(c[1] for c in all_coords)
    max_lon = max(c[1] for c in all_coords)
    bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    # Add TileLayer and markers to map
    map_children = [dl.TileLayer()] + markers

    # Return everything
    return company_card, suppliers, mappings, dl.Map(children=map_children, bounds=bounds, style={"width": "100%", "height": "100%"})

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
