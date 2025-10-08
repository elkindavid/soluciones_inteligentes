from flask import Blueprint, render_template
from flask_login import login_required

dashboard_view_bp = Blueprint("dashboard_view", __name__, template_folder="templates")

@dashboard_view_bp.route("/dashboard_logistico")
@login_required
def dashboard_view():
    """
    Renderiza la plantilla base que embebe el Dash.
    """
    return render_template("dashboard_logistico.html")
