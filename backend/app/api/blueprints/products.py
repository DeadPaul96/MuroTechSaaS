import os
import requests
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from app.models import db, Producto
from app.api.decorators.auth import token_required
from app.extensions import limiter

bp = Blueprint('products', __name__, url_prefix='/api')

@bp.route('/productos', methods=['GET', 'POST'])
@token_required
def productos(current_user):
    if request.method == 'GET':
        q = request.args.get('q', '').strip().lower()
        query = Producto.query.filter_by(empresa_id=current_user.empresa_id)
        
        if q:
            query = query.filter(
                or_(
                    Producto.descripcion.ilike(f'%{q}%'),
                    Producto.nombre_servicio.ilike(f'%{q}%'),
                    Producto.marca.ilike(f'%{q}%'),
                    Producto.modelo.ilike(f'%{q}%'),
                    Producto.caracteristicas.ilike(f'%{q}%'),
                    Producto.cabys.ilike(f'%{q}%'),
                    Producto.codigo.ilike(f'%{q}%')
                )
            )
        
        productos_list = query.limit(50).all()
        return jsonify([{
            'id': p.id, 'cabys': p.cabys, 'codigo': p.codigo, 
            'unidadMedida': p.unidad_medida, 
            'descripcion': p.descripcion,
            'marca': p.marca, 'modelo': p.modelo, 'caracteristicas': p.caracteristicas,
            'nombreServicio': p.nombre_servicio, 'detalleServicio': p.detalle_servicio,
            'precio': float(p.costo or 0), 'margen': float(p.margen or 0), 'precioVenta': float(p.precio_venta or 0),
            'impuesto': float(p.impuesto or 0), 'tipoImpuesto': p.tipo_impuesto,
            'stock': p.stock, 'descuentoMax': float(p.descuento_max or 0),
            'nombre': p.descripcion or p.nombre_servicio
        } for p in productos_list])

    if request.method == 'POST':
        data = request.get_json() or {}
        nuevo = Producto(
            empresa_id=current_user.empresa_id,
            cabys=data.get('cabys'),
            codigo=data.get('codigo'),
            unidad_medida=data.get('unidadMedida', 'Unid'),
            descripcion=data.get('descripcion'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            caracteristicas=data.get('caracteristicas'),
            nombre_servicio=data.get('nombreServicio'),
            detalle_servicio=data.get('detalleServicio'),
            costo=float(data.get('precio', 0)),
            margen=float(data.get('margen', 0)),
            precio_venta=float(data.get('precioVenta', 0)),
            impuesto=float(data.get('impuesto', 13)),
            tipo_impuesto=data.get('tipoImpuesto', '01'),
            stock=int(data.get('stock', 0)),
            descuento_max=float(data.get('descuentoMax', 0))
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({'message': 'Ítem guardado exitosamente', 'id': nuevo.id}), 201

@bp.route('/productos/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_producto(current_user, id):
    producto = Producto.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not producto:
        return jsonify({'message': 'Ítem no encontrado o acceso denegado'}), 404

    if request.method == 'PUT':
        data = request.get_json() or {}
        producto.descripcion = data.get('descripcion', producto.descripcion)
        producto.marca = data.get('marca', producto.marca)
        producto.modelo = data.get('modelo', producto.modelo)
        producto.caracteristicas = data.get('caracteristicas', producto.caracteristicas)
        producto.nombre_servicio = data.get('nombreServicio', producto.nombre_servicio)
        producto.detalle_servicio = data.get('detalleServicio', producto.detalle_servicio)
        producto.costo = float(data.get('precio', producto.costo))
        producto.margen = float(data.get('margen', producto.margen))
        producto.precio_venta = float(data.get('precioVenta', producto.precio_venta))
        producto.impuesto = float(data.get('impuesto', producto.impuesto))
        producto.stock = int(data.get('stock', producto.stock))
        producto.descuento_max = float(data.get('descuentoMax', producto.descuento_max))
        producto.tipo_impuesto = data.get('tipoImpuesto', producto.tipo_impuesto)
        db.session.commit()
        return jsonify({'message': 'Ítem actualizado exitosamente'}), 200

    if request.method == 'DELETE':
        db.session.delete(producto)
        db.session.commit()
        return jsonify({'message': 'Ítem eliminado exitosamente'}), 200

@bp.route('/cabys/search', methods=['GET'])
@limiter.limit(os.environ.get('RATELIMIT_CABYS', '60 per hour'))
def search_cabys():
    """
    Busca códigos CABYS usando la API oficial del Ministerio de Hacienda
    """
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({"success": True, "results": [], "count": 0}), 200
        
        api_url = f"https://api.hacienda.go.cr/fe/cabys?q={query}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            resultados = []
            
            if isinstance(data, dict) and 'cabys' in data:
                items = data['cabys'][:30]
                for item in items:
                    resultados.append({
                        'codigo': item.get('codigo', ''),
                        'descripcion': item.get('descripcion', ''),
                        'impuesto': item.get('impuesto', 13)
                    })
            elif isinstance(data, list):
                for item in data[:30]:
                    resultados.append({
                        'codigo': item.get('codigo', ''),
                        'descripcion': item.get('descripcion', ''),
                        'impuesto': item.get('impuesto', 13)
                    })
            
            return jsonify({"success": True, "results": resultados, "count": len(resultados)}), 200
        else:
            return jsonify({"success": False, "message": "Error al consultar API de Hacienda", "results": [], "count": 0}), response.status_code
            
    except requests.Timeout:
        return jsonify({"success": False, "message": "Timeout al consultar API de Hacienda", "results": [], "count": 0}), 504
    except Exception as e:
        print(f"Error buscando CABYS: {str(e)}")
        return jsonify({"success": False, "message": "Error al buscar en catálogo CABYS", "error": str(e), "results": [], "count": 0}), 500
