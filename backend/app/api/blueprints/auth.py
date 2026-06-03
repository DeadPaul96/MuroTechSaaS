import os
from flask import Blueprint, jsonify, request, current_app
from app.api.decorators.auth import token_required
from app.api.decorators.audit import audit_log
from app.extensions import limiter
from app.services.auth_service import AuthService, AuthenticationError, AuthorizationError

bp = Blueprint('auth', __name__, url_prefix='/api')


def is_company_admin(user):
    return AuthService.is_company_admin(user)


def get_profile_type(user):
    return AuthService.get_profile_type(user)


@bp.route('/login', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_LOGIN', '20 per hour'))
def login():
    data = request.get_json() or {}
    try:
        result = AuthService.login(data.get('email'), data.get('password'))
        return jsonify(result), 200
    except AuthenticationError as exc:
        return jsonify({'message': str(exc)}), 401
    except AuthorizationError as exc:
        return jsonify({'message': str(exc)}), 403


@bp.route('/csrf-token', methods=['GET'])
def csrf_token():
    token = os.environ.get('CSRF_SECRET', '')
    if not token:
        return jsonify({'message': 'CSRF_SECRET no configurado.'}), 500

    origin = request.headers.get('Origin') or request.headers.get('Referer', '')
    allowed = current_app.config.get('CORS_ORIGINS', [])
    if origin and not any(origin.startswith(o.rstrip('/')) for o in allowed):
        return jsonify({'message': 'Origen no permitido.', 'code': 'CSRF_ORIGIN'}), 403

    return jsonify({'csrf_token': token}), 200


@bp.route('/logout', methods=['POST'])
@token_required
@audit_log('sesion')
def logout(current_user):
    AuthService.logout(current_user)
    return jsonify({'message': 'Sesión cerrada correctamente.'}), 200
