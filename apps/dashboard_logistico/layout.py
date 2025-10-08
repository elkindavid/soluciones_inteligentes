# apps/dashboard_logistico/layout.py

from datetime import date
import calendar
from dash import html, dcc



def build_layout():
    """
    Layout con clases Tailwind. Ajusta clases según tu diseño/prioridades.
    """

    # 📅 Calcular primer y último día del mes actual
    hoy = date.today()
    primer_dia = hoy.replace(day=1)
    ultimo_dia = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])

    return html.Div([
        # Header
        html.Div([
        html.H2("Dashboard Logístico - Soluciones Inteligentes", className="text-2xl font-semibold text-slate-800")
        ], className="mb-4"),

        # Filtros globales
        html.Div([
            html.Div([
                html.Label("Desde", className="block text-sm text-slate-700"),
                dcc.DatePickerSingle(id="dash-fecha-desde", display_format="YYYY-MM-DD", className="w-full", date=primer_dia)
            ], className="w-full md:w-1/6 px-2"),

            html.Div([
                html.Label("Hasta", className="block text-sm text-slate-700"),
                dcc.DatePickerSingle(id="dash-fecha-hasta", display_format="YYYY-MM-DD", className="w-full", date=ultimo_dia)
            ], className="w-full md:w-1/6 px-2"),

            html.Div([
                html.Label("Transportadora", className="block text-sm text-slate-700"),
                dcc.Dropdown(id="dash-transportadora", multi=True, placeholder="Selecciona", className="w-full")
            ], className="w-full md:w-1/4 px-2"),

            html.Div([
                html.Label("Material", className="block text-sm text-slate-700"),
                dcc.Dropdown(id="dash-material", multi=True, placeholder="Selecciona", className="w-full")
            ], className="w-full md:w-1/4 px-2"),

            html.Div([
                html.Label("Top N", className="block text-sm text-slate-700"),
                dcc.Input(id="dash-topn", type="number", value=10, min=1, className="w-full border rounded px-2 py-1")
            ], className="w-full md:w-1/12 px-2"),
        ], className="flex flex-wrap -mx-2 mb-4"),

        # KPIs
        html.Div([
            html.Div(id="kpi-toneladas", className="bg-white rounded shadow p-4 w-full md:w-1/4 m-2"),
            html.Div(id="kpi-viajes", className="bg-white rounded shadow p-4 w-full md:w-1/4 m-2"),
            html.Div(id="kpi-proveedores", className="bg-white rounded shadow p-4 w-full md:w-1/4 m-2"),
            html.Div(id="kpi-alertas", className="bg-white rounded shadow p-4 w-full md:w-1/4 m-2"),
        ], className="flex flex-wrap -mx-2 mb-6"),

        # Gráficos (grid responsiva)
        html.Div([
            html.Div(dcc.Graph(id="graf-rutas"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-materiales"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-origenes"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-centros"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-calidad"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-vehiculos"), className="w-full md:w-1/2 p-2"),
        ], className="flex flex-wrap -mx-2"),

        # Alertas (gráfico/tabla)
        html.H4("Alertas por desviación por placa", className="mt-6 mb-2 text-lg"),
        dcc.Loading(dcc.Graph(id="tabla-alertas"), type="default"),

        # store para datos
        dcc.Store(id="store-df")
    ], className="container mx-auto p-4")

