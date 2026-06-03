#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar la emisión de facturas y ver el error exacto
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.app import app, db
from api.models import Usuario, Empresa, Sucursal, Cliente, Producto, Factura
import json
import jwt
from datetime import datetime, timedelta

# Crear contexto de aplicación
with app.app_context():
    # Obtener datos de prueba - usar el usuario admin
    usuario = Usuario.query.filter_by(email='admin@murotech.com').first()
    if not usuario:
        print("[FAIL] No hay usuario admin en la base de datos")
        sys.exit(1)
    
    empresa = usuario.empresa
    sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
    if not sucursal:
        print("[FAIL] No hay sucursales para esta empresa")
        sys.exit(1)
    
    cliente = Cliente.query.filter_by(empresa_id=empresa.id).first()
    if not cliente:
        print("[FAIL] No hay clientes en la base de datos")
        sys.exit(1)
    
    producto = Producto.query.filter_by(empresa_id=empresa.id).first()
    if not producto:
        print("[FAIL] No hay productos en la base de datos")
        sys.exit(1)
    
    print(f"[OK] Usuario: {usuario.email}")
    print(f"[OK] Empresa: {empresa.razon_social}")
    print(f"[OK] Sucursal: {sucursal.nombre} (ID: {sucursal.id})")
    print(f"[OK] Cliente: {cliente.nombre} (ID: {cliente.id})")
    print(f"[OK] Producto: {producto.descripcion} (ID: {producto.id})")
    print()
    
    # Preparar payload de prueba
    payload = {
        "cliente_id": cliente.id,  # UUID string
        "tipoDoc": "01",
        "condicionVenta": "01",
        "medioPago": "01",
        "moneda": "CRC",
        "detalles": [
            {
                "producto_id": producto.id,
                "descripcion": producto.descripcion,
                "cantidad": 1,
                "precio": float(producto.precio_venta),
                "descuento": 0,
                "impuesto": 13
            }
        ]
    }
    
    print("[SEND] Payload a enviar:")
    print(json.dumps(payload, indent=2, default=str))
    print()
    
    # Crear un token JWT válido
    token_payload = {
        'user_id': usuario.id,
        'email': usuario.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
    print(f"[OK] Token generado: {token[:20]}...")
    print()
    
    # Simular la solicitud POST con el token
    with app.test_client() as client:
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Sucursal-ID': str(sucursal.id),
            'Content-Type': 'application/json'
        }
        
        print("[SEND] Enviando solicitud POST /api/facturas...")
        try:
            response = client.post('/api/facturas', 
                                  json=payload,
                                  headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json, indent=2, default=str)}")
            
            if response.status_code != 201:
                print("\n[FAIL] ERROR EN LA EMISION")
                print(f"Detalles: {response.json}")
            else:
                print("\n[OK] EMISION EXITOSA")
            
        except Exception as e:
            print(f"[FAIL] Excepcion: {str(e)}")
            traceback.print_exc()
