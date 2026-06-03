"""
API de SuperAdmin para MUROTECH
Sistema de administración supreme - Ojo de Dios
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

try:
    from .models import db, Empresa, Sucursal, Rol, Usuario, AccesoSucursal, RevokedToken, SuperAdminEmpresa
except ImportError:
    from models import db, Empresa, Sucursal, Rol, Usuario, AccesoSucursal, RevokedToken, SuperAdminEmpresa

supadmin_bp = Blueprint('supadmin', __name__, url_prefix='/api/supadmin')

# ==========================================
# DECORADORES DE AUTENTICACIÓN SUPERADMIN
# ==========================================

def superadmin_required(f):
    """Decorador que solo permite acceso a SuperAdmins"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request as flask_request
        token = None

        auth_header = flask_request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]

        if not token:
            return jsonify({'error': 'Token faltante', 'code': 'TOKEN_MISSING'}), 401

        try:
            import jwt
            from flask import current_app
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=[current_app.config.get('JWT_ALGORITHM', 'HS256')],
                audience=current_app.config.get('JWT_AUDIENCE', 'murotech-api'),
                issuer=current_app.config.get('JWT_ISSUER', 'murotech'),
                leeway=current_app.config.get('JWT_LEEWAY', 30),
                options={'require': ['exp', 'iat', 'aud', 'iss']},
            )

            # Verificar que es superadmin
            if not data.get('is_superadmin'):
                return jsonify({'error': 'Acceso denegado. Se requiere rol SuperAdmin', 'code': 'SUPERADMIN_REQUIRED'}), 403

            current_user = Usuario.query.get(data.get('user_id'))
            if not current_user or not current_user.is_superadmin:
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
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido', 'code': 'INVALID_TOKEN'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# ==========================================
# DASHBOARD DE SUPERADMIN
# ==========================================

@supadmin_bp.route('/dashboard', methods=['GET'])
@superadmin_required
def get_dashboard(current_user):
    """Retorna métricas globales del sistema"""
    try:
        # Consultas de ámbito filtradas
        empresa_query = Empresa.query
        usuario_query = Usuario.query
        sucursal_query = Sucursal.query
        
        if current_user.assigned_company_ids:
            empresa_query = empresa_query.filter(Empresa.id.in_(current_user.assigned_company_ids))
            usuario_query = usuario_query.filter(Usuario.empresa_id.in_(current_user.assigned_company_ids))
            sucursal_query = sucursal_query.filter(Sucursal.empresa_id.in_(current_user.assigned_company_ids))

        total_empresas = empresa_query.count()
        total_usuarios = usuario_query.count()
        total_sucursales = sucursal_query.count()
        total_admins = Usuario.query.filter_by(is_superadmin=True).count()
        
        # Usuarios activos vs inactivos de las empresas autorizadas
        usuarios_activos = usuario_query.filter_by(is_active=True).count()
        usuarios_inactivos = usuario_query.filter_by(is_active=False).count()
        
        # Empresas recientes (últimas 10)
        empresas_recientes = empresa_query.order_by(
            Empresa.fecha_creacion.desc()
        ).limit(10).all()
        
        # Últimos 10 usuarios creados
        usuarios_recientes = usuario_query.order_by(
            Usuario.id.desc()
        ).limit(10).all()
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_empresas': total_empresas,
                'total_usuarios': total_usuarios,
                'total_sucursales': total_sucursales,
                'total_superadmins': total_admins,
                'usuarios_activos': usuarios_activos,
                'usuarios_inactivos': usuarios_inactivos
            },
            'empresas_recientes': [{
                'id': e.id,
                'razon_social': e.razon_social,
                'cedula': e.cedula_juridica,
                'fecha_creacion': e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                'sucursales_count': len(e.sucursales)
            } for e in empresas_recientes],
            'usuarios_recientes': [{
                'id': u.id,
                'nombre': u.nombre,
                'email': u.email,
                'is_superadmin': u.is_superadmin,
                'is_active': u.is_active,
                'empresa_id': u.empresa_id
            } for u in usuarios_recientes]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'DASHBOARD_ERROR'}), 500

# ==========================================
# GESTIÓN DE EMPRESAS
# ==========================================

