# apps/dashboard_logistico/data.py

import pandas as pd
from sqlalchemy import text
from app.extensions import db

def fetch_logistico(tipo=None, desde=None, hasta=None, pedido=None, origen=None, destino=None, transportadora=None, material=None, placa=None, proveedor_mat=None, con_transporte=None):
    """
    Llama al stored procedure usp_GetInformeLogistico y devuelve un DataFrame.
    Los parámetros pueden ser None o strings con listas separadas por comas.
    """
    sql = """
    EXEC MESPesajeInteligenteDB.dbo.usp_GetInformeLogisticoDash
    @tipo=:tipo,
    @fecha_inicio=:fecha_inicio,
    @fecha_fin=:fecha_fin,
    @pedido=:pedido,
    @origen=:origen,
    @destino=:destino,
    @transportadora=:transportadora,
    @material=:material,
    @placa=:placa,
    @proveedor_mat=:proveedor_mat,
    @con_transporte=:con_transporte
    """


    params = {
        "tipo": tipo,
        "fecha_inicio": desde,
        "fecha_fin": hasta,
        "pedido": pedido,
        "origen": origen,
        "destino": destino,
        "transportadora": transportadora,
        "material": material,
        "placa": placa,
        "proveedor_mat": proveedor_mat,
        "con_transporte": con_transporte,
    }

    with db.engine.connect().execution_options(stream_results=True) as conn:
        result = conn.execute(text(sql), params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    # limpiar nombres de columnas (quitar espacios)
    df.columns = [c.strip() for c in df.columns]
    return df

