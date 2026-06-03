"""
Validadores para MUROTECH
Validación de datos según normativa MH Costa Rica
"""
from decimal import Decimal, InvalidOperation
import re
from datetime import datetime

class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass

def validar_cedula_fisica(cedula):
    """
    Valida cédula física costarricense con dígito verificador
    Formato: 9 dígitos (ej: 123456789)
    """
    if not cedula:
        raise ValidationError("Cédula física es requerida")
    
    # Limpiar guiones y espacios
    cedula = str(cedula).replace('-', '').replace(' ', '')
    
    if len(cedula) != 9:
        raise ValidationError("Cédula física debe tener 9 dígitos")
    
    if not cedula.isdigit():
        raise ValidationError("Cédula física debe contener solo números")
    
    # Algoritmo de validación MH Costa Rica
    multiplicadores = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    
    for i, digito in enumerate(cedula[:-1]):
        producto = int(digito) * multiplicadores[i]
        suma += producto if producto < 10 else (producto // 10) + (producto % 10)
    
    verificador_calculado = (10 - (suma % 10)) % 10
    verificador_cedula = int(cedula[-1])
    
    if verificador_calculado != verificador_cedula:
        raise ValidationError("Cédula física inválida (dígito verificador incorrecto)")
    
    return cedula

def validar_cedula_juridica(cedula):
    """
    Valida cédula jurídica costarricense
    Formato: 10 dígitos, debe empezar con 3 (ej: 3101234567)
    """
    if not cedula:
        raise ValidationError("Cédula jurídica es requerida")
    
    # Limpiar guiones y espacios
    cedula = str(cedula).replace('-', '').replace(' ', '')
    
    if len(cedula) != 10:
        raise ValidationError("Cédula jurídica debe tener 10 dígitos")
    
    if not cedula.isdigit():
        raise ValidationError("Cédula jurídica debe contener solo números")
    
    # Debe empezar con 3 (jurídica) o 2 (física extranjera)
    if cedula[0] not in ['2', '3']:
        raise ValidationError("Cédula jurídica debe empezar con 2 o 3")
    
    return cedula

def validar_dimex(dimex):
    """
    Valida DIMEX (Documento de Identidad Migratoria para Extranjeros)
    Formato: 11 o 12 dígitos
    """
    if not dimex:
        raise ValidationError("DIMEX es requerido")
    
    dimex = str(dimex).replace('-', '').replace(' ', '')
    
    if len(dimex) not in [11, 12]:
        raise ValidationError("DIMEX debe tener 11 o 12 dígitos")
    
    if not dimex.isdigit():
        raise ValidationError("DIMEX debe contener solo números")
    
    return dimex

def validar_nite(nite):
    """
    Valida NITE (Número de Identificación Tributaria Especial)
    Formato: 10 dígitos
    """
    if not nite:
        raise ValidationError("NITE es requerido")
    
    nite = str(nite).replace('-', '').replace(' ', '')
    
    if len(nite) != 10:
        raise ValidationError("NITE debe tener 10 dígitos")
    
    if not nite.isdigit():
        raise ValidationError("NITE debe contener solo números")
    
    return nite

def validar_identificacion(tipo_id, identificacion):
    """
    Valida identificación según tipo
    tipo_id: '01' (Física), '02' (Jurídica), '03' (DIMEX), '04' (NITE)
    """
    validadores = {
        '01': validar_cedula_fisica,
        '02': validar_cedula_juridica,
        '03': validar_dimex,
        '04': validar_nite
    }
    
    validador = validadores.get(tipo_id)
    if not validador:
        raise ValidationError(f"Tipo de identificación inválido: {tipo_id}")
    
    return validador(identificacion)

def validar_email(email):
    """Valida formato de email"""
    if not email:
        raise ValidationError("Email es requerido")
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Formato de email inválido")
    
    return email.lower()

def validar_telefono(telefono):
    """Valida formato de teléfono costarricense"""
    if not telefono:
        return None  # Teléfono es opcional
    
    # Limpiar caracteres
    telefono = str(telefono).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    
    # Debe tener 8 dígitos (formato CR)
    if len(telefono) != 8:
        raise ValidationError("Teléfono debe tener 8 dígitos")
    
    if not telefono.isdigit():
        raise ValidationError("Teléfono debe contener solo números")
    
    return telefono

def validar_monto(monto, campo="monto"):
    """
    Valida que el monto sea positivo y tenga máximo 2 decimales
    Retorna Decimal
    """
    if monto is None:
        raise ValidationError(f"{campo} es requerido")
    
    try:
        valor = Decimal(str(monto))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{campo} inválido")
    
    if valor < 0:
        raise ValidationError(f"{campo} no puede ser negativo")
    
    # Verificar máximo 2 decimales
    if abs(valor.as_tuple().exponent) > 2:
        raise ValidationError(f"{campo} no puede tener más de 2 decimales")
    
    return valor

def validar_porcentaje(porcentaje, campo="porcentaje"):
    """
    Valida que el porcentaje esté entre 0 y 100
    Retorna Decimal
    """
    if porcentaje is None:
        raise ValidationError(f"{campo} es requerido")
    
    try:
        valor = Decimal(str(porcentaje))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{campo} inválido")
    
    if valor < 0 or valor > 100:
        raise ValidationError(f"{campo} debe estar entre 0 y 100")
    
    return valor

def validar_cantidad(cantidad, campo="cantidad"):
    """
    Valida que la cantidad sea positiva
    Retorna Decimal
    """
    if cantidad is None:
        raise ValidationError(f"{campo} es requerida")
    
    try:
        valor = Decimal(str(cantidad))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{campo} inválida")
    
    if valor <= 0:
        raise ValidationError(f"{campo} debe ser mayor a 0")
    
    return valor

def validar_consecutivo(consecutivo):
    """
    Valida formato de consecutivo (20 dígitos)
    Formato: SSSTTTTTDDCCCCCCCCCC
    SSS = Sucursal (3)
    TTTTT = Terminal (5)
    DD = Tipo documento (2)
    CCCCCCCCCC = Contador (10)
    """
    if not consecutivo:
        raise ValidationError("Consecutivo es requerido")
    
    consecutivo = str(consecutivo).replace('-', '').replace(' ', '')
    
    if len(consecutivo) != 20:
        raise ValidationError("Consecutivo debe tener 20 dígitos")
    
    if not consecutivo.isdigit():
        raise ValidationError("Consecutivo debe contener solo números")
    
    return consecutivo

def validar_clave(clave):
    """
    Valida formato de clave numérica (50 dígitos)
    Formato según normativa MH v4.4
    """
    if not clave:
        raise ValidationError("Clave es requerida")
    
    clave = str(clave).replace('-', '').replace(' ', '')
    
    if len(clave) != 50:
        raise ValidationError("Clave debe tener 50 dígitos")
    
    if not clave.isdigit():
        raise ValidationError("Clave debe contener solo números")
    
    return clave

def validar_fecha(fecha, campo="fecha"):
    """Valida que la fecha sea válida"""
    if not fecha:
        raise ValidationError(f"{campo} es requerida")
    
    if isinstance(fecha, datetime):
        return fecha
    
    # Intentar parsear string
    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S"
    ]
    
    for formato in formatos:
        try:
            return datetime.strptime(str(fecha), formato)
        except ValueError:
            continue
    
    raise ValidationError(f"{campo} tiene formato inválido")