@supadmin_bp.route('/empresas', methods=['GET'])
@superadmin_required
def listar_empresas(current_user):
    """Lista todas las empresas con paginación"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Empresa.query
        
        if current_user.assigned_company_ids:
            query = query.filter(Empresa.id.in_(current_user.assigned_company_ids))
        
        if search:
            query = query.filter(
                db.or_(
                    Empresa.razon_social.ilike(f'%{search}%'),
                    Empresa.cedula_juridica.ilike(f'%{search}%'),
                    Empresa.email_contacto.ilike(f'%{search}%')
                )
            )
        
        pagination = query.order_by(Empresa.fecha_creacion.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'empresas': [{
                'id': e.id,
                'razon_social': e.razon_social,
                'nombre_comercial': e.nombre_comercial,
                'cedula_juridica': e.cedula_juridica,
                'email_contacto': e.email_contacto,
                'telefono': e.telefono,
                'actividad_economica': e.actividad_economica,
                'fecha_creacion': e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                'sucursales_count': len(e.sucursales),
                'usuarios_count': len(e.usuarios)
            } for e in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'LIST_EMPRESAS_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>', methods=['GET'])
@superadmin_required
def detalle_empresa(current_user, empresa_id):
    """Obtiene detalles de una empresa específica"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        empresa = Empresa.query.get(empresa_id)
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada', 'code': 'EMPRESA_NOT_FOUND'}), 404
        
        # Obtener sucursales
        sucursales = Sucursal.query.filter_by(empresa_id=empresa_id).all()
        
        # Obtener usuarios
        usuarios = Usuario.query.filter_by(empresa_id=empresa_id).all()
        
        return jsonify({
            'success': True,
            'empresa': {
                'id': empresa.id,
                'razon_social': empresa.razon_social,
                'nombre_comercial': empresa.nombre_comercial,
                'cedula_juridica': empresa.cedula_juridica,
                'tipo_identificacion': empresa.tipo_identificacion,
                'email_contacto': empresa.email_contacto,
                'telefono': empresa.telefono,
                'actividad_economica': empresa.actividad_economica,
                'regimen': empresa.regimen,
                'fecha_creacion': empresa.fecha_creacion.isoformat() if empresa.fecha_creacion else None,
                'api_configurada': bool(empresa.api_usuario)
            },
            'sucursales': [{
                'id': s.id,
                'nombre': s.nombre,
                'numero_sucursal': s.numero_sucursal,
                'terminal': s.terminal,
                'direccion': s.direccion
            } for s in sucursales],
            'usuarios': [{
                'id': u.id,
                'nombre': u.nombre,
                'email': u.email,
                'is_superadmin': u.is_superadmin,
                'is_active': u.is_active,
                'pantallas': u.pantallas_asignadas
            } for u in usuarios]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'EMPRESA_DETAIL_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>', methods=['DELETE'])
@superadmin_required
def eliminar_empresa(current_user, empresa_id):
    """Elimina una empresa y todos sus datos (CASCADE)"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        empresa = Empresa.query.get(empresa_id)
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada', 'code': 'EMPRESA_NOT_FOUND'}), 404
        
        # No permitir eliminar la empresa dummy del superadmin
        if empresa_id == '00000000-0000-0000-0000-000000000000':
            return jsonify({'error': 'No se puede eliminar la empresa del sistema', 'code': 'PROTECTED_EMPRESA'}), 400
        
        razon = request.args.get('razon', 'Eliminado por SuperAdmin')
        empresa_nombre = empresa.razon_social
        
        # Eliminar empresa (las relaciones se eliminan por CASCADE)
        db.session.delete(empresa)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Empresa "{empresa_nombre}" eliminada correctamente',
            'razon': razon
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'DELETE_EMPRESA_ERROR'}), 500

# ==========================================
# GESTIÓN DE USUARIOS (TODOS)
# ==========================================

@supadmin_bp.route('/usuarios', methods=['GET'])
@superadmin_required
def listar_usuarios(current_user):
    """Lista todos los usuarios del sistema"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        estado = request.args.get('estado', 'todos')  # activos, inactivos, todos
        rol = request.args.get('rol', 'todos')  # superadmin, admin, emisor, auditor, todos
        
        query = Usuario.query
        
        if current_user.assigned_company_ids:
            query = query.filter(Usuario.empresa_id.in_(current_user.assigned_company_ids))
        
        # Filtro por estado
        if estado == 'activos':
            query = query.filter_by(is_active=True)
        elif estado == 'inactivos':
            query = query.filter_by(is_active=False)
        
        # Filtro por rol
        if rol == 'superadmin':
            query = query.filter_by(is_superadmin=True)
        elif rol == 'admin':
            query = query.filter_by(is_superadmin=False)
            # Filtrar por usuarios con empresa_id no dummy
            query = query.filter(Usuario.empresa_id != '00000000-0000-0000-0000-000000000000')
        
        # Búsqueda
        if search:
            query = query.filter(
                db.or_(
                    Usuario.nombre.ilike(f'%{search}%'),
                    Usuario.email.ilike(f'%{search}%')
                )
            )
        
        pagination = query.order_by(Usuario.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'usuarios': [{
                'id': u.id,
                'nombre': u.nombre,
                'email': u.email,
                'is_superadmin': u.is_superadmin,
                'is_active': u.is_active,
                'empresa_id': u.empresa_id,
                'empresa_nombre': u.empresa.razon_social if u.empresa else 'N/A',
                'pantallas': u.pantallas_asignadas,
                'accesos': [{
                    'sucursal': a.sucursal.nombre if a.sucursal else 'N/A',
                    'rol': a.rol.nombre if a.rol else 'N/A'
                } for a in u.accesos]
            } for u in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'LIST_USUARIOS_ERROR'}), 500

def check_user_scoping(current_user, target_usuario):
    if current_user.assigned_company_ids:
        # SuperAdmins restringidos no pueden alterar a otros superadmins o usuarios de empresas no asignadas
        if target_usuario.is_superadmin or target_usuario.empresa_id not in current_user.assigned_company_ids:
            return False
    return True

@supadmin_bp.route('/usuarios/<usuario_id>', methods=['GET'])
@superadmin_required
def detalle_usuario(current_user, usuario_id):
    """Obtiene detalles de un usuario específico"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        return jsonify({
            'success': True,
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.email,
                'is_superadmin': usuario.is_superadmin,
                'is_active': usuario.is_active,
                'empresa_id': usuario.empresa_id,
                'empresa_nombre': usuario.empresa.razon_social if usuario.empresa else 'N/A',
                'pantallas_asignadas': usuario.pantallas_asignadas,
                'accesos': [{
                    'id': a.id,
                    'sucursal_id': a.sucursal_id,
                    'sucursal_nombre': a.sucursal.nombre if a.sucursal else 'N/A',
                    'rol_id': a.rol_id,
                    'rol_nombre': a.rol.nombre if a.rol else 'N/A'
                } for a in usuario.accesos]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'USUARIO_DETAIL_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/activar', methods=['PUT'])
@superadmin_required
def activar_usuario(current_user, usuario_id):
    """Activa un usuario inactivo"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        # No permitir desactivar al último superadmin
        if usuario.is_superadmin:
            superadmins_activos = Usuario.query.filter_by(
                is_superadmin=True, 
                is_active=True
            ).count()
            if superadmins_activos <= 1:
                return jsonify({'error': 'No se puede desactivar al último SuperAdmin', 'code': 'LAST_SUPERADMIN'}), 400
        
        usuario.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario "{usuario.nombre}" activado correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'ACTIVATE_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/desactivar', methods=['PUT'])
