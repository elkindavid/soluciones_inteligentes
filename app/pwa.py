from flask import Blueprint, send_from_directory, make_response

pwa_bp = Blueprint('pwa', __name__)

@pwa_bp.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@pwa_bp.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('.', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response
