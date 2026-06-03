"""
Script de verificación de APIs - MUROTECH
Verifica que todas las rutas estén funcionando correctamente
"""
import requests
import json
from datetime import datetime

API_BASE = 'http://localhost:5001/api'
TOKEN = None

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, status, message=""):
    symbol = f"{Colors.GREEN}✓{Colors.END}" if status else f"{Colors.RED}✗{Colors.END}"
    print(f"{symbol} {name}")
    if message:
        print(f"  {Colors.YELLOW}{message}{Colors.END}")

def test_health():
    """Test 1: Health Check"""
    try:
        response = requests.get(f'{API_BASE}/health', timeout=5)
        success = response.status_code == 200
        print_test("Health Check", success, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False

def test_login():
    """Test 2: Login SuperAdmin"""
    global TOKEN
    try:
        response = requests.post(f'{API_BASE}/login', json={
            'email': 'superadmin@murotech.com',
            'password': 'SuperAdmin2026!'
        }, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            TOKEN = data.get('token')
            success = TOKEN is not None
            print_test("Login SuperAdmin", success, f"Token obtenido: {TOKEN[:20]}..." if TOKEN else "No token")
            return success
        else:
            print_test("Login SuperAdmin", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_test("Login SuperAdmin", False, str(e))
        return False

def test_superadmin_dashboard():
    """Test 3: Dashboard SuperAdmin"""
    if not TOKEN:
        print_test("Dashboard SuperAdmin", False, "No hay token")
        return False
    
    try:
        response = requests.get(
            f'{API_BASE}/supadmin/dashboard',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=5
        )
        success = response.status_code == 200
        if success:
            data = response.json()
            metrics = data.get('metrics', {})
            print_test("Dashboard SuperAdmin", success, 
                      f"Empresas: {metrics.get('total_empresas')}, Usuarios: {metrics.get('total_usuarios')}")
        else:
            print_test("Dashboard SuperAdmin", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Dashboard SuperAdmin", False, str(e))
        return False

def test_superadmin_empresas():
    """Test 4: Listar Empresas"""
    if not TOKEN:
        print_test("Listar Empresas", False, "No hay token")
        return False
    
    try:
        response = requests.get(
            f'{API_BASE}/supadmin/empresas',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=5
        )
        success = response.status_code == 200
        if success:
            data = response.json()
            count = len(data.get('empresas', []))
            print_test("Listar Empresas", success, f"Total: {count} empresas")
        else:
            print_test("Listar Empresas", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Listar Empresas", False, str(e))
        return False

def test_superadmin_no_company_routes():
    """Test 5: SuperAdmin no accede a rutas de empresa/Emisor"""
    if not TOKEN:
        print_test("SuperAdmin no company routes", False, "No hay token")
        return False
    
    try:
        response = requests.get(
            f'{API_BASE}/usuarios',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=5
        )
        success = response.status_code == 403
        print_test("SuperAdmin no company routes", success, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("SuperAdmin no company routes", False, str(e))
        return False


def test_superadmin_usuarios():
    """Test 5: Listar Usuarios"""
    if not TOKEN:
        print_test("Listar Usuarios", False, "No hay token")
        return False
    
    try:
        response = requests.get(
            f'{API_BASE}/supadmin/usuarios',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=5
        )
        success = response.status_code == 200
        if success:
            data = response.json()
            count = len(data.get('usuarios', []))
            print_test("Listar Usuarios", success, f"Total: {count} usuarios")
        else:
            print_test("Listar Usuarios", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Listar Usuarios", False, str(e))
        return False

def test_superadmin_roles():
    """Test 6: Listar Roles"""
    if not TOKEN:
        print_test("Listar Roles", False, "No hay token")
        return False
    
    try:
        response = requests.get(
            f'{API_BASE}/supadmin/roles',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=5
        )
        success = response.status_code == 200
        if success:
            data = response.json()
            count = len(data.get('roles', []))
            print_test("Listar Roles", success, f"Total: {count} roles")
        else:
            print_test("Listar Roles", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Listar Roles", False, str(e))
        return False

def test_tipo_cambio():
    """Test 7: Tipo de Cambio"""
    try:
        response = requests.get(f'{API_BASE}/tipo-cambio', timeout=5)
        success = response.status_code == 200
        if success:
            data = response.json()
            print_test("Tipo de Cambio", success, f"Venta: ₡{data.get('venta')}")
        else:
            print_test("Tipo de Cambio", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Tipo de Cambio", False, str(e))
        return False

def test_server_time():
    """Test 8: Server Time"""
    try:
        response = requests.get(f'{API_BASE}/time', timeout=5)
        success = response.status_code == 200
        if success:
            data = response.json()
            print_test("Server Time", success, f"Fecha: {data.get('date')}")
        else:
            print_test("Server Time", False, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Server Time", False, str(e))
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}VERIFICACIÓN DE APIs - MUROTECH{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    tests = [
        ("Health Check", test_health),
        ("Login SuperAdmin", test_login),
        ("Dashboard SuperAdmin", test_superadmin_dashboard),
        ("Listar Empresas", test_superadmin_empresas),
        ("SuperAdmin no company routes", test_superadmin_no_company_routes),
        ("Listar Usuarios", test_superadmin_usuarios),
        ("Listar Roles", test_superadmin_roles),
        ("Tipo de Cambio", test_tipo_cambio),
        ("Server Time", test_server_time),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
        print()
    
    # Resumen
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}RESUMEN{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests pasados{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ Todas las APIs están funcionando correctamente{Colors.END}\n")
    else:
        print(f"{Colors.RED}✗ Algunas APIs tienen problemas{Colors.END}\n")

if __name__ == '__main__':
    main()
