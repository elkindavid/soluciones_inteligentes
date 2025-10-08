from flask import redirect, url_for, request
from flask_login import current_user
from dash import Dash

from .layout import build_layout
from .callbacks import register_callbacks

def init_dash(server):
    """
    Monta un Dash app dentro del Flask `server` en la ruta /dashboard/logistico/
    Incluye Tailwind vía CDN en external_scripts.
    """
    url_base = "/dashboard/"

    dash_app = Dash(
        __name__,
        server=server,
        url_base_pathname=url_base,
        assets_folder="app/static",
        external_scripts=["https://cdn.tailwindcss.com"],
        suppress_callback_exceptions=True,
    )

    # 🔒 Protección de ruta
    @server.before_request
    def protect_dash():
        path = request.path or ""
        if path.startswith(url_base):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))

    # 📊 Layout y callbacks
    dash_app.layout = build_layout()
    register_callbacks(dash_app)

    # Registrar la app Dash dentro del servidor principal
    server.dash_apps = getattr(server, "dash_apps", {})
    server.dash_apps["logistico"] = dash_app
