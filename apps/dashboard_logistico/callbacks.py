# apps/dashboard_logistico/callbacks.py

from dash import Input, Output, html
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
from datetime import datetime
import calendar

from .data import fetch_logistico

def register_callbacks(app):
    # 1) Cargar datos y llenar store al cambiar filtros
    @app.callback(
        Output("store-df", "data"),
        Input("dash-fecha-rango", "start_date"),
        Input("dash-fecha-rango", "end_date"),
        Input("dash-transportadora", "value"),
        Input("dash-material", "value"),
        prevent_initial_call=False
    )
    def load_data(fecha_desde, fecha_hasta, transportadoras, materiales):
        if not fecha_desde or not fecha_hasta:
            hoy = datetime.today().date()
            primer_dia = hoy.replace(day=1)
            ultimo_dia = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
            fecha_desde = primer_dia.isoformat()
            fecha_hasta = ultimo_dia.isoformat()

        t_str = ",".join(transportadoras) if transportadoras else None
        m_str = ",".join(materiales) if materiales else None

        df = fetch_logistico(
            tipo=None,
            desde=fecha_desde,
            hasta=fecha_hasta,
            transportadora=t_str,
            material=m_str, 
            placa=None,
            proveedor_mat=None,
            origen=None,
            destino=None,
            pedido=None,
        )

        if df is None or df.empty:
            return pd.DataFrame().to_json(date_format="iso", orient="split")
        return df.to_json(date_format="iso", orient="split")

    # 2) Llenar dropdowns dependientes
    @app.callback(
        Output("dash-transportadora", "options"),
        Output("dash-material", "options"),
        Input("store-df", "data"),
        prevent_initial_call=False
    )
    def populate_dropdowns(store_data):
        if not store_data:
            raise PreventUpdate
        df = pd.read_json(store_data, orient="split")
        transportadoras = sorted(df["NombreEmpresaTpte"].dropna().unique()) if "NombreEmpresaTpte" in df.columns else []
        materiales = sorted(df["Material"].dropna().unique()) if "Material" in df.columns else []
        return [{"label": t, "value": t} for t in transportadoras], [{"label": m, "value": m} for m in materiales]

    # 3) KPIs
    @app.callback(
        Output("kpi-toneladas", "children"),
        Output("kpi-viajes", "children"),
        Output("kpi-proveedores", "children"),
        Input("store-df", "data"),
        prevent_initial_call=False
    )
    def update_kpis(store_data):
        if not store_data:
            return (
                html.Div([html.H6("Toneladas"), html.H3("0 t")]),
                html.Div([html.H6("Viajes"), html.H3("0")]),
                html.Div([html.H6("Proveedores"), html.H3("0")]),
            )
        df = pd.read_json(store_data, orient="split")
        toneladas = df["Toneladas"].astype(float).sum() if "Toneladas" in df.columns else 0
        viajes = df["NumViajes"].astype(float).sum() if "NumViajes" in df.columns else len(df)
        proveedores = int(df["Proveedor"].nunique()) if "Proveedor" in df.columns else 0

        return (
            html.Div([html.H6("Toneladas"), html.H3(f"{toneladas:,.2f} t")]),
            html.Div([html.H6("Viajes"), html.H3(f"{viajes:,}")]),
            html.Div([html.H6("Proveedores"), html.H3(f"{proveedores:,}")])
        )

    # 4) Ranking rutas principales
    @app.callback(
        Output("graf-rutas", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        prevent_initial_call=False
    )
    def update_rutas(store_data, topn):
        if not store_data:
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

    # 5) Ranking materiales por volumen
    @app.callback(
        Output("graf-materiales", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        prevent_initial_call=False
    )
    def update_materiales(store_data, topn):
        if not store_data:
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

    # 6) Ranking orígenes
    @app.callback(
        Output("graf-origenes", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        prevent_initial_call=False
    )
    def update_origenes(store_data, topn):
        if not store_data:
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

    # 7) Ranking centros logísticos
    @app.callback(
        Output("graf-centros", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        prevent_initial_call=False
    )
    def update_centros(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "CentroLogistico" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = (df.groupby("CentroLogistico")["Toneladas"]
                 .sum().reset_index()
                 .sort_values("Toneladas", ascending=False)
                 .head(int(topn or 50)))
        fig = px.pie(agg, names="CentroLogistico", values="Toneladas",
                     hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel,
                     title="Ingresos por Centro Logístico")
        fig.update_traces(texttemplate="%{value:,.0f} t", textinfo="value",
                          textfont=dict(size=12, color="black"),
                          hovertemplate="<b>%{label}</b><br>Toneladas: %{value:,.0f}<extra></extra>")
        fig.update_layout(margin=dict(t=50, l=20, r=20, b=20),
                          showlegend=True, title=dict(font=dict(size=25)))
        return fig

    # 8) Vehículos
    @app.callback(
        Output("graf-vehiculos", "figure"),
        Input("store-df", "data"),
        Input("dash-topn", "value"),
        prevent_initial_call=False
    )
    def update_vehiculos(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Placa" not in df.columns:
            return {}
        agg = (df.groupby("Placa")
                 .agg(Viajes=("Placa", "count"), Toneladas=("Toneladas", "sum"))
                 .reset_index()
                 .sort_values("Viajes", ascending=False)
                 .head(int(topn or 10)))
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
