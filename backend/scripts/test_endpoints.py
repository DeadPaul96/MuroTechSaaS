import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from app import create_app
app = create_app()
client = app.test_client()

# Login
r = client.post('/api/login', json={'email': 'admin@murotech.com', 'password': 'Admin2026!'})
token = r.get_json().get('token')
print(f"Login: {r.status_code} - token={bool(token)}")

headers = {'Authorization': f'Bearer {token}'}

# Test reportes
r2 = client.get('/api/reportes', headers=headers)
print(f"GET /api/reportes: {r2.status_code}")
d2 = r2.get_json()
if r2.status_code == 200:
    print(f"  kpis.ventas={d2['kpis']['ventas']}  kpis.sku_total={d2['kpis']['sku_total']}")
else:
    print(f"  ERROR: {str(d2.get('error',''))[:200]}")

# Test auditoria
r3 = client.get('/api/auditoria', headers=headers)
print(f"GET /api/auditoria: {r3.status_code}")
d3 = r3.get_json()
if r3.status_code == 200:
    print(f"  comprobantes={len(d3.get('comprobantes',[]))}  movimientos={len(d3.get('movimientos',[]))}")
else:
    print(f"  ERROR: {str(d3.get('error',''))[:200]}")
