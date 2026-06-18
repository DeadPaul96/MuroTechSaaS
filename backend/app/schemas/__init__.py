from marshmallow import Schema, fields, validate, validates_schema, ValidationError as MaValidationError


class EmpresaSchema(Schema):
    razon_social = fields.Str(required=True, validate=validate.Length(max=200))
    nombre_comercial = fields.Str(validate=validate.Length(max=200))
    cedula_juridica = fields.Str(required=True, validate=validate.Length(equal=10))
    tipo_identificacion = fields.Str(validate=validate.OneOf(['01', '02', '03', '04']), load_default='02')
    email_contacto = fields.Email(required=True)
    telefono = fields.Str(validate=validate.Length(max=50))
    actividad_economica = fields.Str(validate=validate.Length(max=200))
    ambiente_hacienda = fields.Str(validate=validate.OneOf(['stag', 'prod']), load_default='stag')


class SucursalSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(max=100))
    numero_sucursal = fields.Str(required=True, validate=validate.Length(equal=3))
    terminal = fields.Str(validate=validate.Length(equal=5), load_default='00001')
    direccion = fields.Str(validate=validate.Length(max=500))
    provincia = fields.Str(validate=validate.Length(equal=1), load_default='1')
    canton = fields.Str(validate=validate.Length(equal=2), load_default='01')
    distrito = fields.Str(validate=validate.Length(equal=2), load_default='01')


class ClienteSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(max=100))
    tipo_id = fields.Str(validate=validate.OneOf(['01', '02', '03', '04']), load_default='01')
    identificacion = fields.Str(required=True, validate=validate.Length(max=20))
    email = fields.Email()
    telefono = fields.Str(validate=validate.Length(max=50))


class ProductoSchema(Schema):
    codigo = fields.Str(required=True, validate=validate.Length(max=50))
    descripcion = fields.Str(required=True, validate=validate.Length(max=200))
    cabys = fields.Str(validate=validate.Length(equal=13))
    precio_venta = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))
    precio_compra = fields.Decimal(as_string=True, validate=validate.Range(min=0))
    impuesto = fields.Decimal(as_string=True, validate=validate.Range(min=0, max=100), load_default='13.00')
    stock = fields.Integer(validate=validate.Range(min=0), load_default=0)
    stock_minimo = fields.Integer(validate=validate.Range(min=0), load_default=5)


class FacturaDetalleSchema(Schema):
    producto_id = fields.Str()
    descripcion = fields.Str(required=True, validate=validate.Length(max=200))
    cantidad = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))
    precio = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))
    descuento = fields.Decimal(as_string=True, validate=validate.Range(min=0, max=100), load_default='0.00')
    impuesto = fields.Decimal(as_string=True, validate=validate.Range(min=0, max=100), load_default='13.00')
    tipo_impuesto = fields.Str(validate=validate.Length(max=10), load_default='01')


class FacturaSchema(Schema):
    tipoDoc = fields.Str(validate=validate.OneOf(['01', '02', '03', '04', '05', '08', '09', '10']), load_default='01')
    cliente_id = fields.Str()
    condicionVenta = fields.Str(validate=validate.Length(max=2), load_default='01')
    medioPago = fields.Str(validate=validate.Length(max=2), load_default='01')
    moneda = fields.Str(validate=validate.OneOf(['CRC', 'USD', 'EUR']), load_default='CRC')
    detalles = fields.List(fields.Nested(FacturaDetalleSchema), required=True, validate=validate.Length(min=1))
    referencia_id = fields.Str()
    referencia_codigo = fields.Str()
    referencia_razon = fields.Str(validate=validate.Length(max=200))

    @validates_schema
    def validate_nc_nd_referencia(self, data, **kwargs):
        if data.get('tipoDoc') in ('02', '03') and not data.get('referencia_id'):
            raise MaValidationError('referencia_id', 'NC/ND requiere referencia_id del documento original.')


class PagoCheckoutSchema(Schema):
    empresa_id = fields.Str(required=True)
    plan_tipo = fields.Str(validate=validate.OneOf(list(AVAILABLE_PLAN_KEYS)), load_default='basico') if (AVAILABLE_PLAN_KEYS := ['basico', 'emisor', 'premium', 'enterprise']) else fields.Str(load_default='basico')


class PagoConfirmSchema(Schema):
    payment_id = fields.Str(required=True)
    provider = fields.Str()
    transaction_id = fields.Str()


class MensajeReceptorSchema(Schema):
    clave_comprobante = fields.Str(required=True, validate=validate.Length(equal=50))
    tipo_mensaje = fields.Str(required=True, validate=validate.OneOf(['1', '2', '3', 'aceptar', 'parcial', 'rechazar']))
    cedula_emisor = fields.Str(required=True, validate=validate.Length(max=12))
    cedula_receptor = fields.Str(required=True, validate=validate.Length(max=12))
    fecha_emision_doc = fields.Str()
    detalle_mensaje = fields.Str(validate=validate.Length(max=80))