def validar_moneda(moneda):
    """Valida código de moneda ISO 4217"""
    monedas_validas = ['CRC', 'USD', 'EUR']
    
    if not moneda:
        raise ValidationError("Moneda es requerida")
    
    moneda = str(moneda).upper()
    
    if moneda not in monedas_validas:
        raise ValidationError(f"Moneda inválida. Debe ser una de: {', '.join(monedas_validas)}")
    
    return moneda

def validar_cabys(cabys):
    """
    Valida código CABYS (Código de Bienes y Servicios)
    Formato: 13 dígitos
    """
    if not cabys:
        return None  # CABYS es opcional en algunos casos
    
    cabys = str(cabys).replace('-', '').replace(' ', '')
    
    if len(cabys) != 13:
        raise ValidationError("Código CABYS debe tener 13 dígitos")
    
    if not cabys.isdigit():
        raise ValidationError("Código CABYS debe contener solo números")
    
    return cabys

def sanitizar_texto(texto, max_length=None):
    """
    Sanitiza texto para evitar inyecciones
    Remueve caracteres peligrosos
    """
    if not texto:
        return ""
    
    # Convertir a string
    texto = str(texto)
    
    # Remover caracteres de control
    texto = ''.join(char for char in texto if ord(char) >= 32 or char in ['\n', '\r', '\t'])
    
    # Trim
    texto = texto.strip()
    
    # Limitar longitud
    if max_length and len(texto) > max_length:
        texto = texto[:max_length]
    
    return texto

# Decorador para validar datos de entrada
def validar_entrada(**validaciones):
    """
    Decorador para validar datos de entrada en rutas Flask
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request, jsonify
            
            data = request.get_json() or {}
            
            # Validar cada campo
            for campo, validador in validaciones.items():
                if campo in data:
                    try:
                        data[campo] = validador(data[campo])
                    except ValidationError as e:
                        return jsonify({
                            'success': False,
                            'error': str(e),
                            'campo': campo
                        }), 400
            
            return f(*args, **kwargs)
        return decorated
    return decorator