@superadmin_required
def desactivar_usuario(current_user, usuario_id):
    """Desactiva un usuario"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        # No permitir desactivar al propio usuario
        if usuario.id == current_user.id:
            return jsonify({'error': 'No puede desactivarse a sí mismo', 'code': 'SELF_DEACTIVATE'}), 400
        
        # No permitir desactivar al último superadmin
        if usuario.is_superadmin:
            superadmins_activos = Usuario.query.filter_by(
                is_superadmin=True, 
                is_active=True
            ).count()
            if superadmins_activos <= 1:
                return jsonify({'error': 'No se puede desactivar al último SuperAdmin', 'code': 'LAST_SUPERADMIN'}), 400
        
        usuario.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario "{usuario.nombre}" desactivado correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'DEACTIVATE_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>', methods=['DELETE'])
@superadmin_required
def eliminar_usuario(current_user, usuario_id):
    """Elimina un usuario"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        # No permitir eliminar al propio usuario
        if usuario.id == current_user.id:
            return jsonify({'error': 'No puede eliminarse a sí mismo', 'code': 'SELF_DELETE'}), 400
        
        # No permitir eliminar al último superadmin
        if usuario.is_superadmin:
            superadmins = Usuario.query.filter_by(is_superadmin=True).count()
            if superadmins <= 1:
                return jsonify({'error': 'No se puede eliminar al último SuperAdmin', 'code': 'LAST_SUPERADMIN'}), 400
        
        nombre = usuario.nombre
        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario "{nombre}" eliminado correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'DELETE_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/reset-password', methods=['PUT'])
@superadmin_required
def reset_password(current_user, usuario_id):
    """Resetea la contraseña de un usuario"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        nueva_password = request.get_json().get('nueva_password')
        if not nueva_password or len(nueva_password) < 8:
            return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres', 'code': 'WEAK_PASSWORD'}), 400
        
        usuario.set_password(nueva_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Contraseña de "{usuario.nombre}" reseteada correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'RESET_PASSWORD_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/promover', methods=['PUT'])
@superadmin_required
def promover_superadmin(current_user, usuario_id):
    """Promueve un usuario a SuperAdmin"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        if usuario.is_superadmin:
            return jsonify({'error': 'El usuario ya es SuperAdmin', 'code': 'ALREADY_SUPERADMIN'}), 400
        
        usuario.is_superadmin = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario "{usuario.nombre}" promovido a SuperAdmin'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'PROMOTE_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/degradar', methods=['PUT'])
