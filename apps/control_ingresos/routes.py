# routes.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from .data import obtener_reporte, parse_date
import pandas as pd
from sqlalchemy import text
from app.extensions import db

repingresos_bp = Blueprint(
    "ingresos", __name__,
    url_prefix="/control_ingreso",
    template_folder="templates",
    static_folder="static"   
)

@repingresos_bp.route("/")
@login_required
def index():
    df = obtener_reporte()
    centros = sorted(df['CentroLogistico'].dropna().unique()) if 'CentroLogistico' in df.columns else []
    materiales = sorted(df['Material'].dropna().unique()) if 'Material' in df.columns else []
    proveedores = sorted(df['Proveedor'].dropna().unique()) if 'Proveedor' in df.columns else []
    almacenes = sorted(df['Almacen'].dropna().unique()) if 'Almacen' in df.columns else []
    origenes = sorted(df['Origen'].dropna().unique()) if 'Origen' in df.columns else []

    return render_template(
        "control_ingreso/index.html",
        centros=centros,
        materiales=materiales,
        proveedores=proveedores,
        almacenes=almacenes,
        origenes=origenes
    )

def _get_list_param(name):
    vals = request.args.getlist(name)
    vals = [v.strip() for v in vals if v and v.strip()]
    return ",".join(vals) if vals else None


@repingresos_bp.route("/data")
def get_data():
    tipo = request.args.get("tipo") or None
    fecha_inicio = request.args.get("desde") or None
    fecha_fin = request.args.get("hasta") or None
    centro = request.args.get("centro") or None
    material = request.args.get("material") or None
    proveedor = request.args.get("proveedor") or None
    almacen = request.args.get("almacen") or None
    origen = request.args.get("origen") or None

    sql = text("""
        EXEC MESPesajeInteligenteDB.dbo.usp_GetInformeIngresos
            @tipo = :tipo,
            @fecha_inicio = :fecha_inicio,
            @fecha_fin = :fecha_fin,
            @centro = :centro,
            @material = :material,
            @proveedor = :proveedor,
            @almacen = :almacen,
            @origen = :origen
    """)

    result = db.session.execute(sql, {
        "tipo": tipo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "centro": centro,
        "material": material,
        "proveedor": proveedor,
        "almacen": almacen,
        "origen": origen
    })

    rows = [dict(r) for r in result.mappings()]
    return jsonify(rows)

@repingresos_bp.route("/filtros", methods=["GET"])
@login_required
def filtros():
    tipo = _get_list_param("tipo")
    desde = parse_date(request.args.get("desde"))
    hasta = parse_date(request.args.get("hasta"))
    centro = _get_list_param("centro")
    material = _get_list_param("material")
    proveedor = _get_list_param("proveedor")
    almacen = _get_list_param("almacen")
    origen = _get_list_param("origen")

    df = obtener_reporte(tipo, desde, hasta, centro, material, proveedor, almacen, origen)

    return jsonify({
        "centros": sorted(df['CentroLogistico'].dropna().unique()) if 'CentroLogistico' in df.columns else [],
        "materiales": sorted(df['Material'].dropna().unique()) if 'Material' in df.columns else [],
        "proveedores": sorted(df['Proveedor'].dropna().unique()) if 'Proveedor' in df.columns else [],
        "almacenes": sorted(df['Almacen'].dropna().unique()) if 'Almacen' in df.columns else [],
        "origenes": sorted(df['Origen'].dropna().unique()) if 'Origen' in df.columns else []
    })
