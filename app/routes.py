from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

web_bp = Blueprint("web", __name__, template_folder="templates")

@web_bp.route("/")
@login_required
def home():
    return render_template("home.html")

@web_bp.route("/destajos")
@login_required
def destajos():
    # Aquí tu vista de registro y consulta
    return render_template("destajos.html", user=current_user)

@web_bp.route("/consultar")
@login_required
def consultar():
    # Vista de consulta/edición/eliminación
    return render_template("consultar.html", user=current_user)
