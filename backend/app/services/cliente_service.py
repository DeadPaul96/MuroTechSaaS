"""Servicio de gestión de clientes."""
import uuid

from sqlalchemy import or_

from app.extensions import db
from app.models import Cliente
from app.utils.validators import ValidationError, validar_identificacion, validar_email


class ClienteService:
    @staticmethod
    def get_customers(empresa_id, q=None, limit=50):
        query = Cliente.query.filter_by(empresa_id=empresa_id)
        if q:
            query = query.filter(
                or_(
                    Cliente.nombre.ilike(f'%{q}%'),
                    Cliente.identificacion.ilike(f'%{q}%'),
                    Cliente.email.ilike(f'%{q}%'),
                )
            )
        return query.limit(limit).all()

    @staticmethod
    def get_customer(empresa_id, cliente_id):
        return Cliente.query.filter_by(id=cliente_id, empresa_id=empresa_id).first()

    @staticmethod
    def create_customer(empresa_id, data):
        if not data.get('nombre') or not data.get('identificacion'):
            raise ValidationError('Nombre e identificación son requeridos.')

        tipo_id = data.get('tipo_id', '01')
        try:
            validar_identificacion(tipo_id, data.get('identificacion'))
        except ValidationError:
            raise

        if data.get('correo'):
            validar_email(data.get('correo'))

        if Cliente.query.filter_by(
            empresa_id=empresa_id,
            identificacion=data.get('identificacion'),
        ).first():
            raise ValidationError('Ya existe un cliente con esa identificación.')

        cliente = Cliente(
            id=str(uuid.uuid4()),
            empresa_id=empresa_id,
            tipo_id=tipo_id,
            identificacion=data.get('identificacion'),
            nombre=data.get('nombre'),
            email=data.get('correo'),
            telefono=data.get('telefono'),
            movil=data.get('movil'),
            actividad_economica=data.get('actividad_economica'),
            regimen=data.get('regimen'),
            provincia=data.get('provincia'),
            canton=data.get('canton'),
            distrito=data.get('distrito'),
            barrio=data.get('barrio'),
            direccion=data.get('direccion'),
        )
        db.session.add(cliente)
        db.session.commit()
        return cliente

    @staticmethod
    def update_customer(empresa_id, cliente_id, data):
        cliente = ClienteService.get_customer(empresa_id, cliente_id)
        if not cliente:
            raise ValidationError('Cliente no encontrado.')

        if data.get('nombre'):
            cliente.nombre = data.get('nombre')
        if data.get('correo') is not None:
            if data.get('correo'):
                validar_email(data.get('correo'))
            cliente.email = data.get('correo')
        if data.get('telefono') is not None:
            cliente.telefono = data.get('telefono')
        if data.get('movil') is not None:
            cliente.movil = data.get('movil')
        if data.get('actividad_economica') is not None:
            cliente.actividad_economica = data.get('actividad_economica')
        if data.get('regimen') is not None:
            cliente.regimen = data.get('regimen')
        if data.get('provincia') is not None:
            cliente.provincia = data.get('provincia')
        if data.get('canton') is not None:
            cliente.canton = data.get('canton')
        if data.get('distrito') is not None:
            cliente.distrito = data.get('distrito')
        if data.get('barrio') is not None:
            cliente.barrio = data.get('barrio')
        if data.get('direccion') is not None:
            cliente.direccion = data.get('direccion')

        db.session.commit()
        return cliente

    @staticmethod
    def delete_customer(empresa_id, cliente_id):
        cliente = ClienteService.get_customer(empresa_id, cliente_id)
        if not cliente:
            raise ValidationError('Cliente no encontrado.')

        if cliente.facturas:
            raise ValidationError('No se puede eliminar un cliente con facturas asociadas.')

        db.session.delete(cliente)
        db.session.commit()
        return True
