# DOCUMENTACIÓN DE ARQUITECTURA RECOMENDADA - MUROTECH v2.1

**Clasificación:** Especificación Técnica - Backend Reestructuración  
**Versión:** 2.1-RELEASE  
**Estado:** ✅ APLICADA Y EN PROGRESO  
**Última Actualización:** 17 Junio 2026

---

## 0. PROPÓSITO

Este documento define la arquitectura recomendada para el backend de MUROTECH, su estructura de carpetas y el camino de migración necesario para lograr un proyecto mantenible, seguro y escalable.

---

## 1. ESTADO ACTUAL Y APLICACIÓN

### 1.1 Estado actual
- La aplicación Flask está organizada en `backend/app/` usando patrón factory.
- La configuración centralizada está en `backend/app/config.py`.
- Las extensiones (`db`, `limiter`, `cors`) se inicializan en `backend/app/extensions.py`.
- Ya existen blueprints y decoradores en `backend/app/api/`.
- Hay pruebas unitarias en `backend/tests/`.
- **Flask ahora sirve frontend + API en un solo puerto (5001)**.
- **SQLite automático como fallback** cuando no hay Supabase.

### 1.2 Aplicación de la arquitectura recomendada
La arquitectura recomendada se aplica con los siguientes principios:
- `app/__init__.py` es el punto único de creación de la aplicación.
- Las rutas viven en blueprints bajo `app/api/blueprints/`.
- La lógica de negocio se mueve a `app/services/`.
- El flujo de alta sigue: registro de empresa → selección de plan → orden/pago.
- Los modelos quedan en `app/models.py`.
- Los DTOs y validaciones van en `app/utils/validators.py`.
- Las utilidades comunes se centralizan en `app/utils/`.
- Actualmente coexisten dos capas: el monolito legacy `backend/api/app.py`
  y la nueva arquitectura en `backend/app/`. La migración avanza con
  extracción de lógica a servicios.
- **Legacy `api/app.py` eliminado.** Todas las rutas migradas a blueprints modulares.

### 1.3 Progreso de migración

| Componente | Legacy (api/app.py) | Nuevo (app/) | Estado |
|------------|---------------------|--------------|--------|
| Config | `core/config.py` | `app/config.py` | ✅ Migrado |
| Extensions | — | `app/extensions.py` | ✅ Migrado |
| Models | inline | `app/models.py` | ✅ Migrado |
| Auth | inline | `app/api/decorators/auth.py` | ✅ Migrado |
| RBAC | inline | `app/api/decorators/rbac.py` | ✅ Migrado |
| Audit | — | `app/api/decorators/audit.py` | ✅ Nuevo |
| Services | inline | `app/services/` | 🟡 Parcial |
| Validators | `core/validators.py` | `app/utils/validators.py` | ✅ Migrado |
| Crypto | `core/crypto_utils.py` | `app/utils/crypto.py` | ✅ Migrado |
| Blueprints | 52 rutas en 1 archivo | 11 blueprints modulares | ✅ Migrado |
| Empresa | inline | `app/services/empresa_service.py` | ✅ Migrado |
| Auth | inline | `app/services/auth_service.py` | ✅ Migrado |
| Billing | inline | `app/services/billing_plans.py` | ✅ Migrado |
| Auditoria | — | `app/services/auditoria_service.py` | ✅ Nuevo |
| Contingencia | — | `app/services/contingencia_service.py` | ✅ Nuevo |
| Horario MH | — | `fiscal/horario.py` | ✅ Nuevo |
| Schemas/DTOs | inline | `app/schemas/__init__.py` | ✅ Migrado |
| Payments | inline | `app/api/blueprints/payments.py` | ✅ Migrado |

---

## 2. ESTRUCTURA DE CARPETAS ACTUAL

```
backend/
├── run.py                    # Punto de entrada (factory)
├── .env / .env.example       # Configuración por entorno
├── requirements.txt          # Dependencias
├── app/                      # Aplicación Flask modular
│   ├── __init__.py           # Factory + serve frontend
│   ├── config.py             # Config Dev/Test/Prod
│   ├── extensions.py         # db, migrate, limiter, cors
│   ├── middleware.py         # Seguridad headers + CSRF
│   ├── error_handlers.py     # 404, 405, 500
│   ├── models.py             # Modelos SQLAlchemy
│   ├── api/
│   │   ├── blueprints/       # 11 blueprints modulares
│   │   └── decorators/       # auth, rbac, audit
│   ├── services/             # Lógica de negocio
│   │   └── email_service.py  # Envío SMTP
│   ├── schemas/              # Schemas/DTOs marshmallow
│   └── utils/                # crypto, validators, money, date
├── docker/                   # Dockerfile + docker-compose + nginx.conf
├── fiscal/                   # Integración Hacienda CR
│   ├── xml_builder.py        # Construcción XML v4.4
│   ├── clave.py              # Clave + consecutivo
│   ├── signer.py             # Firma XAdES-BES
│   ├── hacienda_client.py    # Cliente API MH
│   ├── horario.py            # Horario + reintentos
│   ├── xsd_validator.py      # Validación XSD
│   └── schemas/              # Esquemas XSD
├── core/                     # Legacy (en desuso)
├── tests/                    # Unit tests
└── scripts/
    ├── ...                   # Migraciones y utilidades
    └── backup_db.py          # Backup de base de datos

frontend/
├── index.html                # Entry point PWA
├── manifest.json             # PWA manifest
├── service-worker.js         # Service Worker
├── offline.html              # Fallback offline
├── html/                     # 16 páginas HTML (+ mensajeReceptor.html)
├── css/                      # Estilos
├── js/                       # Lógica (config.js + mensajeReceptor.js centralizados)
└── imagenes/                 # Assets

.github/
└── workflows/                # CI/CD GitHub Actions

docs/
└── openapi.yaml              # Documentación API OpenAPI
```

---

## 3. LO QUE FALTA PARA COMPLETAR LA MIGRACIÓN

| # | Item | Estado | Estimación |
|---|------|--------|------------|
| 1 | Eliminar `api/app.py` (legacy 3800+ líneas) | ✅ Completado | 0 días |
| 2 | Mover todos los services restantes | 🟡 Parcial | 2-3 días |
| 3 | Schemas/DTOs con marshmallow | ✅ Completado | 0 días |
| 4 | Dockerfile + docker-compose | ✅ Completado | 0 días |
| 5 | CI/CD GitHub Actions completo | ✅ Completado | 0 días |
| 6 | Eliminar `api/app.py` (legacy) | ✅ Completado | 0 días |

---

> **📦 Nota:** `signxml` actualizado a v4.4+ (API `SignatureConstructionMethod.enveloped`) y `lxml>=5.3.0`.

*Documento actualizado: 17 Junio 2026.*
