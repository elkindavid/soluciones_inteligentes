from datetime import date
import calendar
from dash import html, dcc
import pandas as pd

def build_layout():
    """
    Layout con diseño mejorado usando Tailwind:
    - Filtros redondeados con sombra y espaciado limpio
    - KPIs coloridos y modernos
    - Gráficos en tarjetas con sombra
    """

    # 📅 Calcular primer y último día del mes actual
    hoy = date.today()
    primer_dia = hoy.replace(day=1)
    ultimo_dia = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])

    return html.Div([
        # 🧭 Header
        html.Div([
            html.H2("📊 Dashboard Logístico", className="text-3xl font-bold text-slate-800 text-center mb-2"),
            html.P("Monitoreo de transporte, proveedores y materiales",
                   className="text-slate-500 text-center mb-6")
        ]),

        # 🎛️ Filtros globales
        html.Div([
           html.Div([
                html.Label("Rango de Fechas", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.DatePickerRange(
                    id="dash-fecha-rango",
                    start_date=primer_dia,
                    end_date=ultimo_dia,
                    display_format="YYYY-MM-DD",
                    className="w-full",
                    clearable=True,
                    with_portal=True  # abre el selector en ventana modal (más cómodo)
                )
            ], className="w-full md:w-1/4 px-2"),

            # 🧾 Tipo de ingreso
            html.Div([
                html.Label("Tipo de Ingreso", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.Dropdown(
                    id="dash-tipo",
                    multi=True,
                    placeholder="Selecciona...",
                    options=[
                        {"label": "COMPRAS", "value": "Compras"},
                        {"label": "TRASLADOS", "value": "Traslados"},
                        {"label": "TERCEROS", "value": "Terceros"}
                    ],
                    style={
                        "fontSize": "13px",
                        "whiteSpace": "normal",
                        "wordWrap": "break-word",
                        "lineHeight": "1.3",
                        "minHeight": "45px"
                    },
                    className="w-full rounded-lg shadow-sm"
                )
            ], className="w-full md:w-1/5 px-2"),  # 👈 más angosto pero alineado visualmente

            # 🚚 Con / Sin transporte
            html.Div([
                html.Label("Transporte", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.Checklist(
                    id="dash-transporte",
                    options=[
                        {"label": "Con transporte", "value": 1},
                        {"label": "Sin transporte", "value": 2}
                    ],
                    value=[],  # 👈 Por defecto, ninguno seleccionado
                    className="text-slate-500 text-sm flex flex-col items-start space-y-1",
                    inputStyle={"marginRight": "6px"}
                )
            ], className="w-2/12 px-2 flex flex-col items-start justify-center"),


            # 🚛 Transportadora
            html.Div([
                html.Label("Transportadora", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.Dropdown(
                    id="dash-transportadora",
                    multi=True,
                    placeholder="Selecciona...",
                    style={
                        "fontSize": "13px",
                        "whiteSpace": "normal",
                        "wordWrap": "break-word",
                        "lineHeight": "1.3",
                        "minHeight": "45px"
                    },
                    className="w-full rounded-lg shadow-sm"
                )
            ], className="w-full md:w-1/3 px-2"),  # 👈 más ancha

            html.Div([
                html.Label("Material", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.Dropdown(
                    id="dash-material",
                    multi=True,
                    placeholder="Selecciona...",
                    style={
                        "fontSize": "13px",
                        "whiteSpace": "normal",
                        "wordWrap": "break-word",
                        "lineHeight": "1.3",
                        "minHeight": "45px"
                    },
                    className="w-full rounded-lg shadow-sm"
                )
            ], className="w-full md:w-1/4 px-2"),

            html.Div([
                html.Label("Top N", className="block text-sm font-medium text-slate-700 mb-1"),
                dcc.Input(
                    id="dash-topn",
                    type="number",
                    value=10,
                    min=1,
                    className="w-full border border-slate-300 rounded-lg shadow-sm px-3",
                    style={
                        "fontSize": "13px",
                        "height": "45px",      # misma altura que el dropdown de Material
                        "lineHeight": "1.3",
                        "textAlign": "center", # centrado visual del número
                        "color": "#334155",    # tono gris similar al texto de otros filtros
                        "backgroundColor": "white"
                    }
                )
            ], className="w-full md:w-1/12 px-2"),

        ], className="flex flex-wrap -mx-2 mb-8 bg-white p-4 rounded-xl shadow-md"),

        # 💎 KPIs con colores y diseño moderno
        html.Div([
            html.Div([
                html.P(id="kpi-toneladas", className="text-3xl font-bold text-green-900")
            ], className="bg-green-100 rounded-xl shadow p-4 text-center hover:shadow-lg transition"),

            html.Div([
                html.P(id="kpi-viajes", className="text-3xl font-bold text-blue-900")
            ], className="bg-blue-100 rounded-xl shadow p-4 text-center hover:shadow-lg transition"),

            html.Div([
                html.P(id="kpi-proveedores", className="text-3xl font-bold text-yellow-900")
            ], className="bg-yellow-100 rounded-xl shadow p-4 text-center hover:shadow-lg transition"),
        ], className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mb-10"),

        # 📈 Gráficos principales
        html.Div([
            html.Div(dcc.Graph(id="graf-rutas", className="rounded-xl shadow bg-white p-2"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-materiales", className="rounded-xl shadow bg-white p-2"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-origenes", className="rounded-xl shadow bg-white p-2"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-centros", className="rounded-xl shadow bg-white p-2"), className="w-full md:w-1/2 p-2"),
            html.Div(dcc.Graph(id="graf-vehiculos", className="rounded-xl shadow bg-white p-2"), className="w-full md:w-1/2 p-2")
        ], className="flex flex-wrap -mx-2"),

       # store para datos
        dcc.Store(
            id="store-df",
            data=pd.DataFrame().to_json(date_format="iso", orient="split")
        ),
        dcc.Store(
            id="store-df-full",  # <-- nuevo store
            data=pd.DataFrame().to_json(date_format="iso", orient="split")
        ),
        dcc.Interval(id="init-timer", interval=2000, n_intervals=0, max_intervals=1)
    ], className="container mx-auto p-4")
