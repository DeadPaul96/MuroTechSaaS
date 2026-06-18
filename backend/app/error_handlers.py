"""Manejadores de errores globales de la aplicación."""
import logging
import traceback

from flask import jsonify

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Registra controladores de errores globales."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Solicitud inválida', 'code': 'BAD_REQUEST'}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'No autorizado', 'code': 'UNAUTHORIZED'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Acceso denegado', 'code': 'FORBIDDEN'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Recurso no encontrado', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Método no permitido', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'error': 'Demasiadas solicitudes. Intente nuevamente más tarde.',
            'code': 'RATE_LIMIT_EXCEEDED',
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error('Error interno del servidor: %s\n%s', error, traceback.format_exc())
        return jsonify({'error': 'Error interno del servidor', 'code': 'INTERNAL_SERVER_ERROR'}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.error('Excepción no manejada: %s\n%s', error, traceback.format_exc())
        return jsonify({'error': 'Error inesperado del servidor', 'code': 'UNHANDLED_EXCEPTION'}), 500
