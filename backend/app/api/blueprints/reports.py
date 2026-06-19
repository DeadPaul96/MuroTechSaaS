from decimal import Decimal
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app.models import (
    db, Factura, FacturaDetalle, Sucursal, Producto, Cliente
)
from app.api.decorators.auth import token_required
from app.api.decorators.rbac import require_role
from app.services.auth_service import AuthService
from app.utils.money import calcular_variacion
from app.utils.date_utils import _parse_date

bp = Blueprint('reports', __name__, url_prefix='/api')


def is_company_admin(user):
    """Devuelve True si el usuario tiene rol Administrador o es superadmin."""
    if user.is_superadmin:
        return True
    return any(acc.rol.nombre in ('Administrador', 'Admin') for acc in user.accesos)


def validate_sucursal(user, sucursal_id):
    """Retorna la sucursal si el usuario tiene acceso a ella."""
    if not sucursal_id:
        acceso = user.accesos[0] if user.accesos else None
        return acceso.sucursal if acceso else None
    sucursal = Sucursal.query.get(sucursal_id)
    if not sucursal:
        return None
    if is_company_admin(user):
        if sucursal.empresa_id != user.empresa_id:
            return None
        return sucursal
    allowed_ids = [acc.sucursal_id for acc in user.accesos]
    return sucursal if sucursal_id in allowed_ids else None

@bp.route('/reportes/data', methods=['GET'])
@token_required
def get_reportes_data(current_user):
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    cliente_id = request.args.get('cliente_id')
    
    sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
    query_facturas = Factura.query.filter(
        Factura.sucursal_id.in_(sucursales_ids),
        Factura.is_draft == False
    )
    
    desde_dt = _parse_date(desde)
    hasta_dt = _parse_date(hasta, end_of_day=True)
    if desde_dt: query_facturas = query_facturas.filter(Factura.fecha_emision >= desde_dt)
    if hasta_dt: query_facturas = query_facturas.filter(Factura.fecha_emision <= hasta_dt)
    if cliente_id and cliente_id != 'all': 
        query_facturas = query_facturas.filter(Factura.cliente_id == cliente_id)

    facturas = query_facturas.all()

    total_ventas = sum(f.total for f in facturas)
    total_iva = sum(f.impuestos for f in facturas)
    total_neto = total_ventas - total_iva

    ventas_por_fecha = {}
    for f in facturas:
        fecha_str = f.fecha_emision.strftime('%Y-%m-%d')
        ventas_por_fecha[fecha_str] = ventas_por_fecha.get(fecha_str, 0) + float(f.total)
    
    chart_data = [{'fecha': k, 'total': v} for k, v in sorted(ventas_por_fecha.items())]

    productos = Producto.query.filter_by(empresa_id=current_user.empresa_id).all()
    stock_bajo = [p for p in productos if p.stock <= 5]
    valor_inventario = sum((p.stock * p.costo) for p in productos if p.costo)

    return jsonify({
        'kpis': {
            'ventas': float(total_ventas),
            'iva': float(total_iva),
            'utilidad': float(total_neto * Decimal('0.3')),
            'compras': float(total_neto * Decimal('0.4'))
        },
        'tablas': {
            'ventas': [{
                'fecha': f.fecha_emision.strftime('%Y-%m-%d'),
                'consecutivo': f.numero_consecutivo,
                'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                'bruto': float(f.subtotal),
                'iva': float(f.impuestos),
                'total': float(f.total),
                'estado': f.estado
            } for f in facturas],
            'inventario': [{
                'codigo': p.codigo,
                'nombre': p.descripcion,
                'costo': float(p.costo or 0),
                'venta': float(p.precio_venta or 0),
                'stock': float(p.stock),
                'status': 'STOCK_BAJO' if p.stock <= 5 else 'NORMAL'
            } for p in productos]
        },
        'charts': {
            'ventas': chart_data,
            'productos': [{'label': 'Otros', 'value': 100}]
        },
        'resumen_inventario': {
            'total_skus': len(productos),
            'valor_total': float(valor_inventario),
            'conteo_bajo': len(stock_bajo)
        }
    })

