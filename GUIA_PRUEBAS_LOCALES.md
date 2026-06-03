# 🧪 GUÍA DE PRUEBAS LOCALES — MUROTECH SaaS

**Para:** Cliente / Usuario final  
**Objetivo:** Descargar, iniciar y probar todas las funcionalidades de la plataforma en servidor local  
**Tiempo estimado:** 15-20 minutos  
**Última actualización:** 2 Junio 2026

---

## 📋 REQUISITOS PREVIOS

| Requisito | Versión | Cómo verificar | Descarga |
|-----------|---------|-----------------|----------|
| Python | 3.10 o superior | Abrir terminal → `python --version` | [python.org](https://www.python.org/downloads/) |
| Git | Cualquiera | `git --version` | [git-scm.com](https://git-scm.com/) |
| Navegador | Chrome/Edge/Firefox | — | Cualquiera moderno |

> **⚠️ Importante:** Al instalar Python en Windows, marca la casilla **"Add Python to PATH"**.

---

## 🚀 PASO 1 — Descargar el proyecto

### Opción A: Con Git (recomendado)

```bash
git clone https://github.com/DeadPaul96/MuroTechSaaS
cd MUROTECH-SaaS
```

### Opción B: Descarga ZIP

1. Ir al repositorio en GitHub
2. Clic en el botón verde **"Code"**
3. Seleccionar **"Download ZIP"**
4. Descomprimir la carpeta
5. Entrar a la carpeta descomprimida

---

## 🔧 PASO 2 — Iniciar el servidor

### Windows

1. **Doble clic** en el archivo `start.bat`
2. Esperar a que termine de instalar (primera vez tarda 2-3 minutos)
3. Cuando pregunte **"¿Deseas cargar datos de prueba?"**, presionar **Enter** (Sí)
4. Esperar a ver el mensaje:

```
  ────────────────────────────────────────────
   🚀 Servidor listo en: http://localhost:5001
   📧 Demo:  admin@qa.com / admin123
  ────────────────────────────────────────────
```

### Mac / Linux

```bash
chmod +x start.sh
./start.sh
```

> **Si falla:** Verificar que Python esté instalado y en el PATH. Intentar con `python3` en lugar de `python`.

---

## 🌐 PASO 3 — Abrir la plataforma

1. Abrir el navegador (Chrome recomendado)
2. Ir a: **http://localhost:5001**
3. Deberás ver la pantalla de inicio de sesión

### Credenciales de prueba

| Campo | Valor |
|-------|-------|
| Email | `admin@qa.com` |
| Password | `admin123` |

---

## 🧪 PASO 4 — Probar las funcionalidades

### 4.1 ✅ Panel de Control (Dashboard)

Después de iniciar sesión, verás el panel principal.

**Qué verificar:**
- [ ] Se muestra el dashboard con estadísticas
- [ ] Las notificaciones aparecen en la campana 🔔
- [ ] El menú lateral funciona y navega entre secciones

---

### 4.2 ✅ Clientes

Ir a **Clientes** en el menú lateral.

**Qué verificar:**
- [ ] Se muestra la lista de 5 clientes de prueba
- [ ] Se puede buscar un cliente por nombre
- [ ] Botón **"Nuevo Cliente"** abre el formulario
- [ ] Al crear un cliente, aparece en la lista
- [ ] Se puede editar un cliente existente
- [ ] Se puede eliminar un cliente

**Datos para crear un cliente:**
| Campo | Valor |
|-------|-------|
| Nombre | Cliente de Prueba |
| Identificación | 123456789 |
| Email | prueba@correo.com |
| Teléfono | 8888-9999 |
| Tipo ID | Física (01) |

---

### 4.3 ✅ Inventario / Productos

Ir a **Inventario** en el menú lateral.

**Qué verificar:**
- [ ] Se muestra la lista de 10 productos de prueba
- [ ] Se puede buscar productos por nombre o código
- [ ] Botón **"Nuevo Producto"** abre el formulario
- [ ] Al crear un producto, aparece en la lista
- [ ] Se puede editar un producto existente
- [ ] Los precios y stock se muestran correctamente
- [ ] La búsqueda CABYS funciona al escribir

**Datos para crear un producto:**
| Campo | Valor |
|-------|-------|
| Código | PRU-001 |
| Descripción | Producto de Prueba |
| Marca | Genérico |
| Precio Venta | 10000 |
| Impuesto | 13% |
| Stock | 50 |

---

### 4.4 ✅ Facturación (Pantalla Principal)

Ir a **Facturación** en el menú lateral. **Esta es la función más importante.**

**Qué verificar:**
- [ ] Se carga la pantalla de facturación correctamente
- [ ] El sidebar no sobrepone el panel de facturación
- [ ] Se puede seleccionar un cliente del dropdown
- [ ] Se puede buscar y agregar productos a la factura
- [ ] Los cálculos de subtotal, IVA y total son correctos
- [ ] Se puede cambiar el tipo de documento (Factura, Tiquete, NC, ND)

**Probar emisión de factura:**
1. Seleccionar cliente: **Juan Pérez**
2. Agregar producto: **Laptop Dell XPS 13** → cantidad 1
3. Agregar producto: **Mouse Inalámbrico Logitech** → cantidad 2
4. Verificar que el total calcula correctamente
5. Clic en **"Emitir"** o **"Guardar"**

> **Nota:** En modo local, el envío a Hacienda está desactivado (`HACIENDA_SEND_ENABLED=false`). La factura se guarda localmente pero **no se envía al Ministerio de Hacienda**.

---

### 4.5 ✅ Notas de Crédito y Débito

En la pantalla de Facturación:

**Qué verificar:**
- [ ] Al seleccionar tipo **"Nota de Crédito"** o **"Nota de Débito"**, aparece el panel de referencia
- [ ] El panel de referencia pide: Clave del documento, Código de razón, Razón
- [ ] Al cambiar a Factura o Tiquete, el panel de referencia desaparece

**Probar NC:**
1. Cambiar tipo documento a **"Nota de Crédito Electrónica"**
2. Verificar que aparece el panel de referencia
3. Ingresar una clave de referencia (puede ser inventada para prueba)
4. Seleccionar un código de razón (ej. "Anulación")
5. Agregar un producto y emitir

---

### 4.6 ✅ Modo Contingencia

En la pantalla de Facturación:

**Qué verificar:**
- [ ] En el dropdown de tipo de documento, aparecen las opciones **"Contingencia Factura (09)"** y **"Contingencia Tiquete (10)"**
- [ ] Al seleccionar contingencia, el sistema marca la clave con `situacion=2`

---

### 4.7 ✅ Cotizaciones

Ir a **Cotizaciones** en el menú lateral.

**Qué verificar:**
- [ ] Se puede crear una nueva cotización
- [ ] Se pueden agregar productos a la cotización
- [ ] Se puede cambiar el estado (Borrador → Enviada → Aceptada)
- [ ] El tipo de cambio USD se muestra si está disponible

---

### 4.8 ✅ Planes y Precios

Ir a **Planes** en el menú lateral.

**Qué verificar:**
- [ ] Se muestran los 4 planes disponibles
- [ ] Al hacer clic en un plan, aparece el modal de pago
- [ ] El modal de pago tiene campos para datos de tarjeta
- [ ] El número de tarjeta se formatea automáticamente (grupos de 4)
- [ ] La fecha de expiración se formatea automáticamente (MM/AA)
- [ ] No hay sidebar en esta página (diseño centrado)

---

### 4.9 ✅ Reportes

Ir a **Reportes** en el menú lateral.

**Qué verificar:**
- [ ] Se muestran estadísticas de ventas
- [ ] Se pueden filtrar por fecha
- [ ] Los gráficos se renderizan correctamente

---

### 4.10 ✅ Configuración

Ir a **Configuración** en el menú lateral.

**Qué verificar:**
- [ ] Se muestra la información de la empresa
- [ ] Se pueden editar los datos de la empresa
- [ ] Se muestra la lista de usuarios
- [ ] Se pueden crear nuevos usuarios con roles
- [ ] La configuración de facturación es editable

---

### 4.11 ✅ Auditoría

Ir a **Auditoría** en el menú lateral.

**Qué verificar:**
- [ ] Se muestra el registro de acciones auditadas
- [ ] Se pueden filtrar por fecha y tipo de acción
- [ ] Las acciones críticas (logout, cambios de plan, pagos) aparecen registradas

---

### 4.12 ✅ PWA (Progressive Web App)

**Qué verificar:**
- [ ] En Chrome, aparece el icono de instalación en la barra de direcciones
- [ ] Al instalar, la app se abre como ventana independiente (sin barra de URL)
- [ ] Al desconectar internet y recargar, aparece la página offline con botón de reintento

**Cómo probar offline:**
1. Abrir DevTools (F12)
2. Ir a la pestaña **Network**
3. Marcar **"Offline"** en el dropdown
4. Recargar la página (F5)
5. Deberías ver la página offline de MUROTECH
6. Desmarcar "Offline" y hacer clic en **"Reintentar"**

---

### 4.13 ✅ SuperAdmin

Ir a **SuperAdmin** en el menú lateral (si aparece).

**Qué verificar:**
- [ ] Se muestra el panel de administración global
- [ ] Se pueden ver todas las empresas registradas
- [ ] Se puede suspender/reactivar el plan de una empresa

---

## 🔐 PASO 5 — Probar seguridad y límites

### Rate Limiting

1. Intentar registrar más de 10 empresas en una hora → debería bloquear
2. Intentar login fallido más de 20 veces en una hora → debería bloquear

### Protección CSRF

1. En desarrollo local, las mutaciones (POST/PUT/DELETE) funcionan desde el navegador
2. En producción, peticiones desde orígenes no autorizados son bloqueadas

---

## 📊 RESUMEN DE VERIFICACIÓN

Al completar todas las pruebas, esta es tu checklist:

| # | Funcionalidad | Estado |
|---|---------------|--------|
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

## ❓ PROBLEMAS COMUNES

### El servidor no inicia

```
Solución:
1. Verificar Python instalado: python --version (debe ser 3.10+)
2. Eliminar la carpeta backend/venv/ y volver a ejecutar start.bat
3. Verificar que el archivo backend/.env existe
```

### Error de "No module named 'xxx'"

```
Solución:
1. Activar el venv: backend\venv\Scripts\activate
2. Instalar manualmente: pip install -r backend/requirements.txt
3. Volver a ejecutar: python backend/run.py
```

### No aparecen los datos de prueba

```
Solución:
Abrir en el navegador: http://localhost:5001/api/seed
Esto carga los datos de prueba (empresa, clientes, productos).
```

### La página se ve desordenada

```
Solución:
1. Limpiar caché del navegador: Ctrl+Shift+Delete
2. O abrir en ventana de incógnito
3. Asegurarse de acceder desde http://localhost:5001 (no file://)
```

### Error de CORS

```
Solución:
Acceder siempre desde http://localhost:5001
No abrir los archivos HTML directamente desde el explorador de archivos.
```

---

## 🛑 Cómo detener el servidor

En la terminal donde corre el servidor:

- **Windows:** Presionar `Ctrl + C`
- **Mac/Linux:** Presionar `Ctrl + C`

---

## 📝 Notas importantes

1. **Los datos son locales:** Todo se guarda en SQLite. Al eliminar la base de datos, se pierde todo.
2. **No se envía a Hacienda:** En modo local, `HACIENDA_SEND_ENABLED=false`. Las facturas se guardan pero no se envían al MH.
3. **Los pagos son simulados:** No hay cargo real de tarjeta. Es un mock para pruebas.
4. **Para conectar a Supabase real:** Editar `backend/.env` y agregar `DATABASE_URL=postgresql://...`

---

*Documento generado para pruebas locales — MUROTECH SaaS v1.3.0*