@superadmin_required
def degradar_superadmin(current_user, usuario_id):
    """Degrada un SuperAdmin a usuario normal"""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado', 'code': 'USUARIO_NOT_FOUND'}), 404
        
        if not check_user_scoping(current_user, usuario):
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre este usuario.', 'code': 'ACCESS_DENIED'}), 403

        if not usuario.is_superadmin:
            return jsonify({'error': 'El usuario no es SuperAdmin', 'code': 'NOT_SUPERADMIN'}), 400
        
        # No permitir degradar al último superadmin
        superadmins = Usuario.query.filter_by(is_superadmin=True).count()
        if superadmins <= 1:
            return jsonify({'error': 'No se puede degradar al último SuperAdmin', 'code': 'LAST_SUPERADMIN'}), 400
        
        # No permitir degradarse a sí mismo
        if usuario.id == current_user.id:
            return jsonify({'error': 'No puede degradarse a sí mismo', 'code': 'SELF_DEGRADE'}), 400
        
        usuario.is_superadmin = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'SuperAdmin "{usuario.nombre}" degradado a usuario normal'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'DEGRADE_ERROR'}), 500

# ==========================================
# GESTIÓN DE ROLES
# ==========================================

@supadmin_bp.route('/roles', methods=['GET'])
@superadmin_required
def listar_roles(current_user):
    """Lista todos los roles del sistema"""
    try:
        roles = Rol.query.all()
        return jsonify({
            'success': True,
            'roles': [{
                'id': r.id,
                'nombre': r.nombre,
                'descripcion': r.descripcion,
                'usuarios_count': len(r.accesos)
            } for r in roles]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'LIST_ROLES_ERROR'}), 500

# ==========================================
# ESTADÍSTICAS Y REPORTES
# ==========================================

@supadmin_bp.route('/stats/usuarios', methods=['GET'])
@superadmin_required
def stats_usuarios(current_user):
    """Estadísticas de usuarios"""
    try:
        total = Usuario.query.count()
        activos = Usuario.query.filter_by(is_active=True).count()
        inactivos = Usuario.query.filter_by(is_active=False).count()
        superadmins = Usuario.query.filter_by(is_superadmin=True).count()
        
        # Por día (últimos 30 días)
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        treinta_dias = datetime.utcnow() - timedelta(days=30)
        nuevos = Usuario.query.filter(Usuario.id >= treinta_dias).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'activos': activos,
                'inactivos': inactivos,
                'superadmins': superadmins,
                'nuevos_30_dias': nuevos
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'STATS_ERROR'}), 500

@supadmin_bp.route('/stats/empresas', methods=['GET'])
@superadmin_required
def stats_empresas(current_user):
    """Estadísticas de empresas"""
    try:
        total = Empresa.query.count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'STATS_ERROR'}), 500

# ==========================================
# REGISTRO DE ACCIONES (AUDITORÍA)
# ==========================================

