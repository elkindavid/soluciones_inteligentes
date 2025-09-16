# apps/optimizacion/routes.py
from flask import Blueprint, render_template, request, send_file, session
from flask_login import login_required, current_user
from .modelo import procesar_archivo  # ajusta import según tu estructura
import os
import io
import pandas as pd

optimizacion_bp = Blueprint(
    "optimizacion",
    __name__,
     url_prefix="/optimizar",
    template_folder="templates"
)

UPLOAD_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
global_df_sol = None

@optimizacion_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    global global_df_sol
    if request.method == 'POST':
        if 'archivo' in request.files and request.files['archivo'].filename != '':
            archivo = request.files['archivo']
            filepath = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(filepath)
            session['archivo_path'] = filepath
        elif 'archivo_path' in session:
            filepath = session['archivo_path']
        else:
            return "⚠️ Debes subir un archivo Excel antes de ejecutar el modelo.", 400

        if not os.path.exists(filepath):
            session.pop('archivo_path', None)
            return "⚠️ El archivo cargado ya no está disponible. Por favor súbelo de nuevo.", 400

        solo_mineros = 'solo_mineros' in request.form
        limite = int(request.form['limite']) / 100
        modelo = request.form.get('modelo', 'precio')

        resultados = procesar_archivo(filepath, solo_mineros, limite, modelo)
        global_df_sol = resultados['df_sol'].copy()
        return render_template(
            'index.html',  # plantilla dentro de apps/optimizacion/templates/optimizar
            **resultados,
            solo_mineros=solo_mineros,
            limite_comercializadores=int(request.form['limite'])
            
        )

    return render_template(
        'index.html',
        limite_comercializadores=100,
        solo_mineros=False,
        modelo_usado=None
    )

@optimizacion_bp.route('/descargar_excel', endpoint='descargar_excel')
@login_required
def descargar_excel():
    global global_df_sol
    if global_df_sol is None:
        return "No hay resultados para exportar.", 400

    output = io.BytesIO()
    global_df_sol.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        download_name="resultados_optimizacion.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
