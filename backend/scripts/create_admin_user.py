#!/usr/bin/env python3
"""Crea usuario administrador de empresa (requiere DATABASE_URL en .env)."""
import uuid
from werkzeug.security import generate_password_hash

from db_conn import get_psycopg2_connection


def main():
    conn = get_psycopg2_connection()
    cur = conn.cursor()

    print('=' * 60)
    print('CREANDO USUARIO ADMINISTRADOR')
    print('=' * 60)

    empresa_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO empresas (
            id, razon_social, nombre_comercial, cedula_juridica,
            tipo_identificacion, is_active, plan_estado, plan_tipo
        ) VALUES (
            %s, 'Empresa Demo MUROTECH', 'Demo Corp', '3101234567',
            '02', true, 'activo', 'premium'
        )
        ON CONFLICT (cedula_juridica) DO UPDATE
        SET is_active = true, plan_estado = 'activo'
        RETURNING id
    """, (empresa_id,))
    result = cur.fetchone()
    empresa_id = result[0] if result else empresa_id

    sucursal_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO sucursales (
            id, empresa_id, nombre, numero_sucursal, terminal, direccion
        ) VALUES (
            %s, %s, 'Sucursal Principal', '001', '00001', 'San José, Costa Rica'
        )
        ON CONFLICT DO NOTHING
        RETURNING id
    """, (sucursal_id, empresa_id))
    result = cur.fetchone()
    if not result:
        cur.execute('SELECT id FROM sucursales WHERE empresa_id = %s LIMIT 1', (empresa_id,))
        sucursal_id = cur.fetchone()[0]
    else:
        sucursal_id = result[0]

    cur.execute("SELECT id FROM roles WHERE nombre = 'Administrador'")
    rol_admin_id = cur.fetchone()[0]

    password_hash = generate_password_hash('Admin2026!')
    cur.execute('SELECT id FROM usuarios WHERE email = %s', ('admin@murotech.com',))
    existe = cur.fetchone()
    if existe:
        cur.execute("""
            UPDATE usuarios
            SET password_hash = %s, is_active = true, empresa_id = %s
            WHERE email = 'admin@murotech.com'
            RETURNING id
        """, (password_hash, empresa_id))
    else:
        usuario_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO usuarios (
                id, empresa_id, nombre, email, password_hash,
                is_superadmin, is_active, pantallas_asignadas
            ) VALUES (
                %s, %s, 'Administrador Demo', 'admin@murotech.com', %s,
                false, true, 'facturacion,inventario,clientes'
            )
            RETURNING id
        """, (usuario_id, empresa_id, password_hash))
    usuario_id = cur.fetchone()[0]

    cur.execute("""
        SELECT id FROM accesos_sucursal
        WHERE usuario_id = %s AND sucursal_id = %s
    """, (usuario_id, sucursal_id))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO accesos_sucursal (id, usuario_id, sucursal_id, rol_id)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid.uuid4()), usuario_id, sucursal_id, rol_admin_id))

    conn.commit()
    cur.close()
    conn.close()
    print('Listo. admin@murotech.com / Admin2026!')


if __name__ == '__main__':
    main()
