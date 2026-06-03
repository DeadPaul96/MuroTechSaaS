from functools import wraps
from flask import request, jsonify
from app.models import AccesoSucursal

def require_role(allowed_roles):
    """
    Decorador para verificar si el usuario tiene permiso en una sucursal.
    Espera que la petición incluya 'sucursal_id' en los headers o args.
    """
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.is_superadmin:
                return f(current_user, *args, **kwargs)
                
            sucursal_id = request.headers.get('X-Sucursal-ID') or request.args.get('sucursal_id')
            if not sucursal_id:
                return jsonify({'message': 'Debe especificar la sucursal (X-Sucursal-ID).'}), 400
                
            acceso = AccesoSucursal.query.filter_by(usuario_id=current_user.id, sucursal_id=sucursal_id).first()
            if not acceso or acceso.rol.nombre not in allowed_roles:
                return jsonify({'message': 'No tiene permisos suficientes en esta sucursal.'}), 403
                
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator
