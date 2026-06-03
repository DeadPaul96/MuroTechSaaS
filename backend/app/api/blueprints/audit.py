from flask import Blueprint, jsonify, request

from app.api.decorators.auth import token_required
from app.api.decorators.rbac import require_role
from app.models import AuditoriaLog

bp = Blueprint('audit', __name__, url_prefix='/api/v1/auditoria')


@bp.route('', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor'])
def audit_index(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    accion = request.args.get('accion', '')

    query = AuditoriaLog.query.order_by(AuditoriaLog.timestamp.desc())
    if accion:
        query = query.filter(AuditoriaLog.accion.ilike(f'%{accion}%'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = [
        {
            'id': entry.id,
            'usuario_id': entry.usuario_id,
            'entidad': entry.entidad,
            'accion': entry.accion,
            'valores_antes': entry.valores_antes,
            'valores_despues': entry.valores_despues,
            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
            'ip_address': entry.ip_address,
            'user_agent': entry.user_agent,
        }
        for entry in pagination.items
    ]

    return jsonify({
        'success': True,
        'logs': logs,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    }), 200
