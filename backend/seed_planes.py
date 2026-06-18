#!/usr/bin/env python3
"""
Script para inicializar los planes de suscripción en la base de datos
Ejecutar: python seed_planes.py
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()
from api.models import db, Plan

def seed_planes():
    """Crea los planes de suscripción por defecto"""
    
    planes_data = [
        {
            'nombre': 'Básico',
            'descripcion': 'Ideal para pequeños negocios que inician su facturación electrónica. Incluye las funcionalidades esenciales para cumplir con la normativa 4.4 del Ministerio de Hacienda.',
            'precio_mensual': 15000.00,  # CRC
            'precio_anual': 150000.00,   # CRC (10% descuento)
            'cuota_facturas': 50,
            'usuarios_incluidos': 1,
            'sucursales_incluidas': 1,
            'tiene_api_hacienda': True,
            'tiene_firma_digital': False,
            'tiene_soporte': False,
            'tiene_reportes_avanzados': False,
            'tiene_multi_moneda': False,
            'orden': 1
        },
        {
            'nombre': 'Profesional',
            'descripcion': 'Para negocios en crecimiento que necesitan más capacidad y herramientas avanzadas. Incluye firma digital y soporte básico.',
            'precio_mensual': 35000.00,  # CRC
            'precio_anual': 350000.00,   # CRC (10% descuento)
            'cuota_facturas': 200,
            'usuarios_incluidos': 3,
            'sucursales_incluidas': 2,
            'tiene_api_hacienda': True,
            'tiene_firma_digital': True,
            'tiene_soporte': True,
            'tiene_reportes_avanzados': False,
            'tiene_multi_moneda': False,
            'orden': 2
        },
        {
            'nombre': 'Enterprise',
            'descripcion': 'Solución completa para empresas con múltiples sucursales. Incluye reportes avanzados, soporte prioritario y todas las funcionalidades.',
            'precio_mensual': 75000.00,  # CRC
            'precio_anual': 750000.00,   # CRC (10% descuento)
            'cuota_facturas': 1000,
            'usuarios_incluidos': 10,
            'sucursales_incluidas': 5,
            'tiene_api_hacienda': True,
            'tiene_firma_digital': True,
            'tiene_soporte': True,
            'tiene_reportes_avanzados': True,
            'tiene_multi_moneda': True,
            'orden': 3
        },
        {
            'nombre': 'Corporativo',
            'descripcion': 'Para grandes empresas con necesidades específicas. Facturación ilimitada, múltiples sucursales, API dedicada y soporte 24/7.',
            'precio_mensual': 150000.00,  # CRC
            'precio_anual': 1500000.00,   # CRC (10% descuento)
            'cuota_facturas': 999999,  # Ilimitado
            'usuarios_incluidos': 999,  # Ilimitado
            'sucursales_incluidas': 999,  # Ilimitado
            'tiene_api_hacienda': True,
            'tiene_firma_digital': True,
            'tiene_soporte': True,
            'tiene_reportes_avanzados': True,
            'tiene_multi_moneda': True,
            'orden': 4
        }
    ]
    
    with app.app_context():
        try:
            # Verificar si ya existen planes
            planes_existentes = Plan.query.count()
            if planes_existentes > 0:
                print(f"⚠️  Ya existen {planes_existentes} planes en la base de datos.")
                respuesta = input("¿Desea recrearlos? (s/n): ")
                if respuesta.lower() != 's':
                    print("Operación cancelada.")
                    return
            
            # Eliminar planes existentes
            Plan.query.delete()
            
            # Crear nuevos planes
            for plan_data in planes_data:
                plan = Plan(**plan_data)
                db.session.add(plan)
            
            db.session.commit()
            
            print("✅ Planes de suscripción creados exitosamente:")
            print("-" * 60)
            for plan in Plan.query.order_by(Plan.orden).all():
                print(f"  {plan.orden}. {plan.nombre}")
                print(f"     Mensual: ₡{plan.precio_mensual:,.0f}")
                print(f"     Anual:   ₡{plan.precio_anual:,.0f}")
                print(f"     Cuota:   {plan.cuota_facturas} facturas/mes")
                print(f"     Usuarios: {plan.usuarios_incluidos}")
                print()
            
            print("-" * 60)
            print("✨ La base de datos está lista para suscripciones!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creando planes: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("  MUROTECH SaaS - Inicialización de Planes")
    print("=" * 60)
    print()
    seed_planes()