# MUROTECH SaaS — Facturación Electrónica Costa Rica

Sistema de facturación electrónica multi-empresa compatible con la API v4.4 del Ministerio de Hacienda de Costa Rica.

---

## Requisitos previos

| Requisito | Versión mínima | Descarga |
|-----------|----------------|----------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Git | Cualquiera | [git-scm.com](https://git-scm.com/) |
| Navegador | Chrome / Edge / Firefox | — |

> **Windows:** Al instalar Python, marca la casilla **"Add Python to PATH"** o el sistema no lo reconocerá.

No necesitas Node.js, PostgreSQL ni Redis. El sistema funciona con **SQLite local** y todas las dependencias se instalan automáticamente.

---

## Paso 1 — Descargar el proyecto

### Con Git (recomendado)

```bash
git clone https://github.com/DeadPaul96/MuroTechSaaS.git
cd MuroTechSaaS
```

### Descarga ZIP

1. Ir al repositorio en GitHub
2. Clic en el botón verde **"Code"** → **"Download ZIP"**
3. Descomprimir la carpeta
4. Entrar a la carpeta descomprimida

---

## Paso 2 — Iniciar el servidor

### Windows (doble clic o desde CMD)

```bash
start.bat
```

El script hace todo automáticamente:
- Crea el entorno virtual `venv/`
- Instala todas las dependencias de `requirements.txt`
- Genera el archivo `.env` con claves seguras únicas
- Inicializa la base de datos SQLite
- Ofrece cargar datos de prueba (presiona Enter para aceptar)
- Inicia el servidor en http://localhost:5001

Cuando veas esto, el servidor está listo:

```
  ----------------------------------------
   Servidor listo en: http://localhost:5001
   Demo: admin@qa.com / admin123
  ----------------------------------------
```

### Mac / Linux

```bash
chmod +x start.sh
./start.sh
```

### Paso a paso (manual, cualquier OS)

```bash
# Entrar al backend
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear .env
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux

# Iniciar
python run.py
```

---

## Paso 3 — Abrir la plataforma

1. Abrir el navegador
2. Ir a **http://localhost:5001**
3. Verás la pantalla de inicio de sesión

| Campo | Valor |
|-------|-------|
| Email | `admin@qa.com` |
| Password | `admin123` |

> Si no aparecen datos, abre **http://localhost:5001/api/seed** para cargarlos manualmente.

---

## Paso 4 — Qué probar

### 4.1 Dashboard

Después de iniciar sesión:
- Se muestra el panel con estadísticas generales
- Las notificaciones funcionan (campana)
- El menú lateral navega entre secciones

### 4.2 Clientes

Ir a **Clientes** en el menú lateral:
- Lista de clientes de prueba cargados
- Buscar por nombre funciona
- Crear, editar y eliminar clientes

Datos de prueba para crear un cliente:

| Campo | Valor |
|-------|-------|
| Nombre | Cliente de Prueba |
| Identificación | 123456789 |
| Email | prueba@correo.com |
| Teléfono | 8888-9999 |
| Tipo ID | Física (01) |

### 4.3 Inventario / Productos

Ir a **Inventario** en el menú lateral:
- Lista de productos de prueba
- Búsqueda por nombre o código
- Crear, editar y eliminar productos
- Búsqueda de código CABYS funciona al escribir

Datos de prueba para crear un producto:

| Campo | Valor |
|-------|-------|
| Código | PRU-001 |
| Descripción | Producto de Prueba |
| Precio Venta | 10000 |
| Impuesto | 13% |
| Stock | 50 |

### 4.4 Facturación

Ir a **Facturación** en el menú lateral. Esta es la función principal:

1. Seleccionar cliente: **Juan Pérez**
2. Agregar producto: **Laptop Dell XPS 13** → cantidad 1
3. Agregar otro producto: **Mouse Inalámbrico** → cantidad 2
4. Verificar que subtotal, IVA y total calculan correctamente
5. Clic en **Emitir**

Tipos de documento disponibles: Factura Electrónica (01), Tiquete (04), Nota de Crédito (02), Nota de Débito (03), Contingencia (09/10).

> En modo local, `HACIENDA_SEND_ENABLED=false`. Las facturas se guardan localmente pero **no se envían al Ministerio de Hacienda**.

### 4.5 Notas de Crédito y Débito

En la pantalla de Facturación:
1. Cambiar el tipo de documento a **Nota de Crédito Electrónica**
2. Aparece el panel de referencia (clave del documento, código de razón, descripción)
3. Ingresar una clave de referencia (puede ser inventada para prueba)
4. Seleccionar razón (ej. "Anulación")
5. Agregar un producto y emitir

### 4.6 Modo Contingencia

En el dropdown de tipo de documento, seleccionar **Contingencia Factura (09)** o **Contingencia Tiquete (10)**. El sistema marca automáticamente la clave con `situacion=2`.

### 4.7 Cotizaciones

Ir a **Cotizaciones**:
- Crear una cotización nueva con productos
- Cambiar el estado: Borrador → Enviada → Aceptada

### 4.8 Planes y Precios

Ir a **Planes**:
- Se muestran los 4 planes disponibles
- Clic en un plan abre el modal de pago
- El número de tarjeta se formatea automáticamente (grupos de 4)
- La fecha de expiración se formatea (MM/AA)

> Los pagos son simulados. No hay cargo real de tarjeta.

### 4.9 Reportes

Ir a **Reportes**:
- Estadísticas de ventas con filtros por fecha
- Gráficos se renderizan correctamente

### 4.10 Configuración

Ir a **Configuración**:
- Editar información de empresa
- Gestionar usuarios y roles
- Configuración de facturación electrónica

### 4.11 Auditoría

Ir a **Auditoría**:
- Registro de todas las acciones críticas (login, facturas, cambios de plan)
- Filtros por fecha y tipo de acción

### 4.12 PWA (Progressive Web App)

- En Chrome, aparece el icono de instalación en la barra de direcciones
- Al instalar, la app se abre como ventana independiente
- Probar modo offline: F12 → Network → marcar "Offline" → recargar. Debe aparecer la página offline de MUROTECH

### 4.13 SuperAdmin

Ir a **SuperAdmin** (si está visible en el menú):
- Panel de administración global de empresas
- Suspender / reactivar planes

---

## Checklist de verificación

| # | Funcionalidad | OK |
|---|---------------|----|
| 1 | Servidor inicia correctamente | ☐ |
| 2 | Login con credenciales demo | ☐ |
| 3 | Dashboard con estadísticas | ☐ |
| 4 | CRUD de clientes | ☐ |
| 5 | CRUD de productos/inventario | ☐ |
| 6 | Emisión de factura | ☐ |
| 7 | Notas de crédito/débito con referencia | ☐ |
| 8 | Tipos contingencia (09/10) | ☐ |
| 9 | Cotizaciones | ☐ |
| 10 | Modal de pago en planes | ☐ |
| 11 | Reportes y filtros | ☐ |
| 12 | Configuración de empresa | ☐ |
| 13 | Auditoría visible | ☐ |
| 14 | PWA instalable | ☐ |
| 15 | Modo offline funciona | ☐ |

---

## Problemas comunes

**El servidor no inicia**
1. Verificar Python instalado: `python --version` (debe ser 3.10+)
2. Eliminar `backend/venv/` y volver a ejecutar `start.bat`
3. Verificar que `backend/.env` existe

**Error: No module named 'xxx'**
```bash
# Activar el venv manualmente e instalar
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/run.py
```

**No aparecen datos de prueba**
Abrir en el navegador: http://localhost:5001/api/seed

**La página se ve desordenada**
- Limpiar caché: `Ctrl+Shift+Delete`
- Abrir en ventana de incógnito
- Asegurarse de acceder desde `http://localhost:5001` y no desde `file://`

**Error de CORS**
Acceder siempre desde `http://localhost:5001`. No abrir los HTML directamente desde el explorador de archivos.

---

## Cómo detener el servidor

En la terminal donde está corriendo: `Ctrl + C`

---

## Configuración avanzada

### Conectar a Supabase (PostgreSQL en la nube)

1. Crear un proyecto en [supabase.com](https://supabase.com)
2. Copiar la URL de conexión desde **Settings → Database**
3. Editar `backend/.env`:

```env
DATABASE_URL=postgresql://postgres.TU_PROYECTO:TU_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

4. Reiniciar el servidor

### Cambiar el puerto

Editar `PORT=5001` en `backend/.env`.

### Ejecutar tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## Estructura del proyecto

```
MuroTechSaaS/
├── start.bat              # Script de inicio Windows
├── start.sh               # Script de inicio Mac/Linux
├── README.md              # Este archivo
│
├── backend/               # API Flask (Python)
│   ├── run.py             # Punto de entrada
│   ├── requirements.txt   # Dependencias Python
│   ├── .env.example       # Plantilla de configuración
│   ├── app/               # Aplicación Flask modular
│   │   ├── __init__.py    # Factory (crea la app + sirve frontend)
│   │   ├── config.py      # Configuración por entorno
│   │   └── api/           # Endpoints API (blueprints)
│   ├── fiscal/            # Integración Hacienda CR
│   ├── core/              # Utilidades compartidas
│   └── tests/             # Tests
│
└── frontend/              # Interfaz web (HTML/CSS/JS)
    ├── index.html         # Punto de entrada
    ├── manifest.json      # PWA manifest
    ├── service-worker.js  # Service Worker PWA
    ├── html/              # Páginas HTML
    ├── css/               # Estilos
    └── js/                # Lógica JavaScript
```

---

## Notas importantes

- Los datos son locales. Todo se guarda en SQLite. Al eliminar la base de datos se pierde todo.
- No se envía a Hacienda en modo local (`HACIENDA_SEND_ENABLED=false`).
- Los pagos son simulados. No hay cargo real de tarjeta.
- Para producción real se necesita certificado P12 y credenciales de Hacienda.

---

MUROTECH © 2026 — Sistema de Facturación Electrónica para Costa Rica
