# MUROTECH SaaS - Sistema de Facturación Electrónica

Plataforma profesional de facturación electrónica, cotizaciones y gestión de inventario, optimizada para el cumplimiento tributario en Costa Rica (v4.4).

## 🚀 Estructura del Proyecto

El proyecto ha sido modernizado y organizado profesionalmente:

- **`frontend/`**: Aplicación de cliente (HTML/CSS/JS) moderna con diseño "Flat & Dense".
- **`backend/`**: Servidor API Flask (Python) para procesamiento de datos y lógica de negocio.
- **`excel/`**: Catálogos y datos de soporte.

## 🛠️ Tecnologías

- **Frontend**: HTML5, Vanilla JavaScript, CSS3 (Tokens & Custom Properties).
- **Backend**: Python 3.9+, Flask, Gunicorn.
- **Base de Datos**: SQL Server (LocalDB/Express).
- **Librerías Clave**: SweetAlert2, jsPDF, SheetJS.

## 💻 Instalación Local

### 1. Requisitos
- Python 3.9 o superior.
- SQL Server (LocalDB recomendado).
- Driver ODBC 17 para SQL Server.

### 2. Configuración del Backend
```bash
# Entrar a la carpeta del backend
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor de desarrollo
python api/app.py
```

### 3. Ejecución del Frontend
Simplemente abra `frontend/index.html` en su navegador o use un servidor local (Live Server).

---

## 🌐 Despliegue (Production)

### ☁️ Netlify (Frontend)
1. Conecte su repositorio de GitHub a Netlify.
2. La configuración ya está lista en `netlify.toml`.
3. Netlify detectará automáticamente la carpeta `frontend` como el directorio de publicación.

### ☁️ Render (Backend)
1. Cree un nuevo "Web Service" en Render.
2. Conecte su repositorio de GitHub.
3. Configure los siguientes parámetros:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `gunicorn --chdir backend api.app:app`
4. Agregue las variables de entorno necesarias (DB_CONNECTION_STRING, etc.).

### 🐙 GitHub
1. Inicialice el repositorio: `git init`
2. Añada los archivos: `git add .`
3. Realice el commit: `git commit -m "Modernización de MUROTECH y preparación para despliegue"`
4. Suba a su repositorio remoto.

---

## ✨ Características Principales
- ✅ **Facturación Electrónica**: Generación de XML v4.4 y PDF profesional.
- ✅ **Cotizaciones**: Creación de proformas comerciales con descarga en PDF.
- ✅ **Inventario**: Control de existencias con búsqueda inteligente CABYS.
- ✅ **Clientes**: Base de datos de clientes con autocompletado premium.
- ✅ **Seguridad**: Sistema de login y registro integrado.

---

**Desarrollado por**: [Paul Zuñiga/ZenithTech CR]  
**Versión**: 2.0.0 (Modernizada)  
**Licencia**: Propietaria - MUROTECH SOLUTIONS S.A.
