"""Decorador de auditoría de cambios."""
from functools import wraps

from flask import request

from app.services.auditoria_service import AuditoriaService


def audit_log(entity_name, snapshot_fn=None):
    """
    Registra cambios en AuditoriaLog.
    snapshot_fn(current_user, *args, **kwargs) -> dict estado antes
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = args[0] if args else None
            before = None
            if snapshot_fn and current_user:
                try:
                    before = snapshot_fn(current_user, *args, **kwargs)
                except Exception:
                    before = None
            response = func(*args, **kwargs)
            after = None
            if snapshot_fn and current_user:
                try:
                    after = snapshot_fn(current_user, *args, **kwargs)
                except Exception:
                    after = None
            AuditoriaService.log_change(
                usuario_id=getattr(current_user, 'id', None),
                entidad=entity_name,
                accion=request.method,
                valores_antes=before,
                valores_despues=after,
            )
            return response

        return wrapper

    return decorator
