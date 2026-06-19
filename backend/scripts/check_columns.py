import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
from app import create_app
from app.models.base import db

app = create_app()
tablas = ['usuarios','empresas','sucursales','clientes','productos','roles','accesos_sucursal']
with app.app_context():
    with db.engine.connect() as conn:
        for tabla in tablas:
            sql = "SELECT column_name FROM information_schema.columns WHERE table_name=:t ORDER BY ordinal_position"
            r = conn.execute(db.text(sql), {"t": tabla})
            cols = [row[0] for row in r.fetchall()]
            print(f"\n{tabla}: {cols}" if cols else f"\n{tabla}: NO EXISTE")
