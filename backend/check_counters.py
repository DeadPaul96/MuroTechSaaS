#!/usr/bin/env python3
"""
Script to check and fix NULL counter values in Sucursal table
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from api.app import app, db
from api.models import Sucursal

with app.app_context():
    print("\n" + "="*80)
    print("CHECKING SUCURSAL COUNTERS")
    print("="*80 + "\n")
    
    sucursales = Sucursal.query.all()
    
    if not sucursales:
        print("No sucursales found in database.")
        sys.exit(0)
    
    print(f"Found {len(sucursales)} sucursal(es)\n")
    
    changes_made = False
    
    for sucursal in sucursales:
        print(f"Sucursal: {sucursal.nombre} (ID: {sucursal.id})")
        print(f"  c_factura:      {sucursal.c_factura} (type: {type(sucursal.c_factura).__name__})")
        print(f"  c_tiquete:      {sucursal.c_tiquete} (type: {type(sucursal.c_tiquete).__name__})")
        print(f"  c_nota_credito: {sucursal.c_nota_credito} (type: {type(sucursal.c_nota_credito).__name__})")
        print(f"  c_nota_debito:  {sucursal.c_nota_debito} (type: {type(sucursal.c_nota_debito).__name__})")
        print()
        
        # Check for NULL values
        has_null = False
        if sucursal.c_factura is None:
            print("  ⚠️  c_factura is NULL - will fix to 0")
            sucursal.c_factura = 0
            has_null = True
            changes_made = True
        if sucursal.c_tiquete is None:
            print("  ⚠️  c_tiquete is NULL - will fix to 0")
            sucursal.c_tiquete = 0
            has_null = True
            changes_made = True
        if sucursal.c_nota_credito is None:
            print("  ⚠️  c_nota_credito is NULL - will fix to 0")
            sucursal.c_nota_credito = 0
            has_null = True
            changes_made = True
        if sucursal.c_nota_debito is None:
            print("  ⚠️  c_nota_debito is NULL - will fix to 0")
            sucursal.c_nota_debito = 0
            has_null = True
            changes_made = True
        
        if has_null:
            print("  Saving changes...")
            db.session.add(sucursal)
        else:
            print("  ✓ All counters are valid (not NULL)")
        print()
    
    if changes_made:
        print("Committing changes to database...")
        db.session.commit()
        print("✓ Database updated successfully!")
    else:
        print("No changes needed - all counters are valid.")
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80 + "\n")
