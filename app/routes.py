from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from sqlalchemy import text
from .extensions import db

web_bp = Blueprint("web", __name__, template_folder="templates")

@web_bp.route("/")
@login_required
def home():
    # leer rol del usuario logueado
    user_role_id = current_user.rol_id  # ya mapeado en tu modelo User
    
    sql = text("""
        SELECT a.AreaID, a.Nombre, a.Icono
        FROM Areas a
        JOIN Permisos p ON p.AreaID = a.AreaID
        WHERE p.RolID = :role_id
    """)
    areas = db.session.execute(sql, {'role_id': user_role_id}).mappings().all()
    
    return render_template("home.html", areas=areas)

@web_bp.route("/destajos")
@login_required
def destajos():
    # Aquí tu vista de registro y consulta
    return render_template(
        "destajos.html", 
        user=current_user,
        is_admin = current_user.is_admin
    )

# Ruta para App de prueba
@web_bp.route("/appprueba")
@login_required
def appprueba():
    # Renderiza un template simple
    return render_template(
        "appprueba.html",
        user=current_user,
        is_admin=current_user.is_admin
    )

@web_bp.route("/consultar")
@login_required
def consultar():
    # Vista de consulta/edición/eliminación
    return render_template(
        "consultar.html", 
        user=current_user,
        is_admin = current_user.is_admin
    )

@web_bp.route('/areas')
@login_required
def areas():
    user_role_id = session['role_id']
    
    sql = text("""
        SELECT a.AreaID, a.Nombre, a.Icono
        FROM Areas a
        JOIN Permisos p ON p.AreaID = a.AreaID
        WHERE p.RolID = :role_id
    """)
    rows = db.session.execute(sql, {'role_id': user_role_id}).mappings().all()

    return render_template('areas.html', areas = rows)

@web_bp.route('/apps/<int:area_id>')
@login_required
def apps(area_id):
    user_role_id = session.get('role_id')

    sql = text("""
        SELECT app.AppID, app.Nombre, app.Url, app.Icono
        FROM Apps app
        JOIN Permisos p ON (p.AppID = app.AppID OR p.AreaID = app.AreaID)
        WHERE app.AreaID = :area_id AND p.RolID = :role_id
    """)
    rows = db.session.execute(sql, {
        'area_id': area_id,
        'role_id': user_role_id
    }).mappings().all()

    return render_template('apps.html', apps=rows)