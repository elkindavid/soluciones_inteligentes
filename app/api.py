from flask import Blueprint, request, jsonify, send_file, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy import text
from .extensions import db
from .models import RegistroDestajo
from datetime import datetime, date
from .models import GHDestajo, GHEmpleado
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter
from .auth import admin_required_api
from tempfile import NamedTemporaryFile

api_bp = Blueprint("api", __name__)

@api_bp.get("/employees")
@login_required
def employees():
    q = request.args.get("q", "").strip()
    planta = request.args.get("planta", "").strip()

    where = ["estado = 'ACTIVO'"]
    params = {}

    if q:
        where.append("""(
            LOWER(LTRIM(RTRIM(nombreCompleto))) LIKE LOWER(:q) OR
            LOWER(LTRIM(RTRIM(apellidoCompleto))) LIKE LOWER(:q) OR
            LOWER(LTRIM(RTRIM(nombreCompleto)) + ' ' + LTRIM(RTRIM(apellidoCompleto))) LIKE LOWER(:q) OR
            CAST(numeroDocumento AS NVARCHAR(50)) LIKE :q
        )""")
        params['q'] = f'%{q}%'

    # si planta fue enviada y no es vacío ni 'TODAS', filtramos por agrupador4
    if planta and planta.upper() != 'TODAS':
        where.append("agrupador4 LIKE :pplanta")
        params['pplanta'] = f'%{planta}%'

    sql = text(f"""
        SELECT nombreCompleto, apellidoCompleto, numeroDocumento, agrupador4
        FROM GH_Empleados
        WHERE {' AND '.join(where)}
        ORDER BY nombreCompleto
    """)
    rows = db.session.execute(sql, params).mappings().all()

    return jsonify([
        {
            'nombre': f"{r['nombreCompleto']} {r['apellidoCompleto']}".strip(),
            'documento': str(r['numeroDocumento']),
            'agrupador4': r.get('agrupador4')
        }
        for r in rows
    ])


@api_bp.get("/destajos")
@login_required
def destajos_catalog():
    q = request.args.get("q", "").strip()
    planta = request.args.get("planta", "").strip()
    where = ["1=1"]
    params = {}

    if q:
        where.append("Concepto LIKE :q")
        params['q'] = f'%{q}%'

    # Si planta no se envía o es vacío → no filtrar 
    # Si planta == 'TODAS' → incluir todos
    if planta and planta.upper() != 'TODAS':
        # traemos filas donde GH_Destajos.Planta = planta OR Planta = 'TODAS'
        where.append("(Planta = :planta OR Planta = 'TODAS')")
        params['planta'] = planta

    sql = text(f"""
        SELECT Id, Planta, Concepto, Valor
        FROM GH_Destajos
        WHERE {' AND '.join(where)}
        ORDER BY Concepto
    """)
    rows = db.session.execute(sql, params).mappings().all()

    return jsonify([
        {
            'id': int(r['Id']),
            'planta': r['Planta'],
            'concepto': r['Concepto'],
            'valor': float(r['Valor'] or 0)
        }
        for r in rows
    ])

@api_bp.post("/registros")
@login_required
def crear_registro():
    data = request.get_json(force=True)
    reg = RegistroDestajo(
        empleado_documento=data['empleado_documento'],
        empleado_nombre=data['empleado_nombre'],
        destajo_id=int(data['destajo_id']),
        cantidad=float(data['cantidad']),
        fecha=datetime.fromisoformat(data['fecha']).date(),
        usuario_id=current_user.id
    )
    db.session.add(reg)
    db.session.commit()
    return jsonify({'ok': True, 'id': reg.id})

@api_bp.put("/registros/<int:rid>")
@login_required
def editar_registro(rid):
    reg = db.session.get(RegistroDestajo, rid)
    if not reg:
        return jsonify({'error': 'not found'}), 404

    # 🔒 solo permitir si es el creador o admin
    if reg.usuario_id != current_user.id and not getattr(current_user, "is_admin", False):
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(force=True)

    for k in ['empleado_documento', 'empleado_nombre']:
        if k in data:
            setattr(reg, k, data[k])
    if 'destajo_id' in data:
        reg.destajo_id = int(data['destajo_id'])
    if 'cantidad' in data:
        reg.cantidad = float(data['cantidad'])
    if 'fecha' in data:
        reg.fecha = datetime.fromisoformat(data['fecha']).date()

    db.session.commit()
    return jsonify({'ok': True})

@api_bp.delete("/registros/<int:rid>")
@login_required
@admin_required_api   # ⬅️ aquí
def eliminar_registro(rid):
    breakpoint()
    reg = db.session.get(RegistroDestajo, rid)
    if not reg: return jsonify({'error':'not found'}), 404
    db.session.delete(reg)
    db.session.commit()
    return jsonify({'ok': True})