@bp.route('/auditoria', methods=['GET'])
@token_required
def get_auditoria_data(current_user):
    try:
        if is_company_admin(current_user):
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
        else:
            sucursales_ids = [acc.sucursal_id for acc in current_user.accesos]

        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        estado = request.args.get('estado', 'todos')
        vendedor_id = request.args.get('vendedor_id', 'todos')
        medio_pago = request.args.get('medio_pago', 'todos')
        q = request.args.get('q', '').lower()

        f_query = Factura.query.filter(Factura.sucursal_id.in_(sucursales_ids))
        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt: f_query = f_query.filter(Factura.fecha_emision >= desde_dt)
        if hasta_dt: f_query = f_query.filter(Factura.fecha_emision <= hasta_dt)
        if estado != 'todos': f_query = f_query.filter(Factura.estado.ilike(f"%{estado}%"))
        if vendedor_id != 'todos': f_query = f_query.filter(Factura.usuario_id == vendedor_id)
        if medio_pago != 'todos': f_query = f_query.filter(Factura.medio_pago == medio_pago)
        
        if q:
            f_query = f_query.join(Cliente, isouter=True).filter(
                db.or_(
                    Factura.numero_consecutivo.ilike(f"%{q}%"),
                    Factura.clave.ilike(f"%{q}%"),
                    Cliente.nombre.ilike(f"%{q}%"),
                    Factura.observaciones.ilike(f"%{q}%")
                )
            )

        facturas = f_query.order_by(Factura.fecha_emision.desc()).all()
        facturas_list = [{
            'id': f.id,
            'fecha': f.fecha_emision.isoformat() + 'Z',
            'consecutivo': f.numero_consecutivo,
            'clave': f.clave,
            'receptor': f.cliente.nombre if f.cliente else 'Consumidor Final',
            'vendedor': f.usuario.nombre if f.usuario else 'Sistema',
            'monto': f.total,
            'medio_pago': f.medio_pago,
            'estado': f.estado,
            'has_pdf': f.pdf_comprobante is not None,
            'has_xml': f.xml_comprobante is not None
        } for f in facturas]

        movs_list = []
        try:
            # InventarioMovimiento no implementado aún — lista vacía
            pass
        except Exception:
            pass

        bitacora = [{
            'fecha': f.fecha_emision.isoformat() + 'Z',
            'transaccion': f"TRN-{str(f.id)[:8].upper()}",
            'caja': f.sucursal.nombre,
            'vendedor': 'Sistema',
            'monto': f.total,
            'medio_pago': f.medio_pago
        } for f in facturas[:50]]

        return jsonify({
            'comprobantes': facturas_list,
            'movimientos': movs_list,
            'ventas': bitacora
        }), 200

    except Exception as e:
        print(f"Error Auditoría: {str(e)}")
        return jsonify({'message': 'Error al cargar datos de auditoría', 'error': str(e)}), 500

