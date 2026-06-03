# Migraciones de base de datos

No se requiere una base de datos nueva. Use el orquestador:

```bash
cd backend
python scripts/run_all_migrations.py
python scripts/run_all_migrations.py --encrypt-secrets
```

## Scripts incluidos

| Script | Propósito |
|--------|-----------|
| `migrate_db_v44.py` | Ubicación en sucursales, `superadmin_empresas` |
| `add_tipo_impuesto_column.py` | `tipo_impuesto` en detalle de factura |
| `migrate_ambiente_mensaje.py` | `ambiente_hacienda`, tabla `mensajes_receptor` |
| `migrate_productos_tipo_impuesto.py` | `tipo_impuesto` en productos |
| `migrate_indexes.py` | Índices de rendimiento |
| `encrypt_empresa_secrets.py` | Cifra PIN/password MH existentes |
| `verify_schema.py` | Checklist tablas/columnas vs `models.py` |

## Flask-Migrate (opcional)

```bash
set FLASK_APP=api.app:app
flask db init
flask db migrate -m "baseline"
flask db upgrade
```

Requiere `DATABASE_URL` en `.env`.