@supadmin_bp.route('/audit-log', methods=['GET'])
@superadmin_required
def audit_log(current_user):
    """Registro de acciones del SuperAdmin"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        accion = request.args.get('accion', '')
        
        # Aquí se podría implementar un modelo de auditoría
        # Por ahora retornamos un log básico
        
        return jsonify({
            'success': True,
            'message': 'Sistema de auditoría en desarrollo',
            'logs': []
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'AUDIT_ERROR'}), 500

# ==========================================
# MANTENIMIENTO DE EMISORES Y SUCURSALES (1a)
# ==========================================

@supadmin_bp.route('/empresas', methods=['POST'])
@superadmin_required
def crear_empresa(current_user):
    """Crea un nuevo emisor (Empresa) y su primer usuario Administrador"""
    try:
        data = request.get_json() or {}
        cedula = data.get('cedula_juridica')
        razon_social = data.get('razon_social')
        email_contacto = data.get('email_contacto')
        password = data.get('password')
        
        if not cedula or not razon_social or not email_contacto or not password:
            return jsonify({'error': 'Cédula jurídica, Razón Social, Email de contacto y Contraseña son requeridos', 'code': 'MISSING_FIELDS'}), 400
            
        if Empresa.query.filter_by(cedula_juridica=cedula).first():
            return jsonify({'error': 'La empresa con esta cédula ya existe', 'code': 'EMPRESA_EXISTS'}), 400
            
        if Usuario.query.filter_by(email=email_contacto).first():
            return jsonify({'error': 'El correo electrónico ya está en uso', 'code': 'EMAIL_EXISTS'}), 400

        # Crear empresa
        nueva_empresa = Empresa(
            razon_social=razon_social,
            nombre_comercial=data.get('nombre_comercial', razon_social),
            cedula_juridica=cedula,
            tipo_identificacion=data.get('tipo_identificacion', '02'),
            actividad_economica=data.get('actividad_economica'),
            regimen=data.get('regimen', 'General'),
            email_contacto=email_contacto,
            telefono=data.get('telefono'),
            api_usuario=data.get('api_usuario'),
            api_password=data.get('api_password'),
            api_pin_p12=data.get('api_pin'),
            plan_tipo=data.get('plan_tipo', 'mensual'),
            plan_cuota=int(data.get('plan_cuota', 500)),
            plan_estado='activo',
            is_active=True
        )
        db.session.add(nueva_empresa)
        db.session.flush()

        # Crear sucursal principal
        sucursal = Sucursal(
            empresa_id=nueva_empresa.id,
            numero_sucursal=data.get('api_sucursal', '001'),
            terminal=data.get('api_terminal', '00001'),
            nombre="Sede Principal",
            direccion=data.get('direccion', 'San José, Costa Rica')
        )
        db.session.add(sucursal)
        db.session.flush()

        # Crear usuario Administrador (Emisor)
        nuevo_usuario = Usuario(
            empresa_id=nueva_empresa.id,
            nombre=data.get('nombre_admin', 'Administrador Principal'),
            email=email_contacto,
            is_superadmin=False,
            is_active=True,
            pantallas_asignadas="auditoria,clientes,configuracion,cotizaciones,editarFactura,inventario,notificaciones,panelControl,pantallaFacturacion,pos,registro,reportes"
        )
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)
        db.session.flush()

        # Asignar acceso sucursal
        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        if not rol_admin:
            rol_admin = Rol(nombre='Administrador', descripcion='Control total de la sucursal/empresa')
            db.session.add(rol_admin)
            db.session.flush()
            
        acceso = AccesoSucursal(
            usuario_id=nuevo_usuario.id,
            sucursal_id=sucursal.id,
            rol_id=rol_admin.id
        )
        db.session.add(acceso)
        
        # Vincular automáticamente al creador si está restringido
        if current_user.assigned_company_ids:
            vinculo = SuperAdminEmpresa(superadmin_id=current_user.id, empresa_id=nueva_empresa.id)
            db.session.add(vinculo)
            current_user.assigned_company_ids.append(nueva_empresa.id)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Empresa y usuario administrador creados exitosamente',
            'empresa_id': nueva_empresa.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'CREATE_EMPRESA_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>', methods=['PUT'])
@superadmin_required
def actualizar_empresa(current_user, empresa_id):
    """Actualiza datos de un emisor (Empresa)"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        empresa = Empresa.query.get(empresa_id)
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada', 'code': 'EMPRESA_NOT_FOUND'}), 404
            
        data = request.get_json() or {}
        empresa.razon_social = data.get('razon_social', empresa.razon_social)
        empresa.nombre_comercial = data.get('nombre_comercial', empresa.nombre_comercial)
        empresa.tipo_identificacion = data.get('tipo_identificacion', empresa.tipo_identificacion)
        empresa.actividad_economica = data.get('actividad_economica', empresa.actividad_economica)
        empresa.regimen = data.get('regimen', empresa.regimen)
        empresa.email_contacto = data.get('email_contacto', empresa.email_contacto)
        empresa.telefono = data.get('telefono', empresa.telefono)
        empresa.plan_tipo = data.get('plan_tipo', empresa.plan_tipo)
        empresa.plan_cuota = int(data.get('plan_cuota', empresa.plan_cuota))
        empresa.plan_estado = data.get('plan_estado', empresa.plan_estado)
        empresa.is_active = data.get('is_active', empresa.is_active)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Empresa actualizada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'UPDATE_EMPRESA_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>/sucursales', methods=['GET'])
@superadmin_required
def listar_sucursales_emisor(current_user, empresa_id):
    """Lista las sucursales de un emisor específico"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        sucursales = Sucursal.query.filter_by(empresa_id=empresa_id).all()
        return jsonify({
            'success': True,
            'sucursales': [{
                'id': s.id,
                'nombre': s.nombre,
                'numero_sucursal': s.numero_sucursal,
                'terminal': s.terminal,
                'direccion': s.direccion,
                'provincia': s.provincia,
                'canton': s.canton,
                'distrito': s.distrito,
                'barrio': s.barrio,
                'otras_senas': s.otras_senas,
                'c_factura': s.c_factura,
                'c_tiquete': s.c_tiquete,
                'c_nota_credito': s.c_nota_credito,
                'c_nota_debito': s.c_nota_debito
            } for s in sucursales]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'LIST_SUCURSALES_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>/sucursales', methods=['POST'])
@superadmin_required
def crear_sucursal_emisor(current_user, empresa_id):
    """Crea una nueva sucursal para un emisor específico"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        data = request.get_json() or {}
        nombre = data.get('nombre')
        numero = data.get('numero_sucursal')
        terminal = data.get('terminal', '00001')
        
        if not nombre or not numero:
            return jsonify({'error': 'Nombre y número de sucursal son obligatorios', 'code': 'MISSING_FIELDS'}), 400
            
        nueva = Sucursal(
            empresa_id=empresa_id,
            nombre=nombre,
            numero_sucursal=numero,
            terminal=terminal,
            direccion=data.get('direccion'),
            provincia=data.get('provincia', '1'),
            canton=data.get('canton', '01'),
            distrito=data.get('distrito', '01'),
            barrio=data.get('barrio', '01'),
            otras_senas=data.get('otras_senas'),
            c_factura=int(data.get('c_factura', 0)),
            c_tiquete=int(data.get('c_tiquete', 0)),
            c_nota_credito=int(data.get('c_nota_credito', 0)),
            c_nota_debito=int(data.get('c_nota_debito', 0))
        )
        db.session.add(nueva)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sucursal creada exitosamente', 'sucursal_id': nueva.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'CREATE_SUCURSAL_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>/sucursales/<sucursal_id>', methods=['PUT'])
