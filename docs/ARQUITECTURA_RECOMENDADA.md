# DOCUMENTACIÓN DE ARQUITECTURA RECOMENDADA - MUROTECH v2.1

**Clasificación:** Especificación Técnica - Backend Reestructuración  
**Versión:** 2.1-RELEASE  
**Estado:** ✅ APLICADA Y EN PROGRESO  
**Última Actualización:** 2 Junio 2026

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
│   └── utils/                # crypto, validators, money, date
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
└── scripts/                  # Migraciones y utilidades

frontend/
├── index.html                # Entry point PWA
├── manifest.json             # PWA manifest
├── service-worker.js         # Service Worker
├── offline.html              # Fallback offline
├── html/                     # 16 páginas HTML
├── css/                      # Estilos
├── js/                       # Lógica (config.js centralizado)
└── imagenes/                 # Assets
```

---

## 3. LO QUE FALTA PARA COMPLETAR LA MIGRACIÓN

| # | Item | Estado | Estimación |
|---|------|--------|------------|
| 1 | Eliminar `api/app.py` (legacy 3800+ líneas) | 🟡 Esperando QA | 0.5 días |
| 2 | Mover todos los services restantes | 🟡 Parcial | 2-3 días |
| 3 | Schemas/DTOs con marshmallow | ❌ Pendiente | 3-5 días |
| 4 | Dockerfile + docker-compose | ❌ Pendiente | 1 día |
| 5 | CI/CD GitHub Actions completo | ❌ Pendiente | 1 día |

---

*Documento actualizado: 2 Junio 2026.*
