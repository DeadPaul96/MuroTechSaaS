"""Configuración pública del backend y estado del sistema."""
import os

from flask import Blueprint, jsonify, current_app

bp = Blueprint('config', __name__, url_prefix='/api/v1/config')


@bp.route('', methods=['GET'])
def get_config():
    """Retorna parámetros de configuración pública del sistema."""
    from app.services.billing_plans import plans_public_payload

    return jsonify({
        'app_name': 'MUROTECH SaaS',
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'hacienda_enabled': os.environ.get('HACIENDA_SEND_ENABLED', 'false').lower() in ('1', 'true', 'yes'),
        'xsd_validation': os.environ.get('HACIENDA_XSD_VALIDATE', 'true').lower() in ('1', 'true', 'yes'),
        'recaptcha_enabled': bool(os.environ.get('RECAPTCHA_SITE_KEY')),
        'plans': plans_public_payload(),
        'supported_currencies': ['CRC', 'USD', 'EUR'],
        'supported_doc_types': [
            {'code': '01', 'label': 'Factura Electrónica'},
            {'code': '02', 'label': 'Nota de Débito Electrónica'},
            {'code': '03', 'label': 'Nota de Crédito Electrónica'},
            {'code': '04', 'label': 'Tiquete Electrónico'},
            {'code': '05', 'label': 'Factura Electrónica de Exportación'},
            {'code': '09', 'label': 'Factura Electrónica de Contingencia'},
            {'code': '10', 'label': 'Tiquete Electrónico de Contingencia'},
        ],
    }), 200
