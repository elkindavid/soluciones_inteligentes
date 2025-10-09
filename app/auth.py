from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db, login_manager
from .models import User, LocalUser, Roles   # 👈 importa LocalUser
from sqlalchemy.exc import OperationalError, InterfaceError
from flask import current_app
import logging

auth_bp = Blueprint("auth", __name__, template_folder="templates")

logger = logging.getLogger(__name__)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Debes iniciar sesión primero.", "error")
            return redirect(url_for("auth.login"))
        if not getattr(current_user, "is_admin", False):
            flash("No tienes permisos para acceder a esta sección", "error")
            return redirect(url_for("web.home"))
        return f(*args, **kwargs)
    return wrapper

def admin_required_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # no logueado
        if not getattr(current_user, "is_admin", False):
            abort(403)  # sin permisos
        return f(*args, **kwargs)
    return wrapper

# Listado de usuarios (solo admins)
@auth_bp.route("/usuarios")
def listado():
    users = User.query.order_by(User.id).all()
    return render_template("usuarios_listado.html", users=users)

# Cargar usuario según tipo de DB
@login_manager.user_loader
def load_user(user_id):
    try:
        # 🔗 Solo online (SQL Server)
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error cargando usuario: {e}")
        return None

# Login dinámico online/offline
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")

        # Solo online → SQL Server
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
              # ⬇️ guardar el rol en la sesión
            session['role_id'] = user.rol_id

            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("web.home"))

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template("auth_login.html")

# Registro de usuarios (solo admins)
@auth_bp.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    # Traer lista de roles para el form, excluye al SuperUsuario
    roles = Roles.query.filter(Roles.Nombre != "SuperUsuario").all()


    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        is_admin_flag = True if request.form.get("is_admin") == "on" else False
        rol_id = request.form.get("rol_id")  # nuevo campo del formulario

        if User.query.filter_by(email=email).first():
            flash("Ese correo ya está registrado", "error")
        else:
            user = User(
                email=email,
                name=name,
                password_hash=generate_password_hash(password),
                is_admin=is_admin_flag,
                rol_id=rol_id  # guardas el rol seleccionado
            )
            db.session.add(user)
            db.session.commit()
            flash("Usuario creado", "success")
            return redirect(url_for("auth.listado"))
    
    # Pasas roles al template para el select
    return render_template("auth_register.html", roles=roles)

# Cambiar contraseña
@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not check_password_hash(current_user.password_hash, current_password):
            flash("La contraseña actual es incorrecta", "error")
            return redirect(url_for("auth.change_password"))

        if new_password != confirm_password:
            flash("Las contraseñas nuevas no coinciden", "error")
            return redirect(url_for("auth.change_password"))

        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("Tu contraseña ha sido actualizada correctamente", "success")
        return redirect(url_for("web.home"))

    return render_template("auth_change_password.html")


# Logout
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

# GET /auth/users
@auth_bp.route("/users", methods=["GET"])
def get_users():
    try:
        users = User.query.all()
        users_data = [u.to_dict() for u in users]  # asegúrate que el modelo tenga to_dict()
        return jsonify(users_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
