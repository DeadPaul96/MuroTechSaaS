#!/usr/bin/env python3
"""
Script para verificar y corregir el usuario SuperAdmin
"""
from db_conn import get_psycopg2_connection


def main():
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    
    print("=" * 60)
    print("🔍 VERIFICANDO SUPERADMIN")
    print("=" * 60)
    
    # Verificar empresa
    cur.execute("""
        SELECT id, razon_social, is_active, plan_estado 
        FROM empresas 
        WHERE id = '00000000-0000-0000-0000-000000000000'
    """)
    empresa = cur.fetchone()
    
    if empresa:
        print(f"\n📊 Empresa SuperAdmin:")
        print(f"  ID: {empresa[0]}")
        print(f"  Razón Social: {empresa[1]}")
        print(f"  Activa: {empresa[2]}")
        print(f"  Plan Estado: {empresa[3]}")
        
        # Corregir si es necesario
        if not empresa[2] or empresa[3] != 'activo':
            print("\n⚠️  Corrigiendo empresa...")
            cur.execute("""
                UPDATE empresas 
                SET is_active = true, plan_estado = 'activo'
                WHERE id = '00000000-0000-0000-0000-000000000000'
            """)
            conn.commit()
            print("  ✅ Empresa corregida!")
    else:
        print("\n❌ Empresa no encontrada")
    
    # Verificar usuario
    cur.execute("""
        SELECT id, nombre, email, is_active, is_superadmin, empresa_id
        FROM usuarios 
        WHERE email = 'superadmin@murotech.com'
    """)
    usuario = cur.fetchone()
    
    if usuario:
        print(f"\n👤 Usuario SuperAdmin:")
        print(f"  ID: {usuario[0]}")
        print(f"  Nombre: {usuario[1]}")
        print(f"  Email: {usuario[2]}")
        print(f"  Activo: {usuario[3]}")
        print(f"  Es SuperAdmin: {usuario[4]}")
        print(f"  Empresa ID: {usuario[5]}")
        
        # Corregir si es necesario
        if not usuario[3] or not usuario[4]:
            print("\n⚠️  Corrigiendo usuario...")
            cur.execute("""
                UPDATE usuarios 
                SET is_active = true, is_superadmin = true
                WHERE email = 'superadmin@murotech.com'
            """)
            conn.commit()
            print("  ✅ Usuario corregido!")
    else:
        print("\n❌ Usuario no encontrado")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("=" * 60)
    print("\nCredenciales de login:")
    print("  Email: superadmin@murotech.com")
    print("  Password: SuperAdmin2026!")

if __name__ == '__main__':
    main()
