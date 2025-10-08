# apps/dashboard_logistico/callbacks.py

from dash import Input, Output, State, html, dcc
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import calendar

from .data import fetch_logistico

def register_callbacks(app):
    # 1) Cargar datos y llenar store al cambiar filtros
    @app.callback(
        Output("store-df", "data"),
        Input("dash-fecha-desde", "date"),
        Input("dash-fecha-hasta", "date"),
        Input("dash-transportadora", "value"),
        Input("dash-material", "value"),
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
        Input("store-df", "data")
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
        Output("kpi-alertas", "children"),
        Input("store-df", "data")
    )
    def update_kpis(store_data):
        if not store_data:
            return (
                html.Div([html.H6("Toneladas"), html.H3("0 t")]),
                html.Div([html.H6("Viajes"), html.H3("0")]),
                html.Div([html.H6("Proveedores"), html.H3("0")]),
                html.Div([html.H6("Alertas"), html.H3("0")]),
            )
        df = pd.read_json(store_data, orient="split")
        toneladas = df["Toneladas"].astype(float).sum() if "Toneladas" in df.columns else 0
        viajes = df["NumViajes"].astype(float).sum() if "NumViajes" in df.columns else len(df)
        proveedores = int(df["Proveedor"].nunique()) if "Proveedor" in df.columns else 0
        alertas = int(df[df["Toneladas"].isnull() | (df["Toneladas"] == 0)].shape[0]) if "Toneladas" in df.columns else 0

        return (
            html.Div([html.H6("Toneladas"), html.H3(f"{toneladas:,.2f} t")]),
            html.Div([html.H6("Viajes"), html.H3(f"{viajes:,}")]),
            html.Div([html.H6("Proveedores"), html.H3(f"{proveedores:,}")]),
            html.Div([html.H6("Alertas"), html.H3(f"{alertas:,}")]),
        )

    # 4) Ranking rutas principales
    @app.callback(
        Output("graf-rutas", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_rutas(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Origen" not in df.columns or "CentroLogistico" not in df.columns or "Toneladas" not in df.columns:
            return {}
        df["ruta"] = df["Origen"].astype(str) + " → " + df["CentroLogistico"].astype(str)
        agg = df.groupby("ruta")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="ruta", orientation="h", title=f"Top {int(topn or 10)} Rutas por Toneladas")
        fig.update_layout(margin=dict(l=140))
        return fig

    # 5) Ranking materiales por volumen
    @app.callback(
        Output("graf-materiales", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_materiales(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Material" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = df.groupby("Material")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="Material", orientation="h", title=f"Top {int(topn or 10)} Materiales por Toneladas")
        fig.update_layout(margin=dict(l=140))
        return fig

    # 6) Ranking orígenes
    @app.callback(
        Output("graf-origenes", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_origenes(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Origen" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = df.groupby("Origen")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Toneladas", y="Origen", orientation="h", title=f"Top {int(topn or 10)} Orígenes por Toneladas")
        fig.update_layout(margin=dict(l=140))
        return fig

    # 7) Ranking centros logísticos (treemap)
    @app.callback(
        Output("graf-centros", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_centros(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "CentroLogistico" not in df.columns or "Toneladas" not in df.columns:
            return {}
        agg = df.groupby("CentroLogistico")["Toneladas"].sum().reset_index().sort_values("Toneladas", ascending=False).head(int(topn or 50))
        fig = px.treemap(agg, path=["CentroLogistico"], values="Toneladas", title="Volumen por Centro Logístico")
        return fig

    # 8) Calidad (scatter)
    @app.callback(
        Output("graf-calidad", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_calidad(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        kval = None
        for c in ["Calidad", "CalidadPromedio", "IndiceCalidad"]:
            if c in df.columns:
                kval = c
                break
        if kval is None:
            return {}
        agg = df.groupby("Origen").agg({kval: "mean", "Toneladas": "sum"}).reset_index()
        fig = px.scatter(agg, x=kval, y="Toneladas", hover_name="Origen", title="Calidad vs Toneladas por Origen")
        return fig

    # 9) Vehículos (conteo de viajes por placa)
    @app.callback(
        Output("graf-vehiculos", "figure"),
        Input("store-df", "data"),
        State("dash-topn", "value")
    )
    def update_vehiculos(store_data, topn):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Placa" not in df.columns:
            return {}
        agg = df.groupby("Placa").size().reset_index(name="Viajes").sort_values("Viajes", ascending=False).head(int(topn or 10))
        fig = px.bar(agg, x="Viajes", y="Placa", orientation="h", title=f"Top {int(topn or 10)} Vehículos por Viajes")
        fig.update_layout(margin=dict(l=140))
        return fig

    # 10) Alertas por desviación por placa (ejemplo)
    @app.callback(
        Output("tabla-alertas", "figure"),
        Input("store-df", "data")
    )
    def update_alertas(store_data):
        if not store_data:
            return {}
        df = pd.read_json(store_data, orient="split")
        if "Toneladas" in df.columns and "ToneladasEsperadas" in df.columns:
            df["desv_pct"] = (df["Toneladas"] - df["ToneladasEsperadas"]) / df["ToneladasEsperadas"].abs() * 100
            df_alert = df[df["ToneladasEsperadas"].notna() & (df["desv_pct"].abs() > 5)]
            if df_alert.empty:
                return {}
            fig = px.scatter(df_alert, x="Placa", y="desv_pct", size="Toneladas", hover_data=["NumTiquete","Proveedor"])
            fig.update_layout(title="Alertas: desviación % por Placa")
            return fig
        return {}

