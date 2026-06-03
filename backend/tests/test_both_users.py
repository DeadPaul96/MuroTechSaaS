#!/usr/bin/env python3
"""
Script para probar el login de ambos usuarios
"""
import requests
import json

API_URL = 'http://localhost:5001'

def test_login(email, password, user_type):
    print(f"\n{'='*60}")
    print(f"🔐 Probando login: {user_type}")
    print(f"{'='*60}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    
    try:
        response = requests.post(
            f'{API_URL}/api/login',
            json={'email': email, 'password': password},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ LOGIN EXITOSO")
            print(f"Token: {data['token'][:50]}...")
            print(f"\nDatos del usuario:")
            print(f"  - Nombre: {data['user']['nombre']}")
            print(f"  - Email: {data['user']['email']}")
            print(f"  - Empresa: {data['user']['empresa']}")
            print(f"  - Es SuperAdmin: {data['user']['is_superadmin']}")
            print(f"  - Pantallas asignadas: {', '.join(data['user']['pantallas'])}")
            print(f"\nAccesos a sucursales:")
            for acceso in data['accesos']:
                print(f"  - {acceso['nombre']} (Rol: {acceso['rol']})")
            return True
        else:
            print(f"\n❌ LOGIN FALLIDO")
            print(f"Status: {response.status_code}")
            print(f"Mensaje: {response.json().get('message', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN")
        print(f"Error: {str(e)}")
        return False

def main():
    print("="*60)
    print("🧪 PRUEBA DE LOGIN - AMBOS USUARIOS")
    print("="*60)
    
    # Test SuperAdmin
    superadmin_ok = test_login(
        'superadmin@murotech.com',
        'SuperAdmin2026!',
        'SUPERADMIN'
    )
    
    # Test Administrador
    admin_ok = test_login(
        'admin@murotech.com',
        'Admin2026!',
        'ADMINISTRADOR'
    )
    
    # Resumen
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE PRUEBAS")
    print(f"{'='*60}")
    print(f"SuperAdmin: {'✅ OK' if superadmin_ok else '❌ FAIL'}")
    print(f"Administrador: {'✅ OK' if admin_ok else '❌ FAIL'}")
    
    if superadmin_ok and admin_ok:
        print("\n🎉 ¡Todos los usuarios funcionan correctamente!")
    else:
        print("\n⚠️  Algunos usuarios tienen problemas")

if __name__ == '__main__':
    main()
