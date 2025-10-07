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

def obtener_reporte(tipo=None, desde=None, hasta=None, pedido=None, origen=None, destino=None, transportadora=None, placa=None, proveedor_mat=None):
    sql = """
        EXEC MESPesajeInteligenteDB.dbo.usp_GetInformeLogistico
            @tipo=:tipo,
            @fecha_inicio=:fecha_inicio,
            @fecha_fin=:fecha_fin,
            @pedido=:pedido,
            @origen=:origen,
            @destino=:destino,
            @transportadora=:transportadora,
            @placa=:placa,
            @proveedor_mat=:proveedor_mat
    
    """

    params = {
        "tipo": none_if_empty(tipo),
        "fecha_inicio": none_if_empty(desde),
        "fecha_fin": none_if_empty(hasta),
        "pedido": none_if_empty(pedido),
        "origen": none_if_empty(origen),
        "destino": none_if_empty(destino),
        "transportadora": none_if_empty(transportadora),
        "placa": none_if_empty(placa),
        "proveedor_mat": none_if_empty(proveedor_mat)
    }

    with db.engine.connect() as conn:
        result = conn.execute(text(sql), params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df