def safe_iso(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)

@api_bp.get("/registros")
@login_required
def listar_registros():
    doc = request.args.get('documento')
    f1 = request.args.get('desde')
    f2 = request.args.get('hasta')
    planta = request.args.get('planta')  # 👈 nuevo

    sql = """
        SELECT r.id, r.empleado_documento, r.empleado_nombre, r.destajo_id, r.cantidad,
               r.fecha, r.fecha_registro, r.usuario_id, d.Concepto
        FROM registros_destajo r
        LEFT JOIN GH_Destajos d ON d.Id = r.destajo_id
        WHERE 1=1
    """
    params = {}
    if doc:
        sql += " AND r.empleado_documento = :doc"
        params['doc'] = doc
    if f1:
        sql += " AND r.fecha >= :f1"
        params['f1'] = date.fromisoformat(f1)
    if f2:
        sql += " AND r.fecha <= :f2"
        params['f2'] = date.fromisoformat(f2)
    if planta:  # 👈 nuevo filtro
        sql += " AND d.Planta = :planta"
        params['planta'] = planta

    sql += " ORDER BY r.fecha DESC"
    rows = db.session.execute(text(sql), params).mappings().all()

    return jsonify([{
        'id': int(r['id']),
        'empleado_documento': r['empleado_documento'],
        'empleado_nombre': r['empleado_nombre'],
        'destajo_id': int(r['destajo_id']),
        'destajo': r['Concepto'],
        'cantidad': float(r['cantidad']),
        'fecha': safe_iso(r['fecha']),
        'fecha_registro': safe_iso(r['fecha_registro']),
        'usuario_id': int(r['usuario_id'])
    } for r in rows])

@api_bp.post("/sync")
@login_required
def sync_batch():
    items = request.get_json(force=True)
    created = []
    for i in items:
        reg = RegistroDestajo(
            empleado_documento=i['empleado_documento'],
            empleado_nombre=i['empleado_nombre'],
            destajo_id = int(i['destajo_id']) if i.get('destajo_id') else -1,
            cantidad=float(i['cantidad']),
            fecha=datetime.fromisoformat(i['fecha']).date(),
            usuario_id=current_user.id
        )
        db.session.add(reg)
        db.session.flush()
        created.append(reg.id)
    db.session.commit()
    return jsonify({'ok': True, 'ids': created})

