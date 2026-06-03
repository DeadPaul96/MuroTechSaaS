#!/usr/bin/env python3
"""
Script de limpieza y configuracion de Supabase para MUROTECH
"""
import os

from db_conn import get_psycopg2_connection


def conectar():
    """Establece conexion a Supabase"""
    return get_psycopg2_connection()

def verificar_datos():
    """Verifica datos existentes"""
    conn = conectar()
    cur = conn.cursor()
    
    print("=" * 60)
    print("📊 VERIFICACION DE DATOS EXISTENTES")
    print("=" * 60)
    
    tablas = ['empresas', 'usuarios', 'clientes', 'productos', 'facturas', 'roles', 'sucursales']
    for tabla in tablas:
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cur.fetchone()[0]
        print(f"  {tabla}: {count} registros")
    
    # Verificar empresa demo
    cur.execute("SELECT id, razon_social FROM empresas WHERE cedula_juridica = '3101123456'")
    demo = cur.fetchone()
    if demo:
        print(f"\n⚠️  Empresa demo encontrada: {demo[1]} (ID: {demo[0]})")
    
    cur.close()
    conn.close()
    return True

def limpiar_datos():
    """Elimina todos los datos ficticios"""
    conn = conectar()
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🗑️  LIMPIEZA DE DATOS")
    print("=" * 60)
    
    try:
        # Desactivar temporalmente las foreign keys
        cur.execute("SET CONSTRAINTS ALL DEFERRED")
        
        # Orden de eliminacion (respectando foreign keys)
        tablas_orden = [
            'facturas_detalle',
            'facturas',
            'inventario_movimientos',
            'notificaciones',
            'compras',
            'accesos_sucursal',
            'productos',
            'clientes',
            'usuarios',
            'sucursales',
            'empresas',
            'roles'
        ]
        
        for tabla in tablas_orden:
            cur.execute(f"DELETE FROM {tabla}")
            print(f"  ✅ {tabla}: {cur.rowcount} registros eliminados")
        
        conn.commit()
        print("\n✅ Todos los datos ficticios han sido eliminados!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la limpieza: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def crear_roles_defecto():
    """Crea los roles del sistema"""
    import uuid
    conn = conectar()
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("👥 CREACION DE ROLES")
    print("=" * 60)
    
    roles = [
        ('SuperAdmin', 'Administrador supreme del sistema con acceso a todo'),
        ('Administrador', 'Administrador de empresa con acceso total'),
        ('Emisor', 'Puede emitir facturas y gestionar clientes'),
        ('Auditor', 'Solo lectura para revisar metricas y facturas')
    ]
    
    for nombre, descripcion in roles:
        cur.execute("SELECT id FROM roles WHERE nombre = %s", (nombre,))
        existe = cur.fetchone()
        if not existe:
            rol_id = str(uuid.uuid4())
            cur.execute("INSERT INTO roles (id, nombre, descripcion) VALUES (%s, %s, %s)", (rol_id, nombre, descripcion))
            print(f"  ✅ Rol '{nombre}' creado (ID: {rol_id[:8]}...)")
        else:
            print(f"  ⚠️  Rol '{nombre}' ya existe")
    
    conn.commit()
    cur.close()
    conn.close()

def crear_superadmin():
    """Crea el super usuario del sistema"""
    conn = conectar()
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("👤 CREACION DE SUPERADMIN")
    print("=" * 60)
    
    # Verificar si ya existe
    cur.execute("SELECT id FROM usuarios WHERE email = %s", ('superadmin@murotech.com',))
    existe = cur.fetchone()
    
    if existe:
        print(f"  ⚠️  SuperAdmin ya existe (ID: {existe[0]})")
    else:
        # Crear empresa dummy para el superadmin (necesaria para FK)
        cur.execute("""
            INSERT INTO empresas (id, razon_social, nombre_comercial, cedula_juridica, tipo_identificacion)
            VALUES ('00000000-0000-0000-0000-000000000000', 'MUROTECH System', 'MUROTECH', '000000000000', '02')
            ON CONFLICT (cedula_juridica) DO NOTHING
        """)
        
        # Crear superadmin
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash('SuperAdmin2026!')
        
        cur.execute("""
            INSERT INTO usuarios (id, empresa_id, nombre, email, password_hash, is_superadmin, is_active)
            VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000000', 
                    'Super Administrador', 'superadmin@murotech.com', %s, true, true)
        """, (password_hash,))
        
        print("  ✅ SuperAdmin creado!")
        print("     Email: superadmin@murotech.com")
        print("     Password: SuperAdmin2026!")
    
    conn.commit()
    cur.close()
    conn.close()

def verificar_limpieza():
    """Verifica que la limpieza fue exitosa"""
    conn = conectar()
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICACION FINAL")
    print("=" * 60)
    
    tablas = ['empresas', 'usuarios', 'clientes', 'productos', 'facturas', 'roles', 'sucursales']
    for tabla in tablas:
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cur.fetchone()[0]
        estado = "✅ VACIO" if count == 0 else f"⚠️  {count} registros"
        print(f"  {tabla}: {estado}")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    print("🚀 INICIANDO LIMPIEZA DE SUPABASE PARA MUROTECH")
    print("=" * 60)
    
    # 1. Verificar datos actuales
    verificar_datos()
    
    # 2. Limpiar datos
    respuesta = input("\n❓ Desea eliminar todos los datos ficticios? (si/no): ")
    if respuesta.lower() in ['si', 's', 'yes', 'y']:
        limpiar_datos()
    else:
        print("  ⏭️  Limpieza cancelada por el usuario")
    
    # 3. Crear roles
    crear_roles_defecto()
    
    # 4. Crear superadmin
    crear_superadmin()
    
    # 5. Verificar limpieza
    verificar_limpieza()
    
    print("\n" + "=" * 60)
    print("🎉 PROCESO COMPLETADO!")
    print("=" * 60)