@superadmin_required
def actualizar_sucursal_emisor(current_user, empresa_id, sucursal_id):
    """Actualiza datos de una sucursal específica"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        sucursal = Sucursal.query.filter_by(id=sucursal_id, empresa_id=empresa_id).first()
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada', 'code': 'SUCURSAL_NOT_FOUND'}), 404
            
        data = request.get_json() or {}
        sucursal.nombre = data.get('nombre', sucursal.nombre)
        sucursal.numero_sucursal = data.get('numero_sucursal', sucursal.numero_sucursal)
        sucursal.terminal = data.get('terminal', sucursal.terminal)
        sucursal.direccion = data.get('direccion', sucursal.direccion)
        sucursal.provincia = data.get('provincia', sucursal.provincia)
        sucursal.canton = data.get('canton', sucursal.canton)
        sucursal.distrito = data.get('distrito', sucursal.distrito)
        sucursal.barrio = data.get('barrio', sucursal.barrio)
        sucursal.otras_senas = data.get('otras_senas', sucursal.otras_senas)
        sucursal.c_factura = int(data.get('c_factura', sucursal.c_factura))
        sucursal.c_tiquete = int(data.get('c_tiquete', sucursal.c_tiquete))
        sucursal.c_nota_credito = int(data.get('c_nota_credito', sucursal.c_nota_credito))
        sucursal.c_nota_debito = int(data.get('c_nota_debito', sucursal.c_nota_debito))
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sucursal actualizada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'UPDATE_SUCURSAL_ERROR'}), 500

@supadmin_bp.route('/empresas/<empresa_id>/sucursales/<sucursal_id>', methods=['DELETE'])
@superadmin_required
def eliminar_sucursal_emisor(current_user, empresa_id, sucursal_id):
    """Elimina una sucursal específica"""
    try:
        if current_user.assigned_company_ids and empresa_id not in current_user.assigned_company_ids:
            return jsonify({'error': 'Acceso denegado. No tiene permisos sobre esta empresa.', 'code': 'ACCESS_DENIED'}), 403

        sucursal = Sucursal.query.filter_by(id=sucursal_id, empresa_id=empresa_id).first()
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada', 'code': 'SUCURSAL_NOT_FOUND'}), 404
            
        db.session.delete(sucursal)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sucursal eliminada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'DELETE_SUCURSAL_ERROR'}), 500

# ==========================================
# GESTIÓN DE SUPER ADMINS Y ASIGNACIÓN (1c)
# ==========================================

@supadmin_bp.route('/usuarios', methods=['POST'])
@superadmin_required
def crear_superadmin(current_user):
    """Crea un nuevo usuario con rol SuperAdmin (Global o Restringido)"""
    try:
        if current_user.assigned_company_ids:
            return jsonify({'error': 'Solo un SuperAdmin global puede crear otros SuperAdmins', 'code': 'UNAUTHORIZED'}), 403
            
        data = request.get_json() or {}
        nombre = data.get('nombre')
        email = data.get('email')
        password = data.get('password')
        
        if not nombre or not email or not password:
            return jsonify({'error': 'Nombre, Email y Contraseña son obligatorios', 'code': 'MISSING_FIELDS'}), 400
            
        if Usuario.query.filter_by(email=email).first():
            return jsonify({'error': 'El correo electrónico ya está registrado', 'code': 'EMAIL_EXISTS'}), 400
            
        # Crear usuario SuperAdmin (vinculado a la empresa dummy '00000000-0000-0000-0000-000000000000')
        nuevo = Usuario(
            empresa_id='00000000-0000-0000-0000-000000000000',
            nombre=nombre,
            email=email,
            is_superadmin=True,
            is_active=True,
            pantallas_asignadas='superAdmin'
        )
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Usuario SuperAdmin creado exitosamente', 'usuario_id': nuevo.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'CREATE_SUPERADMIN_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/asignar', methods=['POST'])
@superadmin_required
def asignar_empresas_superadmin(current_user, usuario_id):
    """Asigna una lista de empresas a un SuperAdmin específico"""
    try:
        if current_user.assigned_company_ids:
            return jsonify({'error': 'Solo un SuperAdmin global puede gestionar asignaciones', 'code': 'UNAUTHORIZED'}), 403

        target_user = Usuario.query.get(usuario_id)
        if not target_user or not target_user.is_superadmin:
            return jsonify({'error': 'El usuario destino debe ser un SuperAdmin', 'code': 'INVALID_TARGET_USER'}), 400
            
        data = request.get_json() or {}
        empresa_ids = data.get('empresa_ids', [])
        
        if not isinstance(empresa_ids, list):
            return jsonify({'error': 'empresa_ids debe ser una lista', 'code': 'INVALID_FORMAT'}), 400
            
        agregados = 0
        for emp_id in empresa_ids:
            empresa = Empresa.query.get(emp_id)
            if empresa:
                existente = SuperAdminEmpresa.query.filter_by(superadmin_id=usuario_id, empresa_id=emp_id).first()
                if not existente:
                    vinculo = SuperAdminEmpresa(superadmin_id=usuario_id, empresa_id=emp_id)
                    db.session.add(vinculo)
                    agregados += 1
                    
        db.session.commit()
        return jsonify({'success': True, 'message': f'Se asignaron {agregados} empresas al SuperAdmin'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'ASSIGN_EMPRESAS_ERROR'}), 500

@supadmin_bp.route('/usuarios/<usuario_id>/asignar/<empresa_id>', methods=['DELETE'])
@superadmin_required
def remover_empresa_superadmin(current_user, usuario_id, empresa_id):
    """Remueve la asignación de una empresa a un SuperAdmin específico"""
    try:
        if current_user.assigned_company_ids:
            return jsonify({'error': 'Solo un SuperAdmin global puede gestionar asignaciones', 'code': 'UNAUTHORIZED'}), 403

        vinculo = SuperAdminEmpresa.query.filter_by(superadmin_id=usuario_id, empresa_id=empresa_id).first()
        if not vinculo:
            return jsonify({'error': 'Asignación no encontrada', 'code': 'ASSIGNMENT_NOT_FOUND'}), 404
            
        db.session.delete(vinculo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignación removida correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'code': 'REMOVE_ASSIGNMENT_ERROR'}), 500

# ==========================================
# REPORTES MULTIDIMENSIONALES (1b)
# ==========================================

@supadmin_bp.route('/reportes', methods=['GET'])
@superadmin_required
def generar_reporte_supadmin(current_user):
    """Genera datos agregados para reportes tributarios y comerciales de emisores"""
    try:
        empresa_id = request.args.get('empresa_id')
        sucursal_id = request.args.get('sucursal_id')
        periodo = request.args.get('periodo', 'mes').lower()
        start_str = request.args.get('start_date')
        end_str = request.args.get('end_date')
        
        from api.models import Factura
        query = Factura.query.join(Sucursal).filter(Factura.is_draft == False)
        
        # Filtro de ámbito general
        if current_user.assigned_company_ids:
            query = query.filter(Sucursal.empresa_id.in_(current_user.assigned_company_ids))
            if empresa_id and empresa_id not in current_user.assigned_company_ids:
                return jsonify({'error': 'Acceso denegado a esta empresa', 'code': 'ACCESS_DENIED'}), 403
        
        if empresa_id:
            query = query.filter(Sucursal.empresa_id == empresa_id)
        if sucursal_id:
            query = query.filter(Factura.sucursal_id == sucursal_id)
            
        # Filtros de fecha
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                query = query.filter(Factura.fecha_emision >= start_date)
            except ValueError:
                pass
        if end_str:
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                query = query.filter(Factura.fecha_emision <= end_date)
            except ValueError:
                pass
                
        facturas = query.all()
        reporte_data = {}
        
        for f in facturas:
            dt = f.fecha_emision
            if periodo == 'hora':
                key = dt.strftime("%Y-%m-%d %H:00")
            elif periodo == 'dia' or periodo == 'fecha':
                key = dt.strftime("%Y-%m-%d")
            elif periodo == 'mes':
                key = dt.strftime("%Y-%m")
            elif periodo == 'ano':
                key = dt.strftime("%Y")
            elif periodo == 'bimestre':
                b = (dt.month - 1) // 2 + 1
                key = f"{dt.year}-B{b}"
            elif periodo == 'trimestre':
                t = (dt.month - 1) // 3 + 1
                key = f"{dt.year}-T{t}"
            elif periodo == 'semestre':
                s = 1 if dt.month <= 6 else 2
                key = f"{dt.year}-S{s}"
            else:
                key = dt.strftime("%Y-%m")
                
            if key not in reporte_data:
                reporte_data[key] = {
                    'cantidad_documentos': 0,
                    'subtotal': 0.0,
                    'impuestos': 0.0,
                    'descuentos': 0.0,
                    'total': 0.0
                }
                
            reporte_data[key]['cantidad_documentos'] += 1
            reporte_data[key]['subtotal'] += float(f.subtotal or 0.0)
            reporte_data[key]['impuestos'] += float(f.impuestos or 0.0)
            reporte_data[key]['descuentos'] += float(f.descuentos or 0.0)
            reporte_data[key]['total'] += float(f.total or 0.0)
            
        sorted_report = []
        for k in sorted(reporte_data.keys()):
            item = reporte_data[k]
            item['periodo'] = k
            sorted_report.append(item)
            
        return jsonify({
            'success': True,
            'filtros': {
                'empresa_id': empresa_id,
                'sucursal_id': sucursal_id,
                'periodo': periodo,
                'start_date': start_str,
                'end_date': end_str
            },
            'datos': sorted_report
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'REPORT_GENERATION_ERROR'}), 500

@supadmin_bp.route('/reportes/descargar', methods=['GET'])
@superadmin_required
def descargar_reporte_csv(current_user):
    """Genera y descarga un reporte en formato CSV (compatible con Excel)"""
    try:
        empresa_id = request.args.get('empresa_id')
        sucursal_id = request.args.get('sucursal_id')
        periodo = request.args.get('periodo', 'mes').lower()
        start_str = request.args.get('start_date')
        end_str = request.args.get('end_date')
        
        from api.models import Factura
        query = Factura.query.join(Sucursal).filter(Factura.is_draft == False)
        
        if current_user.assigned_company_ids:
            query = query.filter(Sucursal.empresa_id.in_(current_user.assigned_company_ids))
            if empresa_id and empresa_id not in current_user.assigned_company_ids:
                return jsonify({'error': 'Acceso denegado'}), 403
                
        if empresa_id:
            query = query.filter(Sucursal.empresa_id == empresa_id)
        if sucursal_id:
            query = query.filter(Factura.sucursal_id == sucursal_id)
            
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                query = query.filter(Factura.fecha_emision >= start_date)
            except ValueError:
                pass
        if end_str:
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                query = query.filter(Factura.fecha_emision <= end_date)
            except ValueError:
                pass
                
        facturas = query.all()
        reporte_data = {}
        
        for f in facturas:
            dt = f.fecha_emision
            if periodo == 'hora':
                key = dt.strftime("%Y-%m-%d %H:00")
            elif periodo == 'dia' or periodo == 'fecha':
                key = dt.strftime("%Y-%m-%d")
            elif periodo == 'mes':
                key = dt.strftime("%Y-%m")
            elif periodo == 'ano':
                key = dt.strftime("%Y")
            elif periodo == 'bimestre':
                b = (dt.month - 1) // 2 + 1
                key = f"{dt.year}-B{b}"
            elif periodo == 'trimestre':
                t = (dt.month - 1) // 3 + 1
                key = f"{dt.year}-T{t}"
            elif periodo == 'semestre':
                s = 1 if dt.month <= 6 else 2
                key = f"{dt.year}-S{s}"
            else:
                key = dt.strftime("%Y-%m")
                
            if key not in reporte_data:
                reporte_data[key] = {
                    'cantidad_documentos': 0,
                    'subtotal': 0.0,
                    'impuestos': 0.0,
                    'descuentos': 0.0,
                    'total': 0.0
                }
                
            reporte_data[key]['cantidad_documentos'] += 1
            reporte_data[key]['subtotal'] += float(f.subtotal or 0.0)
            reporte_data[key]['impuestos'] += float(f.impuestos or 0.0)
            reporte_data[key]['descuentos'] += float(f.descuentos or 0.0)
            reporte_data[key]['total'] += float(f.total or 0.0)
            
        import io
        import csv
        output = io.StringIO()
        output.write(u'\ufeff') # UTF-8 BOM
        
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Periodo ({})'.format(periodo.capitalize()), 'Cantidad de Documentos', 'Subtotal', 'Impuestos', 'Descuentos', 'Total'])
        
        for k in sorted(reporte_data.keys()):
            item = reporte_data[k]
            writer.writerow([
                k,
                item['cantidad_documentos'],
                "{:.2f}".format(item['subtotal']),
                "{:.2f}".format(item['impuestos']),
                "{:.2f}".format(item['descuentos']),
                "{:.2f}".format(item['total'])
            ])
            
        from flask import Response
        res = Response(output.getvalue(), mimetype='text/csv')
        res.headers["Content-Disposition"] = "attachment; filename=reporte_tributario_{}.csv".format(periodo)
        return res
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'DOWNLOAD_REPORT_ERROR'}), 500

# Registrar el blueprint en app.py
def register_supadmin_routes(app):
    """Registra las rutas de SuperAdmin en la aplicación Flask"""
    app.register_blueprint(supadmin_bp)