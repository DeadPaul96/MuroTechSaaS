"""
Script para probar la API CABYS del Ministerio de Hacienda
"""
import requests

def test_api_hacienda():
    """Prueba directa a la API del Ministerio de Hacienda"""
    print("=" * 60)
    print("PRUEBA 1: API del Ministerio de Hacienda")
    print("=" * 60)
    
    query = "computadoras"
    url = f"https://api.hacienda.go.cr/fe/cabys?q={query}"
    
    print(f"\nConsultando: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Tipo de respuesta: {type(data)}")
            print(f"Cantidad de resultados: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list) and len(data) > 0:
                print("\nPrimeros 3 resultados:")
                for i, item in enumerate(data[:3], 1):
                    print(f"\n{i}. {item}")
            else:
                print("\nRespuesta completa:")
                print(data)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_backend_local():
    """Prueba el backend local"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Backend Local")
    print("=" * 60)
    
    query = "computadoras"
    url = f"http://localhost:5001/api/cabys/search?q={query}"
    
    print(f"\nConsultando: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nRespuesta del backend:")
            print(f"Success: {data.get('success')}")
            print(f"Count: {data.get('count')}")
            print(f"Resultados: {len(data.get('results', []))}")
            
            if data.get('results'):
                print("\nPrimeros 3 resultados:")
                for i, item in enumerate(data['results'][:3], 1):
                    print(f"\n{i}. Código: {item.get('codigo')}")
                    print(f"   Descripción: {item.get('descripcion')}")
                    print(f"   IVA: {item.get('impuesto')}%")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al backend local.")
        print("Asegúrate de que el servidor esté corriendo en http://localhost:5001")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_hacienda()
    test_backend_local()
    
    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)
