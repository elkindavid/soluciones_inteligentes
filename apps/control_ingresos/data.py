# app/reporte/data.py
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from app.extensions import db

def parse_date(fecha_str):
    if fecha_str:
        try:
            return datetime.strptime(str(fecha_str), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None

def none_if_empty(value):
    return value if value not in (None, "", []) else None

def obtener_reporte(tipo=None, desde=None, hasta=None, centro=None, material=None, proveedor=None, almacen=None, origen=None):
    sql = """
        EXEC MESPesajeInteligenteDB.dbo.usp_GetInformeIngresos
            @tipo=:tipo,
            @fecha_inicio=:fecha_inicio,
            @fecha_fin=:fecha_fin,
            @centro=:centro,
            @material=:material,
            @proveedor=:proveedor,
            @almacen=:almacen,
            @origen=:origen
    """

    params = {
        "tipo": none_if_empty(tipo),
        "fecha_inicio": none_if_empty(desde),
        "fecha_fin": none_if_empty(hasta),
        "centro": none_if_empty(centro),
        "material": none_if_empty(material),
        "proveedor": none_if_empty(proveedor),
        "almacen": none_if_empty(almacen),
        "origen": none_if_empty(origen)
    }

    with db.engine.connect() as conn:
        result = conn.execute(text(sql), params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df