@bp.route('/reportes', methods=['GET'])
@token_required
def get_reportes_summary(current_user):
    try:
        if is_company_admin(current_user):
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
        else:
            sucursales_ids = [acc.sucursal_id for acc in current_user.accesos]

        desde = request.args.get('desde')
        hasta = request.args.get('hasta')

        f_query = Factura.query.filter(Factura.sucursal_id.in_(sucursales_ids))
        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt: f_query = f_query.filter(Factura.fecha_emision >= desde_dt)
        if hasta_dt: f_query = f_query.filter(Factura.fecha_emision <= hasta_dt)

        facturas = f_query.all()

        ventas_brutas = float(sum(f.total for f in facturas if not f.is_quotation) or 0)
        impuestos = float(sum(f.impuestos for f in facturas if not f.is_quotation) or 0)
        
        compras_db = []
        total_compras = 0.0
        
        utilidad = ventas_brutas - total_compras

        tendencia_dict = {}
        for f in facturas:
            if f.is_quotation: continue
            fecha_str = f.fecha_emision.strftime('%Y-%m-%d') if f.fecha_emision else None
            if fecha_str:
                monto = float(f.total or 0)
                tendencia_dict[fecha_str] = tendencia_dict.get(fecha_str, 0) + monto
        
        tendencia = [{'label': k, 'valor': float(v)} for k, v in sorted(tendencia_dict.items())]

        top_productos = []
        try:
            top_prod_res = db.session.query(
                FacturaDetalle.descripcion,
                func.sum(FacturaDetalle.total_linea).label('total')
            ).join(Factura).filter(Factura.sucursal_id.in_(sucursales_ids))
            
            if desde_dt: top_prod_res = top_prod_res.filter(Factura.fecha_emision >= desde_dt)
            if hasta_dt: top_prod_res = top_prod_res.filter(Factura.fecha_emision <= hasta_dt)
            
            top_prod_raw = top_prod_res.group_by(FacturaDetalle.descripcion).order_by(db.desc('total')).limit(5).all()
            top_productos = [{
                'label': str(p.descripcion or "Producto"),
                'valor': float(p.total or 0)
            } for p in top_prod_raw]
        except Exception as e_top:
            print(f"Error Top Productos: {e_top}")
            top_productos = []

        productos = Producto.query.filter_by(empresa_id=current_user.empresa_id).all()
        inventario = [{
            'codigo': str(p.codigo or "N/A"),
            'descripcion': str(p.descripcion or "Sin descripción"),
            'categoria': str(p.marca or 'General'),
            'precio_compra': float(p.costo or 0),
            'precio_venta': float(p.precio_venta or 0),
            'existencia': int(p.stock or 0),
            'status': 'Bajo' if (p.stock or 0) <= 5 else 'OK'
        } for p in productos]

        valor_inventario = sum(p.stock * p.costo for p in productos)

        return jsonify({
            'kpis': {
                'ventas': float(ventas_brutas or 0),
                'compras': float(total_compras or 0),
                'utilidad': float(utilidad or 0),
                'impuestos': float(impuestos or 0),
                'sku_total': len(productos),
                'valor_inventario': float(valor_inventario or 0),
                'stock_bajo': len([p for p in productos if (p.stock or 0) <= 5])
            },
            'graficos': {
                'tendencia': tendencia,
                'top_productos': top_productos
            },
            'tablas': {
                'ventas': [{
                    'fecha': (f.fecha_emision.isoformat() + 'Z') if f.fecha_emision else '',
                    'numero': f.numero_consecutivo,
                    'cliente': (f.cliente.nombre if f.cliente else 'Consumidor Final'),
                    'bruto': float(f.subtotal or 0),
                    'impuestos': float(f.impuestos or 0),
                    'total': float(f.total or 0),
                    'estado': f.estado or 'N/A'
                } for f in facturas if not f.is_quotation],
                'compras': [{
                    'fecha': (c.fecha.isoformat() + 'Z') if c.fecha else '',
                    'proveedor': c.proveedor or 'Anónimo',
                    'concepto': c.concepto or 'Gasto',
                    'monto': float(c.monto_neto or 0),
                    'iva': float(c.iva or 0),
                    'total': float(c.total or 0),
                    'categoria': c.categoria or 'General'
                } for c in compras_db],
                'inventario': inventario,
                'comprobantes': [{
                    'consecutivo': f.numero_consecutivo,
                    'fecha': f.fecha_emision.isoformat() + 'Z',
                    'receptor': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'estado': f.estado,
                    'clave': f.clave
                } for f in facturas if f.xml_comprobante],
                'cotizaciones': [{
                    'fecha': f.fecha_emision.isoformat() + 'Z',
                    'numero': f.numero_consecutivo,
                    'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'vencimiento': f.fecha_vencimiento.isoformat() + 'Z' if f.fecha_vencimiento else '',
                    'monto': float(f.total),
                    'estado': f.estado
                } for f in facturas if f.is_quotation]
            }
        }), 200

    except Exception as e:
        print(f"Error Reportes: {str(e)}")
        return jsonify({'message': 'Error al procesar reportes', 'error': str(e)}), 500

