#!/usr/bin/env python3
"""
Script para probar el endpoint del dashboard
"""
import requests
import json

API_URL = 'http://localhost:5001'

def test_dashboard(email, password, user_type):
    print(f"\n{'='*60}")
    print(f"📊 Probando Dashboard: {user_type}")
    print(f"{'='*60}")
    
    # 1. Login
    print(f"\n1️⃣  Login con {email}...")
    response = requests.post(
        f'{API_URL}/api/login',
        json={'email': email, 'password': password}
    )
    
    if response.status_code != 200:
        print(f"❌ Login fallido: {response.json()}")
        return False
    
    data = response.json()
    token = data['token']
    user = data['user']
    print(f"✅ Login exitoso")
    print(f"   Usuario: {user['nombre']}")
    print(f"   Empresa: {user['empresa']}")
    print(f"   SuperAdmin: {user['is_superadmin']}")
    
    # 2. Obtener métricas del dashboard
    print(f"\n2️⃣  Obteniendo métricas del dashboard...")
    response = requests.get(
        f'{API_URL}/api/dashboard',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code != 200:
        print(f"❌ Error al obtener dashboard: {response.json()}")
        return False
    
    metrics = response.json()
    print(f"✅ Métricas obtenidas")
    
    # 3. Mostrar métricas
    print(f"\n📈 MÉTRICAS:")
    print(f"   Scope: {metrics.get('scope', 'N/A')}")
    print(f"   Facturas Emitidas: {metrics.get('facturasEmitidas', 0)} ({metrics.get('facturasVariacion', '0%')})")
    print(f"   Ingresos Totales: ₡{metrics.get('ingresosTotales', 0):,.2f} ({metrics.get('ingresosVariacion', '0%')})")
    print(f"   Clientes Activos: {metrics.get('clientesActivos', 0)} ({metrics.get('clientesVariacion', '0%')})")
    print(f"   Tasa de Conversión: {metrics.get('tasaConversion', '0%')} ({metrics.get('tasaVariacion', '0%')})")
    
    if 'periodo' in metrics:
        print(f"\n📅 PERIODO:")
        print(f"   Mes Actual: {metrics['periodo']['mes_actual']}")
        print(f"   Mes Anterior: {metrics['periodo']['mes_anterior']}")
    
    print(f"\n📋 ACTIVIDAD RECIENTE:")
    actividad = metrics.get('actividadReciente', [])
    if actividad:
        for i, item in enumerate(actividad[:5], 1):
            print(f"   {i}. {item['clienteNombre']} - ₡{item['monto']:,.2f} - {item['estado']}")
    else:
        print("   (Sin actividad reciente)")
    
    return True

def main():
    print("="*60)
    print("🧪 PRUEBA DE DASHBOARD - MUROTECH")
    print("="*60)
    
    # Test con Administrador
    admin_ok = test_dashboard(
        'admin@murotech.com',
        'Admin2026!',
        'ADMINISTRADOR'
    )
    
    # Resumen
    print(f"\n{'='*60}")
    print("📊 RESUMEN")
    print(f"{'='*60}")
    print(f"Administrador: {'✅ OK' if admin_ok else '❌ FAIL'}")
    
    if admin_ok:
        print("\n🎉 ¡Dashboard funcionando correctamente!")
        print("\n💡 NOTA: Los datos mostrados son del mes actual.")
        print("   Si no hay facturas, los contadores estarán en 0.")
        print("   Para ver datos reales, crea facturas desde el sistema.")
    else:
        print("\n⚠️  Hay problemas con el dashboard")

if __name__ == '__main__':
    main()
