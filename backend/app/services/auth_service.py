import jwt
import uuid
from datetime import datetime, timedelta, timezone
from flask import current_app, request

from app.models import Usuario, RevokedToken, Sucursal
from app.extensions import db
from app.services.billing_plans import get_plan_info


class AuthenticationError(ValueError):
    pass


class AuthorizationError(ValueError):
    pass


class AuthService:
    @staticmethod
    def login(email, password):
        if not email or not password:
            raise AuthenticationError('Email y contraseña son requeridos.')

        user = Usuario.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            raise AuthenticationError('Usuario o contraseña inválidos.')

        if not user.is_active:
            raise AuthorizationError('Usuario inactivo. Contacte al administrador.')
        if not getattr(user, 'empresa', None) or not user.empresa.is_active:
            raise AuthorizationError('Empresa inactiva. Contacte al administrador.')
        if getattr(user, 'empresa', None) and user.empresa.plan_estado != 'activo':
            raise AuthorizationError('Cuenta con plan bloqueado. Contacte al administrador.')

        token = AuthService._generate_token(user)
        return AuthService._build_login_response(user, token)

    @staticmethod
    def logout(user):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            token = request.args.get('token')

        if token:
            revoked = RevokedToken(token=token)
            db.session.add(revoked)
            db.session.commit()

    @staticmethod
    def get_profile(user):
        return {
            'id': user.id,
            'nombre': user.nombre,
            'email': user.email,
            'is_superadmin': user.is_superadmin,
            'empresa_id': user.empresa_id,
            'roles': [access.rol.nombre for access in getattr(user, 'accesos', []) if access.rol],
        }

    @staticmethod
    def _generate_token(user):
        now = datetime.now(timezone.utc)
        payload = {
            'jti': uuid.uuid4().hex,
            'user_id': user.id,
            'empresa_id': user.empresa_id,
            'is_superadmin': user.is_superadmin,
            'exp': now + timedelta(seconds=current_app.config.get('JWT_EXPIRY', 3600)),
            'iat': now,
            'aud': current_app.config.get('JWT_AUDIENCE', 'murotech-api'),
            'iss': current_app.config.get('JWT_ISSUER', 'murotech'),
            'type': 'access',
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm=current_app.config.get('JWT_ALGORITHM', 'HS256'),
        )

    @staticmethod
    def _is_company_admin(user):
        if not user:
            return False
        return any(access.rol and access.rol.nombre == 'Administrador' for access in getattr(user, 'accesos', []))

    @staticmethod
    def is_company_admin(user):
        return AuthService._is_company_admin(user)

    @staticmethod
    def get_profile_type(user):
        if not user:
            return None
        if user.is_superadmin:
            return 'SuperAdmin'
        if AuthService._is_company_admin(user):
            return 'Emisor'
        return 'Usuario'

    @staticmethod
    def _get_pantallas(user):
        if user.is_superadmin:
            return ['superAdmin']
        if AuthService._is_company_admin(user):
            return [
                'auditoria', 'clientes', 'configuracion', 'cotizaciones',
                'editarFactura', 'inventario', 'notificaciones',
                'panelControl', 'pantallaFacturacion', 'pos', 'registro', 'reportes',
            ]
        pantallas_raw = user.pantallas_asignadas.split(',') if user.pantallas_asignadas else []
        return [p.strip() for p in pantallas_raw if p.strip() and p.strip() != 'superAdmin']

    @staticmethod
    def _get_accesos(user):
        accesos = []
        if user.is_superadmin or AuthService._is_company_admin(user):
            sucursales = Sucursal.query.filter_by(empresa_id=user.empresa_id).all()
            rol_name = 'SuperAdmin' if user.is_superadmin else 'Administrador'
            for sucursal in sucursales:
                accesos.append({
                    'sucursal_id': sucursal.id,
                    'nombre': sucursal.nombre,
                    'rol': rol_name,
                })
            return accesos

        for access in getattr(user, 'accesos', []):
            if access.sucursal and access.rol:
                accesos.append({
                    'sucursal_id': access.sucursal_id,
                    'nombre': access.sucursal.nombre,
                    'rol': access.rol.nombre,
                })
        return accesos

    @staticmethod
    def _build_login_response(user, token):
        accesos = AuthService._get_accesos(user)
        if not accesos and not user.is_superadmin:
            raise AuthorizationError('Usuario sin acceso a sucursales. Contacte al administrador.')

        plan_info = get_plan_info(getattr(user.empresa, 'plan_tipo', None))

        return {
            'token': token,
            'user': {
                'id': user.id,
                'nombre': user.nombre,
                'email': user.email,
                'empresa': getattr(user.empresa, 'razon_social', None),
                'perfil': 'SuperAdmin' if user.is_superadmin else ('Emisor' if AuthService._is_company_admin(user) else 'Usuario'),
                'is_superadmin': user.is_superadmin,
                'pantallas': AuthService._get_pantallas(user),
                'plan_tipo': getattr(user.empresa, 'plan_tipo', None),
                'plan_label': plan_info['label'],
                'plan_cuota': getattr(user.empresa, 'plan_cuota', None),
                'plan_estado': getattr(user.empresa, 'plan_estado', None),
            },
            'accesos': accesos,
        }