@bp.route('/auditoria/comprobantes', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor', 'Emisor'])
def auditoria_comprobantes(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    facturas = Factura.query.filter_by(sucursal_id=sucursal.id).order_by(Factura.fecha_emision.desc()).limit(100).all()
    return jsonify([{
        'id': f.id,
        'fecha': f.fecha_emision.isoformat(),
        'numero_consecutivo': f.numero_consecutivo,
        'clave': f.clave,
        'clienteNombre': f.cliente.nombre if f.cliente else 'Consumidor Final',
        'monto': f.total,
        'estado': f.estado,
        'tipo': f.tipo_documento
    } for f in facturas])

@bp.route('/auditoria/inventario', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor'])
def auditoria_inventario(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403
    # InventarioMovimiento no implementado aún
    return jsonify([])

@bp.route('/auditoria/ventas', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor'])
def auditoria_ventas(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    ventas = Factura.query.filter(
        Factura.sucursal_id == sucursal.id,
        Factura.estado.notin_(['Borrador', 'Rechazada'])
    ).order_by(Factura.fecha_emision.desc()).limit(100).all()
    
    return jsonify([{
        'id': v.id,
        'fecha': v.fecha_emision.isoformat(),
        'transaccion': f"TRN-{v.id}-{v.numero_consecutivo[-4:] if v.numero_consecutivo else '0000'}",
        'caja': 'TERMINAL PRINCIPAL',
        'vendedor': current_user.nombre,
        'monto': v.total,
        'pago': v.medio_pago
    } for v in ventas])

@bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard_metrics(current_user):
    try:
        if current_user.is_superadmin:
            return jsonify({"message": "SuperAdmin debe usar el panel de SuperAdmin"}), 403
        
        accesos = current_user.accesos
        if not accesos:
            return jsonify({
                "facturasEmitidas": 0,
                "facturasVariacion": "0%",
                "ingresosTotales": 0,
                "ingresosVariacion": "0%",
                "clientesActivos": 0,
                "clientesVariacion": "0%",
                "tasaConversion": "0.0%",
                "tasaVariacion": "0%",
                "actividadReciente": [],
                "scope": "sin_acceso"
            }), 200
        
        es_administrador = any(acc.rol.nombre == 'Administrador' for acc in accesos)
        
        if es_administrador:
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
            scope = "empresa"
        else:
            sucursales_ids = [acc.sucursal_id for acc in accesos]
            scope = "sucursal"
        
        if not sucursales_ids:
            return jsonify({
                "facturasEmitidas": 0,
                "facturasVariacion": "0%",
                "ingresosTotales": 0,
                "ingresosVariacion": "0%",
                "clientesActivos": 0,
                "clientesVariacion": "0%",
                "tasaConversion": "0.0%",
                "tasaVariacion": "0%",
                "actividadReciente": [],
                "scope": scope
            }), 200
        
        hoy = datetime.now()
        inicio_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1)
        fin_mes_anterior = inicio_mes_actual - timedelta(seconds=1)
        
        facturas_mes_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        facturas_mes_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        facturas_variacion = calcular_variacion(facturas_mes_actual, facturas_mes_anterior)
        
        facturas_exitosas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Pagada', 'Aceptada MH', 'Aceptada', 'Pendiente']),
            Factura.fecha_emision >= inicio_mes_actual
        ).all()
        ingresos_mes_actual = sum(float(f.total) for f in facturas_exitosas_actual)
        
        facturas_exitosas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Pagada', 'Aceptada MH', 'Aceptada', 'Pendiente']),
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).all()
        ingresos_mes_anterior = sum(float(f.total) for f in facturas_exitosas_anterior)
        
        ingresos_variacion = calcular_variacion(ingresos_mes_actual, ingresos_mes_anterior)
        
        clientes_activos_actual = db.session.query(func.count(func.distinct(Factura.cliente_id))).filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual,
            Factura.cliente_id.isnot(None)
        ).scalar() or 0
        
        clientes_activos_anterior = db.session.query(func.count(func.distinct(Factura.cliente_id))).filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior,
            Factura.cliente_id.isnot(None)
        ).scalar() or 0
        
        clientes_variacion = calcular_variacion(clientes_activos_actual, clientes_activos_anterior)
        
        total_facturas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        facturas_rechazadas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Rechazada', 'Anulada']),
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        tasa_conversion_actual = 100.0
        if total_facturas_actual > 0:
            exito = total_facturas_actual - facturas_rechazadas_actual
            tasa_conversion_actual = (exito / total_facturas_actual) * 100
        
        total_facturas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        facturas_rechazadas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Rechazada', 'Anulada']),
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        tasa_conversion_anterior = 100.0
        if total_facturas_anterior > 0:
            exito_anterior = total_facturas_anterior - facturas_rechazadas_anterior
            tasa_conversion_anterior = (exito_anterior / total_facturas_anterior) * 100
        
        tasa_variacion = calcular_variacion(tasa_conversion_actual, tasa_conversion_anterior)
        
        actividad = []
        recientes = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False
        ).order_by(Factura.fecha_emision.desc()).limit(10).all()
        
        for f in recientes:
            actividad.append({
                "tipo": "factura",
                "id": f.numero_consecutivo,
                "clienteNombre": f.cliente.nombre if f.cliente else "Consumidor Final",
                "monto": float(f.total),
                "estado": f.estado,
                "fecha": f.fecha_emision.isoformat(),
                "sucursal": f.sucursal.nombre if f.sucursal else "N/A"
            })
        
        return jsonify({
            "facturasEmitidas": facturas_mes_actual,
            "facturasVariacion": facturas_variacion,
            "ingresosTotales": ingresos_mes_actual,
            "ingresosVariacion": ingresos_variacion,
            "clientesActivos": clientes_activos_actual,
            "clientesVariacion": clientes_variacion,
            "tasaConversion": f"{tasa_conversion_actual:.1f}%",
            "tasaVariacion": tasa_variacion,
            "actividadReciente": actividad,
            "scope": scope,
            "periodo": {
                "mes_actual": inicio_mes_actual.strftime("%B %Y"),
                "mes_anterior": inicio_mes_anterior.strftime("%B %Y")
            }
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Error al cargar métricas", "error": str(e)}), 500
