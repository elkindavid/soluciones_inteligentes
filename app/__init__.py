from flask import Flask
from .extensions import db, login_manager
from .routes import web_bp
from .api import api_bp
from .auth import auth_bp
from .pwa import pwa_bp
from apps.optimizacion_mezcla_carbon.routes import optimizacion_bp
from .admin import admin_bp
from apps.control_logistico.routes import informes_bp
from apps.control_ingresos.routes import repingresos_bp
from apps.dashboard_logistico.init import dashboard_bp, init_dashboard
from apps.dashboard_logistico.views import dashboard_view_bp
from config import Config
import socket

def can_connect_sqlserver(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # comprobar conexión al SQL Server
    if can_connect_sqlserver("190.255.33.10", 2500):
        print("🔗 Conectado a SQL Server")
    else:
        print("⚠️ Offline: login se maneja en frontend con IndexedDB")

    # registrar blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(pwa_bp)
    app.register_blueprint(optimizacion_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(informes_bp)   # 👈 registrar aquí
    app.register_blueprint(repingresos_bp)   # 👈 registrar aquí
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dashboard_view_bp)
    init_dashboard(app)

    return app
