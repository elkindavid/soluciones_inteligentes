# apps/dashboard_logistico/__init__.py

from flask import Blueprint

dashboard_bp = Blueprint(
    "dashboard_logistico",          # nombre del blueprint
    __name__,                       # nombre del módulo actual (requerido)
    template_folder="templates",
    static_folder="static",
    url_prefix="/dashboard"
)

def init_dashboard(app):
    """
    Inicializa el dashboard y lo monta en la app Flask.
    Importamos init_dash dentro de la función para evitar ciclos de importación.
    """
    from .routes import init_dash
    init_dash(app)
