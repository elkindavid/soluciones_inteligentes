# admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .extensions import db
from .models import App, Area, Roles, Permiso
import re

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def solo_superusuario():
    if not current_user.superusuario:
        flash("No tienes permisos para acceder.")
        return False
    return True

@admin_bp.route('/panel')
@login_required
def panel():
    if not solo_superusuario(): return redirect(url_for('web.index'))
    apps = App.query.all()
    areas = Area.query.all()
    roles = Roles.query.all()
    permisos = Permiso.query.all()
    return render_template('admin/panel.html', apps=apps, areas=areas, roles=roles, permisos=permisos)

# @admin_bp.route('/apps/new', methods=['GET', 'POST'])
# @login_required
# def new_app():
#     if not solo_superusuario(): return redirect(url_for('web.index'))
#     if request.method == 'POST':
#         area_id = request.form['area_id']
#         nombre = request.form['nombre']
#         url = request.form['url']
#         icono = request.form['icono']
#         app = App(AreaID=area_id, Nombre=nombre, Url=url, Icono=icono)
#         db.session.add(app)
#         db.session.commit()
#         flash("App creada")
#         return redirect(url_for('admin.panel'))
#     areas = Area.query.all()
#     return render_template('admin/new_app.html', areas=areas)

@admin_bp.route('/apps/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_app(app_id):
    app = db.session.get(App, app_id)
    if not app:
        flash('App no encontrada')
        return redirect(url_for('admin.panel'))  # redirige al panel de admin

    areas = Area.query.all()  # lista de áreas para el dropdown

    if request.method == 'POST':
        app.Nombre = request.form['nombre']
        app.Url = request.form['url']
        app.Icono = request.form['icono']
        area_id = request.form.get('area_id')
        app.AreaID = int(area_id) if area_id else None
        db.session.commit()
        flash('App actualizada correctamente')
        return redirect(url_for('admin.panel'))

    return render_template('admin/editar_app.html', app=app, areas=areas)

@admin_bp.route('/apps/<int:app_id>/delete', methods=['POST'])
@login_required
def eliminar_app(app_id):
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    app = db.session.get(App, app_id)
    if not app:
        flash('App no encontrada', 'warning')
        return redirect(url_for('admin.panel'))

    # Verificar si está asociada a un Área
    if app.AreaID:
        flash('No se puede eliminar la App porque está asociada a un Área', 'warning')
        return redirect(url_for('admin.panel'))

    # Verificar si tiene permisos asignados (Roles)
    permisos_asociados = db.session.query(Permiso).filter_by(AppID=app_id).count()
    if permisos_asociados > 0:
        flash('No se puede eliminar la App porque tiene Permisos asignados', 'warning')
        return redirect(url_for('admin.panel'))

    # Si pasó ambas verificaciones, eliminar
    db.session.delete(app)
    db.session.commit()
    flash('App eliminada correctamente', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/areas/new', methods=['GET', 'POST'])
@login_required
def new_area():
    if not solo_superusuario(): return redirect(url_for('web.index'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        area = Area(Nombre=nombre)
        db.session.add(area)
        db.session.commit()
        flash("Área creada")
        return redirect(url_for('admin.panel'))
    return render_template('admin/new_area.html')

@admin_bp.route('/areas/<int:area_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_area(area_id):
    if not solo_superusuario(): 
        return redirect(url_for('web.index'))

    area = db.session.get(Area, area_id)
    if not area:
        flash('Área no encontrada')
        return redirect(url_for('admin.panel'))

    if request.method == 'POST':
        area.Nombre = request.form['nombre']
        db.session.commit()
        flash('Área actualizada correctamente')
        return redirect(url_for('admin.panel'))

    return render_template('admin/editar_area.html', area=area)


# Eliminar área
@admin_bp.route('/areas/<int:area_id>/delete', methods=['POST'])
@login_required
def eliminar_area(area_id):
    if not solo_superusuario(): 
        return redirect(url_for('web.index'))

    area = db.session.get(Area, area_id)
    if not area:
        flash('Área no encontrada', 'warning')
        return redirect(url_for('admin.panel'))

    # Revisa si hay apps asociadas a esa área
    apps_asociadas = db.session.query(App).filter_by(AreaID=area_id).count()

    if apps_asociadas > 0:
        flash('No se puede eliminar el área porque tiene Apps asociadas', 'warning')
        return redirect(url_for('admin.panel'))

    db.session.delete(area)
    db.session.commit()
    flash('Área eliminada correctamente', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/roles/new', methods=['GET', 'POST'])
@login_required
def new_rol():
    if not solo_superusuario(): return redirect(url_for('web.index'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        rol = Roles(Nombre=nombre)
        db.session.add(rol)
        db.session.commit()
        flash("Rol creado")
        return redirect(url_for('admin.panel'))
    return render_template('admin/new_rol.html')

@admin_bp.route('/permisos/new', methods=['GET', 'POST'])
@login_required
def new_permiso():
    if not solo_superusuario(): return redirect(url_for('web.index'))
    if request.method == 'POST':
        rol_id = request.form['rol_id']
        app_id = request.form.get('app_id') or None
        permiso = Permiso(RolID=rol_id, AppID=app_id)
        db.session.add(permiso)
        db.session.commit()
        flash("Permiso creado")
        return redirect(url_for('admin.panel'))
    roles = Roles.query.all()
    areas = Area.query.all()
    apps = App.query.all()
    return render_template('admin/new_permiso.html', roles=roles, areas=areas, apps=apps)

@admin_bp.route('/roles/<int:rol_id>/edit', methods=['GET','POST'])
@login_required
def editar_rol(rol_id):
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    rol = db.session.get(Roles, rol_id)
    if not rol:
        flash('Rol no encontrado')
        return redirect(url_for('admin.panel'))

    if request.method == 'POST':
        rol.Nombre = request.form['nombre']
        db.session.commit()
        flash('Rol actualizado correctamente')
        return redirect(url_for('admin.panel'))

    return render_template('admin/editar_rol.html', rol=rol)

# Eliminar rol
@admin_bp.route('/roles/<int:rol_id>/delete', methods=['POST'])
@login_required
def eliminar_rol(rol_id):
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    rol = db.session.get(Roles, rol_id)
    if not rol:
        flash('Rol no encontrado', 'warning')
        return redirect(url_for('admin.panel'))

    # Revisa si hay permisos asociados a ese rol
    permisos_asociados = db.session.query(Permiso).filter_by(RolID=rol_id).count()

    if permisos_asociados > 0:
        flash('No se puede eliminar el rol porque tiene Permisos asociados', 'warning')
        return redirect(url_for('admin.panel'))

    db.session.delete(rol)
    db.session.commit()
    flash('Rol eliminado correctamente', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/apps/matriz', methods=['GET'])
@login_required
def matriz_apps_areas():
    if not solo_superusuario():
        return redirect(url_for('web.index'))
    apps = App.query.all()
    areas = Area.query.all()
    return render_template('admin/matriz_apps_areas.html', apps=apps, areas=areas)

@admin_bp.route('/apps/matriz', methods=['POST'])
@login_required
def guardar_apps_areas():
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    # recorre directamente request.form
    for key, value in request.form.items():
        m = re.match(r'app_area\[(\d+)\]', key)
        if not m:
            continue
        app_id = int(m.group(1))
        area_id = value  # puede venir '' si eligieron Sin Área
        app = db.session.get(App, app_id)
        if app:
            if area_id == '' or area_id is None:
                app.AreaID = None
            else:
                app.AreaID = int(area_id)

    db.session.commit()
    flash('Relaciones Apps–Áreas actualizadas correctamente')
    return redirect(url_for('admin.matriz_apps_areas'))

@admin_bp.route('/apps/matriz_roles', methods=['GET'])
@login_required
def matriz_apps_roles():
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    roles = Roles.query.all()
    apps = App.query.all()
    permisos = Permiso.query.all()

    # aquí NO hay flash
    return render_template(
        'admin/matriz_apps_roles.html',
        roles=roles,
        apps=apps,
        permisos=permisos
    )


@admin_bp.route('/apps/matriz_roles', methods=['POST'])
@login_required
def guardar_apps_roles():
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    # Limpiar los permisos actuales (o haz diff)
    Permiso.query.delete()

    for key, value in request.form.items():
        m = re.match(r'rol_app\[(\d+)\]\[(\d+)\]', key)
        if not m:
            continue
        rol_id = int(m.group(1))
        app_id = int(m.group(2))
        permiso = Permiso(RolID=rol_id, AppID=app_id)
        db.session.add(permiso)

    db.session.commit()

    # aquí sí lanzas el mensaje
    flash('✅ Permisos Roles–Apps actualizados correctamente', 'success')
    return redirect(url_for('admin.matriz_apps_roles'))

@admin_bp.route('/apps/new', methods=['GET', 'POST'])
@login_required
def new_app():
    if not solo_superusuario():
        return redirect(url_for('web.index'))

    areas = db.session.query(Area).all()

    if request.method == 'POST':
        nombre = request.form['nombre']
        url = request.form['url']
        icono = request.form['icono']
        area_id = request.form['area_id']

        # corregir valor para el FK
        if area_id == '' or area_id is None:
            area_id = None
        else:
            area_id = int(area_id)

        nueva_app = App(
            Nombre=nombre,
            Url=url,
            Icono=icono,
            AreaID=area_id
        )

        db.session.add(nueva_app)
        db.session.commit()
        flash('App creada correctamente', 'success')
        return redirect(url_for('admin.panel'))

    return render_template('admin/new_app.html', areas=areas)
