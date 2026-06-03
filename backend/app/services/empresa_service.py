import os
from flask import current_app
from app.extensions import db
from app.models import Empresa, Sucursal, Usuario, Rol, AccesoSucursal, Notificacion
from app.services.auditoria_service import AuditoriaService
from app.utils.crypto import decrypt_text, encrypt_text
from app.utils.date_utils import _parse_date
from app.utils.money import _parse_int
from app.utils.validators import ValidationError
from fiscal.signer import encrypt_p12_data, decrypt_p12_data


class EmpresaService:
    @staticmethod
    def validate_sucursal(current_user, sucursal_id):
        if not sucursal_id:
            return None
        return Sucursal.query.filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()

    @staticmethod
    def list_sucursales(current_user):
        sucursales = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()
        return [
            {
                'id': s.id,
                'nombre': s.nombre,
                'numero_sucursal': s.numero_sucursal,
                'direccion': s.direccion,
                'terminal': s.terminal,
            }
            for s in sucursales
        ]

    @staticmethod
    def create_sucursal(current_user, data):
        if not data.get('nombre') or not data.get('numero_sucursal'):
            raise ValidationError('Nombre y número de sucursal son requeridos.')

        nueva = Sucursal(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            numero_sucursal=data.get('numero_sucursal'),
            direccion=data.get('direccion'),
            terminal=data.get('terminal'),
        )
        db.session.add(nueva)
        db.session.commit()
        return {
            'message': 'Sucursal creada.',
            'sucursal': {
                'id': nueva.id,
                'nombre': nueva.nombre,
                'numero_sucursal': nueva.numero_sucursal,
                'direccion': nueva.direccion,
                'terminal': nueva.terminal,
            },
        }

    @staticmethod
    def create_notification(empresa_id, tipo, titulo, descripcion, link=None):
        notif = Notificacion(
            empresa_id=empresa_id,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            link=link,
        )
        db.session.add(notif)
        return notif

    @staticmethod
    def get_empresa_config(empresa):
        suc = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        return {
            'razon_social': empresa.razon_social,
            'nombre_comercial': empresa.nombre_comercial,
            'cedula': empresa.cedula_juridica,
            'correo_hacienda': empresa.email_contacto,
            'telefono': empresa.telefono,
            'actividad': empresa.actividad_economica,
            'direccion': suc.direccion if suc else '',
        }

    @staticmethod
    def update_empresa_config(current_user, data):
        empresa = Empresa.query.get(current_user.empresa_id)
        if not empresa:
            raise ValidationError('Empresa no encontrada.')

        antes = AuditoriaService.snapshot_empresa(empresa)
        empresa.razon_social = data.get('razon_social', empresa.razon_social)
        empresa.nombre_comercial = data.get('nombre_comercial', empresa.nombre_comercial)
        empresa.email_contacto = data.get('correo_hacienda', empresa.email_contacto)
        empresa.telefono = data.get('telefono', empresa.telefono)
        empresa.actividad_economica = data.get('actividad', empresa.actividad_economica)

        sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        if sucursal:
            sucursal.direccion = data.get('direccion', sucursal.direccion)

        db.session.commit()
        AuditoriaService.log_change(
            usuario_id=current_user.id,
            entidad='empresa',
            accion='UPDATE',
            valores_antes=antes,
            valores_despues=AuditoriaService.snapshot_empresa(empresa),
            entidad_id=empresa.id,
        )
        EmpresaService.create_notification(
            current_user.empresa_id,
            'sistema',
            'Datos de Empresa Actualizados',
            'Se han modificado los datos comerciales de la empresa.',
        )
        return {'message': 'Datos de empresa actualizados correctamente.'}

    @staticmethod
    def get_facturacion_config(empresa):
        sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        return {
            'api_user': empresa.api_usuario,
            'sucursal_num': sucursal.numero_sucursal if sucursal else '001',
            'terminal_num': sucursal.terminal if sucursal else '00001',
            'ambiente': EmpresaService.get_hacienda_environment(empresa),
        }

    @staticmethod
    def update_facturacion_config(current_user, data):
        empresa = Empresa.query.get(current_user.empresa_id)
        if not empresa:
            raise ValidationError('Empresa no encontrada.')

        antes = AuditoriaService.snapshot_empresa(empresa)
        empresa.api_usuario = data.get('api_user', empresa.api_usuario)
        if data.get('api_pass'):
            EmpresaService.store_secret(empresa, 'api_password', data.get('api_pass'))
        if data.get('api_pin'):
            EmpresaService.store_secret(empresa, 'api_pin_p12', data.get('api_pin'))

        nuevo_ambiente = (data.get('ambiente') or '').lower()
        if nuevo_ambiente in ('stag', 'prod', 'produccion', 'production'):
            empresa.ambiente_hacienda = 'prod' if nuevo_ambiente in ('prod', 'produccion', 'production') else 'stag'

        db.session.commit()
        AuditoriaService.log_change(
            usuario_id=current_user.id,
            entidad='empresa_facturacion',
            accion='UPDATE',
            valores_antes=antes,
            valores_despues=AuditoriaService.snapshot_empresa(empresa),
            entidad_id=empresa.id,
        )
        return {
            'message': 'Configuración de facturación actualizada.',
            'ambiente': EmpresaService.get_hacienda_environment(empresa),
        }

    @staticmethod
    def get_plan_config(empresa):
        return {
            'plan_tipo': empresa.plan_tipo,
            'plan_cuota': empresa.plan_cuota,
            'plan_estado': empresa.plan_estado,
            'plan_inicio': empresa.plan_inicio.isoformat() if empresa.plan_inicio else None,
            'plan_vencimiento': empresa.plan_vencimiento.isoformat() if empresa.plan_vencimiento else None,
        }

    @staticmethod
    def update_plan_config(current_user, data):
        empresa = Empresa.query.get(current_user.empresa_id)
        if not empresa:
            raise ValidationError('Empresa no encontrada.')

        empresa.plan_tipo = data.get('plan_tipo', empresa.plan_tipo)
        empresa.plan_cuota = _parse_int(data.get('plan_cuota', empresa.plan_cuota), empresa.plan_cuota)
        empresa.plan_vencimiento = _parse_date(data.get('plan_vencimiento')) or empresa.plan_vencimiento
        empresa.plan_estado = data.get('plan_estado', empresa.plan_estado)
        db.session.commit()
        return {'message': 'Plan de facturación actualizado correctamente.'}

    @staticmethod
    def suspend_plan(current_user, motivo='Plan vencido o bloqueado'):
        empresa = Empresa.query.get(current_user.empresa_id)
        if not empresa:
            raise ValidationError('Empresa no encontrada.')

        EmpresaService.suspend_empresa(empresa, motivo=motivo)
        db.session.commit()
        return {'message': 'Plan suspendido y usuarios desactivados.'}

    @staticmethod
    def reactivate_empresa(current_user, motivo='Reactivación por administrador'):
        empresa = Empresa.query.get(current_user.empresa_id)
        if not empresa:
            raise ValidationError('Empresa no encontrada.')

        empresa.plan_estado = 'activo'
        empresa.is_active = True
        for usuario in empresa.usuarios:
            usuario.is_active = True

        EmpresaService.create_notification(
            empresa.id,
            'pago',
            'Cuenta reactivada',
            f'La cuenta fue reactivada: {motivo}',
        )
        db.session.commit()
        return {'message': 'Plan reactivado y usuarios activados.'}

    @staticmethod
    def get_unread_notifications_count(current_user):
        return Notificacion.query.filter_by(empresa_id=current_user.empresa_id, leida=False).count()

    @staticmethod
    def get_notifications(current_user, sucursal_id):
        sucursal = EmpresaService.validate_sucursal(current_user, sucursal_id)
        if not sucursal:
            raise ValidationError('Sucursal no encontrada o no tiene acceso.')

        notificaciones = Notificacion.query.filter(
            Notificacion.empresa_id == current_user.empresa_id,
            db.or_(Notificacion.sucursal_id == None, Notificacion.sucursal_id == sucursal.id)
        ).order_by(Notificacion.fecha.desc()).limit(50).all()

        return [
            {
                'id': n.id,
                'type': n.tipo,
                'icon': n.icono,
                'title': n.titulo,
                'desc': n.descripcion,
                'time': n.fecha.isoformat(),
                'read': n.leida,
            }
            for n in notificaciones
        ]

    @staticmethod
    def mark_notification_read(current_user, notification_id):
        notificacion = Notificacion.query.filter_by(id=notification_id, empresa_id=current_user.empresa_id).first()
        if not notificacion:
            raise ValidationError('Notificación no encontrada')

        notificacion.leida = True
        db.session.commit()
        return {'message': 'Notificación marcada como leída'}

    @staticmethod
    def mark_all_notifications_read(current_user, sucursal_id=None):
        query = Notificacion.query.filter_by(empresa_id=current_user.empresa_id, leida=False)
        if sucursal_id is not None:
            query = query.filter(db.or_(Notificacion.sucursal_id == None, Notificacion.sucursal_id == sucursal_id))
        query.update({Notificacion.leida: True})
        db.session.commit()
        return {'message': 'Todas las notificaciones marcadas como leídas'}

    @staticmethod
    def get_hacienda_environment(empresa):
        ambiente = (
            getattr(empresa, 'ambiente_hacienda', None)
            or os.environ.get('HACIENDA_AMBIENTE', 'stag')
        ).lower()
        return 'prod' if ambiente in ('prod', 'produccion', 'production') else 'stag'

    @staticmethod
    def store_secret(empresa, field_name: str, plain_value: str):
        if not plain_value:
            return
        enc = encrypt_text(plain_value, current_app.config.get('ENCRYPTION_KEY'))
        setattr(empresa, field_name, enc)

    @staticmethod
    def _p12_encryption_key():
        return current_app.config.get('ENCRYPTION_KEY')

    @staticmethod
    def encrypt_p12_data(raw_p12):
        return encrypt_p12_data(raw_p12, EmpresaService._p12_encryption_key())

    @staticmethod
    def decrypt_p12_data(p12_data):
        return decrypt_p12_data(p12_data, EmpresaService._p12_encryption_key())

    @staticmethod
    def read_secret(empresa, field_name: str) -> str:
        raw = getattr(empresa, field_name, None) or ''
        try:
            return decrypt_text(raw, current_app.config.get('ENCRYPTION_KEY'))
        except ValueError:
            return raw

    @staticmethod
    def suspend_empresa(empresa, motivo='Plan vencido o bloqueado'):
        empresa.plan_estado = 'suspendido'
        empresa.is_active = False
        for usuario in empresa.usuarios:
            usuario.is_active = False
        EmpresaService.create_notification(
            empresa.id,
            'pago',
            'Cuenta suspendida',
            f'La cuenta fue suspendida: {motivo}',
        )

    @staticmethod
    def list_users(empresa_id):
        usuarios = Usuario.query.filter_by(empresa_id=empresa_id).all()
        result = []
        for u in usuarios:
            result.append({
                'id': u.id,
                'nombre': u.nombre,
                'email': u.email,
                'activo': u.is_active,
                'is_superadmin': u.is_superadmin,
                'pantallas': u.pantallas_asignadas.split(',') if u.pantallas_asignadas else [],
                'accesos': [{'sucursal': a.sucursal.nombre, 'rol': a.rol.nombre} for a in u.accesos],
            })
        return result

    @staticmethod
    def create_user(current_user, data):
        if not data.get('email') or not data.get('password') or not data.get('nombre'):
            raise ValidationError('Email, nombre y contraseña son requeridos.')

        if Usuario.query.filter_by(email=data.get('email')).first():
            raise ValidationError('Email ya en uso.')

        sucursal_id = data.get('sucursal_id')
        if sucursal_id:
            sucursal = Sucursal.query.filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()
            if not sucursal:
                raise ValidationError('Sucursal inválida.')
        else:
            sucursal = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).first()
            if not sucursal:
                raise ValidationError('No hay sucursales configuradas. Contacte al administrador.')

        pantallas_raw = data.get('pantallas', ['facturacion', 'inventario'])
        pantallas_filtradas = [p for p in pantallas_raw if p not in ['superAdmin']]

        nuevo_user = Usuario(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            email=data.get('email'),
            is_superadmin=False,
            pantallas_asignadas=','.join(pantallas_filtradas),
            is_active=True,
        )
        nuevo_user.set_password(data.get('password'))
        db.session.add(nuevo_user)
        db.session.flush()

        rol_nombre = data.get('rol', 'Emisor')
        map_roles = {'admin': 'Administrador', 'user': 'Emisor', 'viewer': 'Auditor'}
        rol_final = map_roles.get(rol_nombre, 'Emisor')

        rol_db = Rol.query.filter_by(nombre=rol_final).first()
        if not rol_db:
            raise ValidationError(f'Rol {rol_final} no configurado en el sistema.')

        acc = AccesoSucursal(
            usuario_id=nuevo_user.id,
            sucursal_id=sucursal.id,
            rol_id=rol_db.id,
        )
        db.session.add(acc)
        db.session.commit()
        return {
            'message': 'Usuario creado exitosamente.',
            'usuario': {
                'id': nuevo_user.id,
                'nombre': nuevo_user.nombre,
                'email': nuevo_user.email,
                'rol': rol_final,
                'sucursal': sucursal.nombre,
            },
        }

    @staticmethod
    def get_user_for_empresa(empresa_id, user_id):
        return Usuario.query.filter_by(id=user_id, empresa_id=empresa_id).first()

    @staticmethod
    def update_user(current_user, user_id, data):
        usuario = EmpresaService.get_user_for_empresa(current_user.empresa_id, user_id)
        if not usuario:
            raise ValidationError('Usuario no encontrado.')

        usuario.nombre = data.get('nombre', usuario.nombre)
        usuario.is_active = data.get('activo', usuario.is_active)
        if 'pantallas' in data:
            pantallas_raw = data.get('pantallas', [])
            pantallas_filtradas = [p for p in pantallas_raw if p not in ['superAdmin']]
            usuario.pantallas_asignadas = ','.join(pantallas_filtradas)

        if data.get('password'):
            usuario.set_password(data.get('password'))

        db.session.commit()
        return {'message': 'Usuario actualizado.'}

    @staticmethod
    def delete_user(current_user, user_id):
        usuario = EmpresaService.get_user_for_empresa(current_user.empresa_id, user_id)
        if not usuario:
            raise ValidationError('Usuario no encontrado.')
        if usuario.id == current_user.id:
            raise ValidationError('No puedes eliminarte a ti mismo.')

        db.session.delete(usuario)
        db.session.commit()
        return {'message': 'Usuario eliminado.'}
