from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import login_required, current_user
from sqlalchemy import text
from .extensions import db
from .models import RegistroDestajo
from datetime import datetime, date
from .models import User, GHDestajo, GHEmpleado
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter

api_bp = Blueprint("api", __name__)

from flask import current_app, request, jsonify
from sqlalchemy import text
from .extensions import db
from sqlalchemy import create_engine

@api_bp.get("/employees")
@login_required
def employees():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    # 🔗 Solo SQL Server
    sql = text("""
        SELECT nombreCompleto, apellidoCompleto, numeroDocumento
        FROM GH_Empleados
        WHERE estado = 'ACTIVO' 
        AND (
            LOWER(LTRIM(RTRIM(nombreCompleto))) LIKE LOWER(:q)
            OR LOWER(LTRIM(RTRIM(apellidoCompleto))) LIKE LOWER(:q)
            OR LOWER(LTRIM(RTRIM(nombreCompleto)) + ' ' + LTRIM(RTRIM(apellidoCompleto))) LIKE LOWER(:q)
            OR CAST(numeroDocumento AS NVARCHAR(50)) LIKE :q
        )
        ORDER BY nombreCompleto
    """)
    rows = db.session.execute(sql, {'q': f'%{q}%'}).mappings().all()

    return jsonify([
        {
            'nombre': f"{r['nombreCompleto']} {r['apellidoCompleto']}".strip(),
            'documento': str(r['numeroDocumento'])
        }
        for r in rows
    ])

@api_bp.get("/destajos")
@login_required
def destajos_catalog():
    q = request.args.get("q", "").strip()

    
    # 🔹 Query para SQL Server
    sql = text("""
        SELECT Id, Planta, Concepto, Valor
        FROM GH_Destajos
        WHERE Concepto LIKE :q
        ORDER BY Concepto
    """)
    rows = db.session.execute(sql, {'q': f'%{q}%'}).mappings().all()

    return jsonify([
        {
            'id': int(r['Id']),
            'planta': r['Planta'],
            'concepto': r['Concepto'],
            'valor': float(r['Valor'])
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
    if not reg: return jsonify({'error':'not found'}), 404
    data = request.get_json(force=True)
    for k in ['empleado_documento','empleado_nombre']:
        if k in data: setattr(reg,k,data[k])
    if 'destajo_id' in data: reg.destajo_id = int(data['destajo_id'])
    if 'cantidad' in data: reg.cantidad = float(data['cantidad'])
    if 'fecha' in data: reg.fecha = datetime.fromisoformat(data['fecha']).date()
    db.session.commit()
    return jsonify({'ok': True})

@api_bp.delete("/registros/<int:rid>")
@login_required
def eliminar_registro(rid):
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
    sql += " ORDER BY r.fecha DESC, r.id DESC"
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
        destajos = GHDestajo.query.all()
        destajos_data = [e.to_dict() for e in destajos]  # asegúrate que el modelo tenga to_dict()
        return jsonify(destajos_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
from io import BytesIO
import pandas as pd
from sqlalchemy import text
from datetime import date
from flask import current_app

from flask import send_file, request, current_app
from sqlalchemy.sql import text
from io import BytesIO
import pandas as pd
from datetime import date
from openpyxl.styles import numbers

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

        df_group = df.groupby(['TipoDocumento','NumeroDocumento','Concepto','AreaFuncional'], as_index=False).agg({
            'Cantidad':'sum',
            'Valor':'mean'  # valor unitario
        })

        df_no_desc = df[~df['Concepto'].str.contains('DESCANSO|JORNAL', case=False, regex=True)]
        ponderado = (
            df_no_desc
            .assign(vxq=lambda x: x['Valor']*x['Cantidad'])
            .groupby('NumeroDocumento')
            .agg({'vxq':'sum','Cantidad':'sum'})
        )
        ponderado['PromPond'] = ponderado['vxq']/ponderado['Cantidad']
        prom_map = ponderado['PromPond'].to_dict()

        def calc_valor_total(row):
            concepto = (row.get('Concepto') or '').upper()
            qty = float(row.get('Cantidad',0))
            val = float(row.get('Valor',0))
            numdoc = row.get('NumeroDocumento')

            if 'JORNAL FESTIVO' in concepto:
                return SMV * 1.8 * qty
            if 'JORNAL' in concepto:
                return SMV * qty
            if 'DESCANSO' in concepto:
                prom = prom_map.get(numdoc,0)
                return prom * qty
            return ""

        df_group['ValorTotal'] = df_group.apply(calc_valor_total, axis=1)
        df_group['TipoNovedad'] = df_group['Concepto'].str.contains('DESCANSO|JORNAL', case=False, regex=True).map(lambda x: 4 if x else 3)
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

    # --- generar excel y ajustar columnas ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_out.to_excel(writer, index=False, sheet_name="Liquidacion")
        ws = writer.sheets["Liquidacion"]

        for col_idx, column_title in enumerate(df_out.columns, start=1):
            col_letter = get_column_letter(col_idx)
            col_cells = ws[col_letter]
            max_length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=len(column_title))
            ws.column_dimensions[col_letter].width = max_length + 2

            # Formato moneda en ValorTotal
            if column_title == 'ValorTotal':
                for c in col_cells[1:]:  # datos, sin cabecera
                    c.number_format = '$ #,##0.00'

    output.seek(0)
    return send_file(
        output,
        download_name="liquidacion.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )




