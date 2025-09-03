from flask import Flask
from .extensions import db, login_manager
from .models import User, LocalUser, GHDestajo, GHEmpleado
from .routes import web_bp
from .api import api_bp
from .auth import auth_bp
from .pwa import pwa_bp
from config import Config
import socket
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def can_connect_sqlserver(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def sync_sqlite(app):
    """Sincroniza datos de SQL Server a SQLite (bind local en raíz)."""
    sqlite_uri = app.config["SQLALCHEMY_DATABASE_URI_SQLITE"]
    engine = create_engine(sqlite_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Crear tablas si no existen
    User.__table__.create(bind=engine, checkfirst=True)
    GHDestajo.__table__.create(bind=engine, checkfirst=True)
    GHEmpleado.__table__.create(bind=engine, checkfirst=True)

    # Copiar datos de SQL Server
    with app.app_context():
        for u in User.query.all():
            session.merge(User(
                id=u.id,
                email=u.email,
                name=u.name,
                password_hash=u.password_hash,
                is_admin=u.is_admin
            ))
        for d in GHDestajo.query.all():
            session.merge(GHDestajo(
                Id=d.Id,
                Planta=d.Planta,
                Concepto=d.Concepto,
                Valor=d.Valor
            ))
        for e in GHEmpleado.query.all():
            session.merge(GHEmpleado(
                numeroDocumento=e.numeroDocumento,
                tipoIdentificacion=e.tipoIdentificacion,
                nombreCompleto=e.nombreCompleto,
                apellidoCompleto=e.apellidoCompleto,
                cargo=e.cargo,
                centroCosto=e.centroCosto,
                estado=e.estado,
                nombreNomina=e.nombreNomina,
                compania=e.compania,
                agrupador4=e.agrupador4
            ))
        session.commit()
    session.close()
    print("✅ Datos sincronizados a SQLite (bind local raíz)")

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # 👉 Forzar SQLite en raíz, no en instance
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI_SQLITE"] = f"sqlite:///{os.path.join(BASE_DIR, 'local.db')}"

    db.init_app(app)
    login_manager.init_app(app)

    # Verificar conexión SQL Server
    sql_server_host = "190.255.33.10"
    sql_server_port = 2500
    # is_online = can_connect_sqlserver(sql_server_host, sql_server_port)
    is_online = can_connect_sqlserver(sql_server_host, sql_server_port)

    
    app.config["IS_ONLINE"] = is_online   # 👈 guardar el flag en config

    if is_online:
        print("🔗 Conectado a SQL Server")
        with app.app_context():
            sync_sqlite(app)
    else:
        print("⚠️ Offline: login se maneja en frontend con IndexedDB")
        login_manager.anonymous_user = login_manager.anonymous_user or type(
            "AnonymousUser", (), {"is_authenticated": False}
        )()

    # Registrar Blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(pwa_bp)

    return app
