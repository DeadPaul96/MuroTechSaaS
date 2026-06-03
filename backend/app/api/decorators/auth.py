from functools import wraps
import jwt
from flask import request, jsonify, current_app
from app.models import Usuario, RevokedToken, SuperAdminEmpresa

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'message': 'Token faltante. Acceso denegado.'}), 401
        
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=[current_app.config.get('JWT_ALGORITHM', 'HS256')],
                audience=current_app.config.get('JWT_AUDIENCE', 'murotech-api'),
                issuer=current_app.config.get('JWT_ISSUER', 'murotech'),
                leeway=current_app.config.get('JWT_LEEWAY', 30),
                options={'require': ['exp', 'iat', 'aud', 'iss']},
            )
            current_user = Usuario.query.get(data['user_id'])
            if not current_user:
                raise Exception("Usuario no encontrado")
            if not current_user.is_active:
                return jsonify({'message': 'Usuario inactivo. Acceso denegado.'}), 403
            if not current_user.empresa or not current_user.empresa.is_active:
                return jsonify({'message': 'Empresa inactiva. Acceso denegado.'}), 403
            if current_user.empresa.plan_estado != 'activo':
                return jsonify({'message': 'Cuenta con plan bloqueado. Contacte al administrador.'}), 403
            
            revoked = RevokedToken.query.filter_by(token=token).first()
            if revoked:
                return jsonify({'message': 'Token revocado. Inicie sesión nuevamente.'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado. Inicie sesión nuevamente.'}), 401
        except jwt.InvalidAudienceError:
            return jsonify({'message': 'Token con audiencia inválida.'}), 401
        except jwt.InvalidIssuerError:
            return jsonify({'message': 'Token con emisor inválido.'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token inválido o expirado.', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Token faltante', 'code': 'TOKEN_MISSING'}), 401
        
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=[current_app.config.get('JWT_ALGORITHM', 'HS256')],
                audience=current_app.config.get('JWT_AUDIENCE', 'murotech-api'),
                issuer=current_app.config.get('JWT_ISSUER', 'murotech'),
                leeway=current_app.config.get('JWT_LEEWAY', 30),
                options={'require': ['exp', 'iat', 'aud', 'iss']},
            )
            # Verify that is superadmin
            if not data.get('is_superadmin'):
                return jsonify({'error': 'Acceso denegado. Se requiere rol SuperAdmin', 'code': 'SUPERADMIN_REQUIRED'}), 403
            
            current_user = Usuario.query.get(data.get('user_id'))
            if not current_user:
                return jsonify({'error': 'Usuario no encontrado', 'code': 'USER_NOT_FOUND'}), 401
            if not current_user.is_superadmin:
                return jsonify({'error': 'SuperAdmin no válido', 'code': 'INVALID_SUPERADMIN'}), 403

            revoked = RevokedToken.query.filter_by(token=token).first()
            if revoked:
                return jsonify({'error': 'Token revocado', 'code': 'TOKEN_REVOKED'}), 401

            # Obtener asignaciones de ámbito (empresas asignadas al superadmin)
            assigned_links = SuperAdminEmpresa.query.filter_by(superadmin_id=current_user.id).all()
            current_user.assigned_company_ids = [link.empresa_id for link in assigned_links]
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidAudienceError:
            return jsonify({'error': 'Token con audiencia inválida', 'code': 'INVALID_AUDIENCE'}), 401
        except jwt.InvalidIssuerError:
            return jsonify({'error': 'Token con emisor inválido', 'code': 'INVALID_ISSUER'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': 'Token inválido', 'code': 'INVALID_TOKEN', 'message': str(e)}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated
