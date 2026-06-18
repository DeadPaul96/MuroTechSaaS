"""Tests E2E: flujo de pagos (checkout → confirmar → verificar estado)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from app.models import db, Empresa, Sucursal, Usuario, Rol, AccesoSucursal


@pytest.fixture
def setup_payment(app, client):
    with app.app_context():
        empresa = Empresa(
            razon_social='Pago Test SA',
            nombre_comercial='PagoTest',
            cedula_juridica='3101888888',
            tipo_identificacion='02',
            email_contacto='pago@test.com',
            plan_tipo='mensual',
            plan_cuota=50,
            plan_estado='pendiente',
            is_active=False,
        )
        db.session.add(empresa)
        db.session.flush()

        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre='Sede',
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
            nombre='Pago User',
            email='pago@test.com',
            is_active=False,
        )
        usuario.set_password('Test123!')
        db.session.add(usuario)
        db.session.flush()

        acceso = AccesoSucursal(usuario_id=usuario.id, sucursal_id=sucursal.id, rol_id=rol.id)
        db.session.add(acceso)
        db.session.commit()

        return {'empresa_id': empresa.id, 'usuario_id': usuario.id}


class TestPaymentFlow:
    """Flujo: crear checkout → confirmar pago → verificar estado."""

    def test_crear_checkout(self, client, setup_payment):
        resp = client.post('/api/pagos/checkout', json={
            'empresa_id': setup_payment['empresa_id'],
            'plan_tipo': 'mensual',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'pending'
        assert 'checkout_url' in data
        assert 'payment_id' in data

    def test_confirmar_pago(self, client, setup_payment):
        # Crear checkout
        resp = client.post('/api/pagos/checkout', json={
            'empresa_id': setup_payment['empresa_id'],
            'plan_tipo': 'mensual',
        })
        payment_id = resp.get_json()['payment_id']

        # Confirmar pago
        resp = client.post('/api/pagos/confirmar', json={
            'payment_id': payment_id,
            'provider': 'stripe',
            'transaction_id': 'txn_test_123',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['message'] == 'Pago confirmado y cuenta activada.'

    def test_confirmar_pago_ya_procesado(self, client, setup_payment):
        # Crear y confirmar
        resp = client.post('/api/pagos/checkout', json={
            'empresa_id': setup_payment['empresa_id'],
            'plan_tipo': 'mensual',
        })
        payment_id = resp.get_json()['payment_id']
        client.post('/api/pagos/confirmar', json={'payment_id': payment_id})

        # Intentar confirmar de nuevo
        resp = client.post('/api/pagos/confirmar', json={'payment_id': payment_id})
        assert resp.status_code == 400

    def test_estado_pago(self, client, setup_payment):
        resp = client.post('/api/pagos/checkout', json={
            'empresa_id': setup_payment['empresa_id'],
            'plan_tipo': 'mensual',
        })
        payment_id = resp.get_json()['payment_id']

        resp = client.get(f'/api/pagos/estatus/{payment_id}')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'pending'

    def test_checkout_empresa_inexistente(self, client, setup_payment):
        resp = client.post('/api/pagos/checkout', json={
            'empresa_id': 'no-existe',
            'plan_tipo': 'mensual',
        })
        assert resp.status_code == 404
