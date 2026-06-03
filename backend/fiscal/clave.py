"""Clave y consecutivo MH v4.4."""
import secrets
from datetime import datetime


def calcular_digito_verificador(clave_sin_verificador: str) -> str:
    pesos = [3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * pesos[i % len(pesos)] for i, d in enumerate(reversed(clave_sin_verificador)))
    resto = total % 11
    verificador = 11 - resto
    if verificador == 11:
        return '0'
    if verificador == 10:
        return '1'
    return str(verificador)


def generar_consecutivo(sucursal, tipo_doc, contador) -> str:
    suc = str(sucursal.numero_sucursal).zfill(3)
    ter = str(sucursal.terminal).zfill(5)
    tipo = str(tipo_doc).zfill(2)
    cont = str(contador).zfill(10)
    return f'{suc}{ter}{tipo}{cont}'


def generar_clave(empresa, consecutivo: str, situacion: str = '1') -> str:
    pais = '506'
    fecha = datetime.utcnow().strftime('%d%m%y')
    cedula = str(empresa.cedula_juridica).replace('-', '').zfill(12)
    seguridad_sin_verificador = str(secrets.randbelow(10_000_000)).zfill(7)
    clave_sin_verificador = f'{pais}{fecha}{cedula}{consecutivo}{situacion}{seguridad_sin_verificador}'
    verificador = calcular_digito_verificador(clave_sin_verificador)
    seguridad = f'{seguridad_sin_verificador}{verificador}'
    return f'{pais}{fecha}{cedula}{consecutivo}{situacion}{seguridad}'
