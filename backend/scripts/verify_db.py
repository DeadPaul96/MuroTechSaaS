#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('Configure DATABASE_URL en .env')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("\n========== USUARIOS ==========")
cur.execute("SELECT nombre, email, is_superadmin, is_active, empresa_id FROM usuarios ORDER BY is_superadmin DESC")
for u in cur.fetchall():
    print(f"  Nombre:      {u[0]}")
    print(f"  Email:       {u[1]}")
    print(f"  SuperAdmin:  {u[2]}")
    print(f"  Activo:      {u[3]}")
    print(f"  Empresa ID:  {u[4]}")
    print()

print("========== EMPRESAS ==========")
cur.execute("SELECT razon_social, cedula_juridica, is_active, plan_estado, plan_tipo FROM empresas")
for e in cur.fetchall():
    print(f"  Razón Social:  {e[0]}")
    print(f"  Cédula:        {e[1]}")
    print(f"  Activa:        {e[2]}")
    print(f"  Plan Estado:   {e[3]}")
    print(f"  Plan Tipo:     {e[4]}")
    print()

print("========== SUCURSALES ==========")
cur.execute("SELECT nombre, numero_sucursal, terminal FROM sucursales")
for s in cur.fetchall():
    print(f"  Nombre:    {s[0]}")
    print(f"  Número:    {s[1]}")
    print(f"  Terminal:  {s[2]}")
    print()

print("========== ACCESOS SUCURSAL ==========")
cur.execute("""
    SELECT u.email, s.nombre, r.nombre
    FROM accesos_sucursal a
    JOIN usuarios u ON u.id = a.usuario_id
    JOIN sucursales s ON s.id = a.sucursal_id
    JOIN roles r ON r.id = a.rol_id
""")
for a in cur.fetchall():
    print(f"  Usuario:   {a[0]}")
    print(f"  Sucursal:  {a[1]}")
    print(f"  Rol:       {a[2]}")
    print()

print("========== ROLES ==========")
cur.execute("SELECT nombre, descripcion FROM roles")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.close()
conn.close()