# GET /api/empleados
@api_bp.route("/empleados", methods=["GET"])
def get_empleados():
    try:
        empleados = GHEmpleado.query.all()
        empleados_data = [e.to_dict() for e in empleados]  # asegúrate que el modelo tenga to_dict()
        return jsonify(empleados_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GET /api/mdestajos
@api_bp.route("/mdestajos", methods=["GET"])
def get_destajos():
    try:
        planta = request.args.get('planta', '').strip()
        q = request.args.get('q', '').strip()

        query = GHDestajo.query
        if q:
            query = query.filter(GHDestajo.Concepto.ilike(f'%{q}%'))
        if planta and planta.upper() != 'TODAS':
            query = query.filter((GHDestajo.Planta == planta) | (GHDestajo.Planta == 'TODAS'))

        destajos = query.order_by(GHDestajo.Concepto).all()
        destajos_data = [d.to_dict() for d in destajos]
        return jsonify(destajos_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import send_file
from tempfile import NamedTemporaryFile
import pandas as pd

from io import BytesIO
from flask import send_file
import pandas as pd

@api_bp.get("/liquidacion/excel")
@login_required
def liquidacion_excel():
    doc = request.args.get('documento')
    f1 = request.args.get('desde')
    f2 = request.args.get('hasta')

    params = {}
    sql = """
    SELECT
      CASE 
            WHEN LEFT(e.tipoIdentificacion,11)='Cédula Ciud' THEN 'C'
            WHEN LEFT(e.tipoIdentificacion,11)='Cédula de E' THEN 'E'
            WHEN LEFT(e.tipoIdentificacion,11)='Permiso Por' THEN 'PT'
            ELSE e.tipoIdentificacion END AS TipoDocumento,
      r.empleado_documento AS NumeroDocumento,
      d.Concepto,
      e.centroCosto AS AreaFuncional,
      r.cantidad AS Cantidad,
      ISNULL(d.Valor,0) AS Valor
    FROM registros_destajo r
    JOIN GH_Empleados e ON e.numeroDocumento = r.empleado_documento
    JOIN GH_Destajos d ON d.Id = r.destajo_id
    WHERE 1=1
    """

    if f1:
        sql += " AND r.fecha >= :f1"
        params['f1'] = date.fromisoformat(f1)
    if f2:
        sql += " AND r.fecha <= :f2"
        params['f2'] = date.fromisoformat(f2)
    if doc:
        sql += " AND r.empleado_documento = :doc"
        params['doc'] = doc

    rows = db.session.execute(text(sql), params).mappings().all()
    df = pd.DataFrame(rows)

    cols = [
        "TipoRegistro","TipoDocumento","NumeroDocumento","Concepto","TipoNovedad","TipoReporte",
        "ValorTotal","IncluyePago","SumaResta","FechaInicial","CantidadDias",
        "TipoIncapacidad","Diagnostico","NumeroIncapacidad","FechaRetiro","MotivoRetiro",
        "AreaFuncional","RangoDiaInicial","RangoHoraInicial","RangoHoraFinal","NumeroDias",
        "Cantidad","NumeroHoras","Indemnizacion","FechaNovedad","PagoTotal",
        "NaturalezaIncapacidad","FechaInicialEPS","Proyecto","FechaRetiroReal","Gobierno1","Gobierno2",
        "FechaIniIncPro","TipoDocEntidad","NumDocEntidad","TipoServicioEntidad",
        "IncapacidadDiasHab","Observaciones","Docentes"
    ]

    if df.empty:
        df_out = pd.DataFrame(columns=cols)
    else:
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)

        SMV = current_app.config.get('AAA', 47450)

        df_group = df.groupby(
            ['TipoDocumento','NumeroDocumento','Concepto','AreaFuncional'],
            as_index=False
        ).agg({'Cantidad':'sum','Valor':'mean'})

        df_validos = df[~df['Concepto'].str.contains('DESCANSO|JORNAL', case=False, regex=True)].copy()
        df_validos['vxq'] = df_validos['Valor']*df_validos['Cantidad']
        ponderado = df_validos.groupby('NumeroDocumento').agg(
            total_val=('vxq','sum'), conteo=('vxq','count')
        )
        ponderado['PromPond'] = ponderado['total_val']/ponderado['conteo']
        ponderado['PromPond'] = ponderado['PromPond'].apply(lambda x: max(x,SMV))
        prom_map = ponderado['PromPond'].to_dict()

        def calc_valor_total(row):
            concepto = (row.get('Concepto') or '').upper()
            qty = float(row.get('Cantidad',0))
            numdoc = row.get('NumeroDocumento')
            if 'JORNAL FESTIVO' in concepto:
                return SMV * 1.8 * qty
            if 'JORNAL' in concepto:
                return SMV * qty
            if 'DESCANSO' in concepto:
                prom = prom_map.get(numdoc, SMV)
                return prom * qty
            return ""

        df_group['ValorTotal'] = df_group.apply(calc_valor_total, axis=1)
        df_group['TipoNovedad'] = df_group['Concepto'].str.contains(
            'DESCANSO|JORNAL', case=False, regex=True).map(lambda x: 4 if x else 3)
        df_group['TipoRegistro'] = 1
        df_group['TipoReporte'] = 5
        df_group['FechaNovedad'] = f2 if f2 else ""
        df_group['IncluyePago'] = df_group['TipoNovedad'].apply(lambda x: 'Y' if x == 4 else '')
        df_group['SumaResta']   = df_group['TipoNovedad'].apply(lambda x: 1 if x == 4 else '')

        for c in ["FechaInicial","CantidadDias","TipoIncapacidad","Diagnostico","NumeroIncapacidad",
                  "FechaRetiro","MotivoRetiro","RangoDiaInicial","RangoHoraInicial","RangoHoraFinal",
                  "NumeroDias","NumeroHoras","Indemnizacion","PagoTotal","NaturalezaIncapacidad",
                  "FechaInicialEPS","Proyecto","FechaRetiroReal","Gobierno1","Gobierno2",
                  "FechaIniIncPro","TipoDocEntidad","NumDocEntidad","TipoServicioEntidad",
                  "IncapacidadDiasHab","Observaciones","Docentes"]:
            df_group[c] = ""

        df_out = df_group[cols]

    # --- Guardar en memoria como .xlsx ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_out.to_excel(writer, index=False, header=False, sheet_name="Liquidacion")
    output.seek(0)

    return send_file(
        output,
        download_name="liquidacion.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@api_bp.get("/plantas")
@login_required
def plantas():
    sql = text("""
        SELECT DISTINCT Planta
        FROM GH_Plantas
        WHERE Planta IS NOT NULL AND LTRIM(RTRIM(Planta)) <> ''
        ORDER BY Planta
    """)
    rows = db.session.execute(sql).mappings().all()
    # devolver lista simple de objetos { Planta: '...' } para facilitar sync en IndexedDB
    return jsonify([{'Planta': r['Planta']} for r in rows])

