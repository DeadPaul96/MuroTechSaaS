from flask import Blueprint, jsonify

bp = Blueprint('config', __name__, url_prefix='/api/v1/config')


@bp.route('', methods=['GET'])
def get_config():
    return jsonify({'message': 'Configuración pública del backend: implementar parámetros dinámicos.'}), 200
