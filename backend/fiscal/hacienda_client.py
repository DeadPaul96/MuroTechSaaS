"""Cliente OAuth + recepción MH Costa Rica (staging/prod)."""
import base64
import os
from datetime import datetime, timezone, timedelta

import requests

CR_TZ = timezone(timedelta(hours=-6))

URLS = {
    'stag': {
        'token': 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token',
        'recepcion': 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion',
        'comprobantes': 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/comprobantes',
        'client_id': 'api-stag',
    },
    'prod': {
        'token': 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token',
        'recepcion': 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion',
        'comprobantes': 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/comprobantes',
        'client_id': 'api-prod',
    },
}


class HaciendaError(Exception):
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class HaciendaClient:
    def __init__(self, ambiente: str = 'stag'):
        self.ambiente = 'prod' if ambiente in ('prod', 'produccion', 'production') else 'stag'
        cfg = URLS[self.ambiente]
        self.token_url = os.environ.get('HACIENDA_TOKEN_URL', cfg['token'])
        self.recepcion_url = os.environ.get('HACIENDA_API_URL', cfg['recepcion']).rstrip('/')
        self.comprobantes_url = os.environ.get(
            'HACIENDA_COMPROBANTES_URL', cfg['comprobantes']
        ).rstrip('/')
        self.client_id = os.environ.get('HACIENDA_CLIENT_ID', cfg['client_id'])
        self.client_secret = os.environ.get('HACIENDA_CLIENT_SECRET', '')
        self.timeout = int(os.environ.get('HACIENDA_TIMEOUT', '30'))

    def obtener_token(self, username: str, password: str) -> str:
        if not username or not password:
            raise HaciendaError('Credenciales ATV (usuario/contraseña) requeridas')
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'username': username,
            'password': password,
        }
        if self.client_secret:
            data['client_secret'] = self.client_secret
        res = requests.post(self.token_url, data=data, timeout=self.timeout)
        if not res.ok:
            raise HaciendaError(
                f'Token MH rechazado ({res.status_code})',
                status_code=res.status_code,
                payload=res.text,
            )
        token = res.json().get('access_token')
        if not token:
            raise HaciendaError('Respuesta sin access_token', payload=res.text)
        return token

    @staticmethod
    def _fecha_emision_iso(dt=None) -> str:
        dt = dt or datetime.now(CR_TZ)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CR_TZ)
        return dt.astimezone(CR_TZ).strftime('%Y-%m-%dT%H:%M:%S-06:00')

    def enviar_comprobante(
        self,
        *,
        clave: str,
        xml_bytes: bytes,
        emisor_tipo: str,
        emisor_numero: str,
        receptor_tipo: str | None = None,
        receptor_numero: str | None = None,
        fecha_emision=None,
        username: str,
        password: str,
    ) -> dict:
        token = self.obtener_token(username, password)
        emisor_tipo = str(emisor_tipo or '02')[-2:].zfill(2)
        payload = {
            'clave': str(clave).replace('-', '')[:50],
            'fecha': self._fecha_emision_iso(fecha_emision),
            'emisor': {
                'tipoIdentificacion': emisor_tipo,
                'numeroIdentificacion': str(emisor_numero).replace('-', ''),
            },
            'comprobanteXml': base64.b64encode(xml_bytes).decode('ascii'),
        }
        if receptor_numero:
            payload['receptor'] = {
                'tipoIdentificacion': str(receptor_tipo or '01')[-2:].zfill(2),
                'numeroIdentificacion': str(receptor_numero).replace('-', ''),
            }
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        res = requests.post(self.recepcion_url, json=payload, headers=headers, timeout=self.timeout)
        try:
            body = res.json()
        except ValueError:
            body = {'raw': res.text}
        if not res.ok:
            raise HaciendaError(
                f'Recepción MH rechazada ({res.status_code})',
                status_code=res.status_code,
                payload=body,
            )
        return {'status_code': res.status_code, 'body': body, 'ambiente': self.ambiente}

    def consultar_estado_recepcion(self, clave: str, username: str, password: str) -> dict:
        """GET /recepcion/{clave} — estado del comprobante en MH."""
        token = self.obtener_token(username, password)
        clave_limpia = str(clave).replace('-', '')[:50]
        url = f'{self.recepcion_url}/{clave_limpia}'
        headers = {'Authorization': f'Bearer {token}'}
        res = requests.get(url, headers=headers, timeout=self.timeout)
        try:
            body = res.json()
        except ValueError:
            body = {'raw': res.text}
        if not res.ok:
            raise HaciendaError(
                f'Consulta MH rechazada ({res.status_code})',
                status_code=res.status_code,
                payload=body,
            )
        return {'status_code': res.status_code, 'body': body, 'ambiente': self.ambiente, 'clave': clave_limpia}

    def obtener_comprobante(self, clave: str, username: str, password: str) -> dict:
        """GET /comprobantes/{clave} — XML sellado u otros datos del comprobante."""
        token = self.obtener_token(username, password)
        clave_limpia = str(clave).replace('-', '')[:50]
        url = f'{self.comprobantes_url}/{clave_limpia}'
        headers = {'Authorization': f'Bearer {token}'}
        res = requests.get(url, headers=headers, timeout=self.timeout)
        try:
            body = res.json()
        except ValueError:
            body = {'raw': res.text}
        if not res.ok:
            raise HaciendaError(
                f'Comprobante MH no disponible ({res.status_code})',
                status_code=res.status_code,
                payload=body,
            )
        return {'status_code': res.status_code, 'body': body, 'ambiente': self.ambiente, 'clave': clave_limpia}


def mapear_estado_mh(respuesta: dict) -> str:
    """Traduce respuesta JSON de MH a estado interno de factura."""
    if not isinstance(respuesta, dict):
        return 'Pendiente'
    estado = (
        respuesta.get('ind-estado')
        or respuesta.get('indEstado')
        or respuesta.get('estado')
        or ''
    )
    e = str(estado).lower()
    if 'acept' in e:
        return 'Aceptada MH'
    if 'rechaz' in e:
        return 'Rechazada MH'
    if 'proces' in e:
        return 'En proceso MH'
    return 'Pendiente MH'
