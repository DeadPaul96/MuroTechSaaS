"""Tests E2E: flujo de emisión de factura (crear → listar → ver detalle)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from app.models import db, Empresa, Sucursal, Usuario, Rol, AccesoSucursal, Cliente


@pytest.fixture
def auth_client(app, client):
    """Crea empresa, usuario, cliente y devuelve client autenticado."""
    with app.app_context():
        empresa = Empresa(
            razon_social='Test E2E SA',
            nombre_comercial='TestE2E',
            cedula_juridica='3101999999',
            tipo_identificacion='02',
            email_contacto='e2e@test.com',
            plan_tipo='mensual',
            plan_cuota=100,
            plan_estado='activo',
            is_active=True,
        )
        db.session.add(empresa)
        db.session.flush()

        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre='Sede Principal',
            numero_sucursal='001',
            terminal='00001',
            provincia='1', canton='01', distrito='01',
        )
        db.session.add(sucursal)
        db.session.flush()

        rol = Rol.query.filter_by(nombre='Administrador').first()
        if not rol:
            rol = Rol(nombre='Administrador', descripcion='Admin')
            db.session.add(rol)
            db.session.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nombre='E2E User',
            email='e2e@test.com',
            is_active=True,
        )
        usuario.set_password('Test123!')
        db.session.add(usuario)
        db.session.flush()

        acceso = AccesoSucursal(usuario_id=usuario.id, sucursal_id=sucursal.id, rol_id=rol.id)
        db.session.add(acceso)

        cliente = Cliente(
            empresa_id=empresa.id,
            nombre='Cliente E2E',
            tipo_id='01',
            identificacion='111111111',
            email='cliente@test.com',
        )
        db.session.add(cliente)
        db.session.commit()

        resp = client.post('/api/login', json={'email': 'e2e@test.com', 'password': 'Test123!'})
        token = resp.get_json()['token']

        return {
            'client': client,
            'token': token,
            'sucursal_id': sucursal.id,
            'cliente_id': cliente.id,
            'empresa_id': empresa.id,
        }


class TestFacturaE2E:
    """Flujo completo: crear factura → listar → ver detalle → descargar."""

    def _auth_headers(self, auth_client):
        return {
            'Authorization': f'Bearer {auth_client["token"]}',
            'X-Sucursal-ID': auth_client['sucursal_id'],
        }

    def test_crear_factura_y_listar(self, auth_client):
        headers = self._auth_headers(auth_client)
        cliente_id = auth_client['cliente_id']

        # Crear factura
        resp = auth_client['client'].post('/api/facturas', json={
            'tipoDoc': '01',
            'cliente_id': cliente_id,
            'condicionVenta': '01',
            'medioPago': '01',
            'moneda': 'CRC',
            'detalles': [{
                'descripcion': 'Producto Test',
                'cantidad': 2,
                'precio': 5000,
                'descuento': 0,
                'impuesto': 13,
            }],
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'consecutivo' in data
        assert 'clave' in data
        assert data['message'] == 'Documento emitido y almacenado correctamente.'

        # Listar facturas
        resp = auth_client['client'].get('/api/facturas', headers=headers)
        assert resp.status_code == 200
        facturas = resp.get_json()
        assert len(facturas) >= 1
        assert facturas[0]['estado'] is not None

    def test_crear_factura_sin_detalles_falla(self, auth_client):
        headers = self._auth_headers(auth_client)
        resp = auth_client['client'].post('/api/facturas', json={
            'tipoDoc': '01',
            'detalles': [],
        }, headers=headers)
        assert resp.status_code == 400

    def test_crear_nc_sin_referencia_falla(self, auth_client):
        headers = self._auth_headers(auth_client)
        resp = auth_client['client'].post('/api/facturas', json={
            'tipoDoc': '03',
            'cliente_id': auth_client['cliente_id'],
            'detalles': [{
                'descripcion': 'Item NC',
                'cantidad': 1,
                'precio': 1000,
                'impuesto': 13,
            }],
        }, headers=headers)
        assert resp.status_code == 400
        assert 'referencia' in resp.get_json().get('message', '').lower()

    def test_obtener_detalle_factura(self, auth_client):
        headers = self._auth_headers(auth_client)

        # Crear factura
        resp = auth_client['client'].post('/api/facturas', json={
            'tipoDoc': '01',
            'cliente_id': auth_client['cliente_id'],
            'detalles': [{
                'descripcion': 'Producto Detalle Test',
                'cantidad': 1,
                'precio': 10000,
                'impuesto': 13,
            }],
        }, headers=headers)
        factura_id = resp.get_json()['id']

        # Obtener detalle
        resp = auth_client['client'].get(f'/api/facturas/{factura_id}', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['consecutivo'] is not None
        assert len(data['detalle']) == 1
        assert float(data['detalle'][0]['precio']) == 10000

    def test_obtener_consecutivo_siguiente(self, auth_client):
        headers = self._auth_headers(auth_client)
        resp = auth_client['client'].get('/api/facturas/consecutivo?tipo=01', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'consecutivo' in data
        assert len(data['consecutivo']) == 20

    def test_config_publica(self, auth_client):
        resp = auth_client['client'].get('/api/v1/config')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['app_name'] == 'MUROTECH SaaS'
        assert len(data['supported_doc_types']) >= 7
