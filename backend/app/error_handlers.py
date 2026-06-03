from flask import jsonify


def register_error_handlers(app):
    """Registra controladores de errores globales."""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Recurso no encontrado', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Método no permitido', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Error interno del servidor', 'code': 'INTERNAL_SERVER_ERROR'}), 500
