from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from app.models import db, Cliente
from app.api.decorators.auth import token_required
from app.utils.validators import ValidationError, validar_identificacion, validar_email

bp = Blueprint('customers', __name__, url_prefix='/api')

@bp.route('/clientes', methods=['GET', 'POST'])
@token_required
def clientes(current_user):
    if request.method == 'GET':
        q = request.args.get('q', '').strip().lower()
        query = Cliente.query.filter_by(empresa_id=current_user.empresa_id)
        
        if q:
            query = query.filter(
                or_(
                    Cliente.nombre.ilike(f'%{q}%'),
                    Cliente.identificacion.ilike(f'%{q}%'),
                    Cliente.email.ilike(f'%{q}%')
                )
            )
        
        clientes = query.limit(50).all()
        return jsonify([{
            'id': c.id, 'nombre': c.nombre, 'identificacion': c.identificacion,
            'tipo_id': c.tipo_id, 'correo': c.email, 'telefono': c.telefono,
            'movil': c.movil, 'actividad': c.actividad_economica, 'regimen': c.regimen,
            'provincia': c.provincia, 'canton': c.canton, 'distrito': c.distrito, 
            'barrio': c.barrio, 'direccion': c.direccion
        } for c in clientes])
        
    if request.method == 'POST':
        data = request.get_json() or {}
        try:
            validar_identificacion(data.get('tipo_id', '01'), data.get('identificacion'))
            if data.get('correo'):
                validar_email(data.get('correo'))
        except ValidationError as verr:
            return jsonify({'message': str(verr)}), 400
        nuevo = Cliente(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            identificacion=data.get('identificacion'),
            tipo_id=data.get('tipo_id', '01'),
            email=data.get('correo'),
            telefono=data.get('telefono'),
            movil=data.get('movil'),
            actividad_economica=data.get('actividad'),
            regimen=data.get('regimen'),
            provincia=data.get('provincia'),
            canton=data.get('canton'),
            distrito=data.get('distrito'),
            barrio=data.get('barrio'),
            direccion=data.get('direccion')
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({'message': 'Cliente creado exitosamente', 'id': nuevo.id}), 201

@bp.route('/clientes/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_cliente(current_user, id):
    cliente = Cliente.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not cliente:
        return jsonify({'message': 'Cliente no encontrado o acceso denegado'}), 404

    if request.method == 'PUT':
        data = request.get_json() or {}
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.email = data.get('correo', cliente.email)
        cliente.telefono = data.get('telefono', cliente.telefono)
        cliente.movil = data.get('movil', cliente.movil)
        cliente.provincia = data.get('provincia', cliente.provincia)
        cliente.canton = data.get('canton', cliente.canton)
        cliente.distrito = data.get('distrito', cliente.distrito)
        cliente.barrio = data.get('barrio', cliente.barrio)
        cliente.direccion = data.get('direccion', cliente.direccion)
        cliente.actividad_economica = data.get('actividad', cliente.actividad_economica)
        cliente.regimen = data.get('regimen', cliente.regimen)
        db.session.commit()
        return jsonify({'message': 'Cliente actualizado exitosamente'}), 200

    if request.method == 'DELETE':
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({'message': 'Cliente eliminado exitosamente'}), 200
