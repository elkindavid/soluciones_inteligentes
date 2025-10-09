# apps/dashboard_logistico/callbacks.py

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
from datetime import datetime
import calendar

from .data import fetch_logistico

def register_callbacks(app):

    # 1) Cargar datos completos según rango de fecha
    @app.callback(
        Output("store-df-full", "data"),
        Input("dash-fecha-rango", "start_date"),
        Input("dash-fecha-rango", "end_date"),
        prevent_initial_call=False
    )
    def load_data(fecha_desde, fecha_hasta):
        if not fecha_desde or not fecha_hasta:
            hoy = datetime.today().date()
            primer_dia = hoy.replace(day=1)
            ultimo_dia = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
            fecha_desde = primer_dia.isoformat()
            fecha_hasta = ultimo_dia.isoformat()

        df = fetch_logistico(
            tipo=None,
            desde=fecha_desde,
            hasta=fecha_hasta,
            transportadora=None,
            material=None,
            placa=None,
            proveedor_mat=None,
            origen=None,
            destino=None,
            pedido=None
        )

        if df is None or df.empty:
            return pd.DataFrame().to_json(date_format="iso", orient="split")
        return df.to_json(date_format="iso", orient="split")

    # 2) Actualizar opciones y valores de los dropdowns
    @app.callback(
        Output("dash-transportadora", "options"),
        Output("dash-material", "options"),
        Output("dash-transportadora", "value"),
        Output("dash-material", "value"),
        Input("store-df-full", "data"),
        State("dash-transportadora", "value"),
        State("dash-material", "value")
    )
    def update_options(df_full_json, sel_transportadora, sel_material):
        if not df_full_json:
            raise PreventUpdate
        df = pd.read_json(df_full_json, orient="split")

        transportadoras = sorted(df["NombreEmpresaTpte"].dropna().unique())
        materiales = sorted(df["Material"].dropna().unique())

        sel_transportadora = [v for v in (sel_transportadora or []) if v in transportadoras]
        sel_material = [v for v in (sel_material or []) if v in materiales]

        options_transportadora = [{"label": t, "value": t} for t in transportadoras]
        options_material = [{"label": m, "value": m} for m in materiales]

        return options_transportadora, options_material, sel_transportadora, sel_material

    # 3) Filtrar datos según selección de dropdowns
    @app.callback(
        Output("store-df", "data"),
        Input("store-df-full", "data"),
        Input("dash-transportadora", "value"),
        Input("dash-material", "value")
    )
    def filter_data(df_full_json, transportadoras, materiales):
        if not df_full_json:
            raise PreventUpdate
        df = pd.read_json(df_full_json, orient="split")

        if transportadoras:
            df = df[df["NombreEmpresaTpte"].isin(transportadoras)]
        if materiales:
            df = df[df["Material"].isin(materiales)]
        return df.to_json(date_format="iso", orient="split")

    # 4) KPIs
    @app.callback(
        Output("kpi-toneladas", "children"),
        Output("kpi-viajes", "children"),
        Output("kpi-proveedores", "children"),
        Input("store-df", "data"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_kpis(store_data, n_intervals):
        if not store_data or n_intervals == 0:
            return (
                html.Div([html.H6("Toneladas"), html.H3("0 t")]),
                html.Div([html.H6("Viajes"), html.H3("0")]),
                html.Div([html.H6("Proveedores"), html.H3("0")]),
            )

        df = pd.read_json(store_data, orient="split")
        toneladas = df["Toneladas"].astype(float).sum() if "Toneladas" in df.columns else 0
        viajes = df["NumViajes"].astype(float).sum() if "NumViajes" in df.columns else len(df)
        proveedores = int(df["Proveedor"].nunique()) if "Proveedor" in df.columns else 0

        # 🔹 Formatos personalizados
        toneladas_fmt = f"{toneladas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        viajes_fmt = f"{viajes:,.0f}".replace(",", ".")  # solo separador de miles

        return (
            html.Div([html.H6("Toneladas"), html.H3(f"{toneladas_fmt} t")]),
            html.Div([html.H6("Viajes"), html.H3(viajes_fmt)]),
            html.Div([html.H6("Proveedores"), html.H3(f"{proveedores:,}".replace(",", "."))])
        )


    # 5) Ranking rutas principales
    @app.callback(
        Output("graf-rutas", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_rutas(store_data, topn, n_intervals):
        if not store_data or n_intervals == 0:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Origen" not in df.columns or "CentroLogistico" not in df.columns or "Toneladas" not in df.columns:
            return {}
        df["Ruta"] = df["Origen"].astype(str) + " → " + df["CentroLogistico"].astype(str)
        agg = df.groupby("Ruta")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="Ruta", orientation="h",
                     title=f"Top {int(topn or 10)} Rutas por Toneladas",
                     text="Toneladas", color="Toneladas", color_continuous_scale="Blues")
        fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
        fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=140),
                          xaxis=dict(showgrid=True, gridcolor="lightgrey"),
                          yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                          title=dict(font=dict(size=25)))
        fig.update_yaxes(categoryorder="total ascending")
        return fig

    # 6) Ranking materiales por volumen
    @app.callback(
        Output("graf-materiales", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_materiales(store_data, topn, n_intervals):
        if not store_data or n_intervals == 0:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Material" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = df.groupby("Material")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="Material", orientation="h",
                     title=f"Top {int(topn or 10)} Materiales por Toneladas",
                     text="Toneladas", color="Toneladas", color_continuous_scale="Blues")
        fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
        fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=140),
                          xaxis=dict(showgrid=True, gridcolor="lightgrey"),
                          yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                          title=dict(font=dict(size=25)))
        fig.update_yaxes(categoryorder="total ascending")
        return fig

    # 7) Ranking orígenes
    @app.callback(
        Output("graf-origenes", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_origenes(store_data, topn, n_intervals):
        if not store_data or n_intervals == 0:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Origen" not in df.columns or "Toneladas" not in df.columns:
            return {}
        if "CiudadOrigen" in df.columns:
            df["Origen"] = df["Origen"].astype(str) + " [" + df["CiudadOrigen"].astype(str) + "]"
        agg = df.groupby("Origen")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="Origen", orientation="h",
                     title=f"Top {int(topn or 10)} Orígenes por Toneladas",
                     text="Toneladas", color="Toneladas", color_continuous_scale="Blues")
        fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
        fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=140),
                          xaxis=dict(showgrid=True, gridcolor="lightgrey"),
                          yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                          title=dict(font=dict(size=25)))
        fig.update_yaxes(categoryorder="total ascending")
        return fig

    # 8) Ranking centros logísticos
    @app.callback(
        Output("graf-centros", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_centros(store_data, topn, n_intervals):
        if not store_data or n_intervals == 0:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "CentroLogistico" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = df.groupby("CentroLogistico")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 50))
        fig = px.pie(agg, names="CentroLogistico", values="Toneladas",
                     hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel,
                     title="Ingresos por Centro Logístico")
        fig.update_traces(texttemplate="%{value:,.0f} t", textinfo="value",
                          textfont=dict(size=12, color="black"),
                          hovertemplate="<b>%{label}</b><br>Toneladas: %{value:,.0f}<extra></extra>")
        fig.update_layout(margin=dict(t=50, l=20, r=20, b=20),
                          showlegend=True, title=dict(font=dict(size=25)))
        return fig

    # 9) Vehículos
    @app.callback(
        Output("graf-vehiculos", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        Input("init-timer", "n_intervals"),  # 👈 nuevo input
        prevent_initial_call=False
    )
    def update_vehiculos(store_data, topn, n_intervals):
        if not store_data or n_intervals == 0:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Placa" not in df.columns:
            return {}
        agg = df.groupby("Placa").agg(Viajes=("Placa", "count"), Toneladas=("Toneladas", "sum")).reset_index()
        agg = agg.sort_values("Viajes", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Viajes", y="Placa", orientation="h",
                     title=f"Top {int(topn or 10)} Vehículos por Viajes",
                     text="Viajes", color="Viajes", color_continuous_scale="Blues",
                     hover_data={"Toneladas": ":,.0f"})
        fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
        fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=140),
                          xaxis=dict(showgrid=True, gridcolor="lightgrey"),
                          yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                          title=dict(font=dict(size=25)))
        fig.update_yaxes(categoryorder="total ascending")
        return fig
