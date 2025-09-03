from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import text
from .extensions import db
from .models import RegistroDestajo
from datetime import datetime, date
from .models import User, GHDestajo, GHEmpleado

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

    if current_app.config["IS_ONLINE"]:
        # 🔹 Query para SQL Server
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

    else:
        # 🔹 Query para SQLite
        sqlite_uri = current_app.config["SQLALCHEMY_DATABASE_URI_SQLITE"]
        sqlite_engine = create_engine(sqlite_uri)

        sql = text("""
            SELECT nombreCompleto, apellidoCompleto, numeroDocumento
            FROM GH_Empleados
            WHERE estado = 'ACTIVO'
            AND (
                LOWER(TRIM(nombreCompleto)) LIKE LOWER(:q)
                OR LOWER(TRIM(apellidoCompleto)) LIKE LOWER(:q)
                OR LOWER(TRIM(nombreCompleto) || ' ' || TRIM(apellidoCompleto)) LIKE LOWER(:q)
                OR CAST(numeroDocumento AS TEXT) LIKE :q
            )
            ORDER BY nombreCompleto
        """)

        with sqlite_engine.connect() as conn:
            rows = conn.execute(sql, {'q': f'%{q}%'}).mappings().all()

    return jsonify([{
        'nombre': f"{r['nombreCompleto']} {r['apellidoCompleto']}".strip(),
        'documento': str(r['numeroDocumento'])
    } for r in rows])

@api_bp.get("/destajos")
@login_required
def destajos_catalog():
    q = request.args.get("q", "").strip()

    if current_app.config["IS_ONLINE"]:
        # 🔹 Query para SQL Server
        sql = text("""
            SELECT Id, Planta, Concepto, Valor
            FROM GH_Destajos
            WHERE Concepto LIKE :q
            ORDER BY Concepto
        """)
        rows = db.session.execute(sql, {'q': f'%{q}%'}).mappings().all()

    else:
        # 🔹 Query para SQLite
        sqlite_uri = current_app.config["SQLALCHEMY_DATABASE_URI_SQLITE"]
        sqlite_engine = create_engine(sqlite_uri)

        sql = text("""
            SELECT Id, Planta, Concepto, Valor
            FROM GH_Destajos
            WHERE Concepto LIKE :q
            ORDER BY Concepto
        """)
        with sqlite_engine.connect() as conn:
            rows = conn.execute(sql, {'q': f'%{q}%'}).mappings().all()

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