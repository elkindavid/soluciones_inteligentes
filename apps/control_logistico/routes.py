# routes.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from .data import obtener_reporte, parse_date
import pandas as pd
from sqlalchemy import text
from app.extensions import db

informes_bp = Blueprint(
    "informes", __name__,
    url_prefix="/reporte",
    template_folder="templates",
    static_folder="static"   
)

@informes_bp.route("/")
@login_required
def index():
    df = obtener_reporte()
    pedidos = sorted(df['NumeroPedido'].dropna().unique()) if 'NumeroPedido' in df.columns else []
    origenes = sorted(df['Origen'].dropna().unique()) if 'Origen' in df.columns else []
    destinos = sorted(df['CentroLogistico'].dropna().unique()) if 'CentroLogistico' in df.columns else []
    transportadoras = sorted(df['NombreEmpresaTpte'].dropna().unique()) if 'NombreEmpresaTpte' in df.columns else []
    placas = sorted(df['Placa'].dropna().unique()) if 'Placa' in df.columns else []
    proveedores = sorted(df['Proveedor'].dropna().unique()) if 'Proveedor' in df.columns else []
    
    return render_template(
        "reporte/index.html",
        pedidos=pedidos,
        origenes=origenes,
        destinos=destinos,
        transportadoras=transportadoras,
        placas=placas,
        proveedores=proveedores,
    )

def _get_list_param(name):
    vals = request.args.getlist(name)
    vals = [v.strip() for v in vals if v and v.strip()]
    return ",".join(vals) if vals else None


@informes_bp.route("/data")
def get_data():
    tipo = request.args.get("tipo") or None
    fecha_inicio = request.args.get("desde") or None
    fecha_fin = request.args.get("hasta") or None
    pedido = request.args.get("pedido") or None
    origen = request.args.get("origen") or None
    destino = request.args.get("destino") or None
    transportadora = request.args.get("transportadora") or None
    placa = request.args.get("placa") or None
    proveedor_mat = request.args.get("proveedor_mat") or None

    sql = text("""
        EXEC MESPesajeInteligenteDB.dbo.usp_GetInformeLogistico
            @tipo = :tipo,
            @fecha_inicio = :fecha_inicio,
            @fecha_fin = :fecha_fin,
            @pedido = :pedido,
            @origen = :origen,
            @destino = :destino,
            @transportadora = :transportadora,
            @placa = :placa,
            @proveedor_mat = :proveedor_mat
            
    """)

    result = db.session.execute(sql, {
        "tipo": tipo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "pedido": pedido,
        "origen": origen,
        "destino": destino,
        "transportadora": transportadora,
        "placa": placa,
        "proveedor_mat": proveedor_mat,
        
    })

    rows = [dict(r) for r in result.mappings()]

    # 🔒 Convertir NumTiquete a string para conservar ceros
    for row in rows:
        if "NumTiquete" in row and row["NumTiquete"] is not None:
            row["NumTiquete"] = str(row["NumTiquete"])

    return jsonify(rows)

@informes_bp.route("/filtros", methods=["GET"])
@login_required
def filtros():
    tipo = _get_list_param("tipo")
    desde = parse_date(request.args.get("desde"))
    hasta = parse_date(request.args.get("hasta"))
    pedido = _get_list_param("pedido")
    origen = _get_list_param("origen")
    destino = _get_list_param("destino")
    transportadora = _get_list_param("transportadora")
    placa = _get_list_param("placa")
    proveedor_mat = _get_list_param("proveedor_mat")

    df = obtener_reporte(tipo, desde, hasta, pedido, origen, destino, transportadora, placa, proveedor_mat)

    return jsonify({
        "pedidos": sorted(df['NumeroPedido'].dropna().unique()) if 'NumeroPedido' in df.columns else [],
        "origenes": sorted(df['Origen'].dropna().unique()) if 'Origen' in df.columns else [],
        "destinos": sorted(df['CentroLogistico'].dropna().unique()) if 'CentroLogistico' in df.columns else [],
        "transportadoras": sorted(df['NombreEmpresaTpte'].dropna().unique()) if 'NombreEmpresaTpte' in df.columns else [],
        "placas": sorted(df['Placa'].dropna().unique()) if 'Placa' in df.columns else [],
        "proveedores": sorted(df['Proveedor'].dropna().unique()) if 'Proveedor' in df.columns else []
    })
