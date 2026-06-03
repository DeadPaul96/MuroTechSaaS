# 🧾 MUROTECH SaaS — Facturación Electrónica Costa Rica

Sistema de facturación electrónica multi-empresa compatible con la API v4.4 del Ministerio de Hacienda de Costa Rica.

---

## 🚀 Inicio Rápido

### Requisitos

| Requisito | Versión | Descarga |
|-----------|---------|----------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Git | Cualquiera | [git-scm.com](https://git-scm.com/) |

> **Nota:** No necesitas Node.js, PostgreSQL ni Redis. El sistema funciona con **SQLite** local y todas las dependencias se instalan automáticamente.

### Opción A: Un solo comando (recomendado)

**Windows:**
```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/MUROTECH-SaaS.git
cd MUROTECH-SaaS

# 2. Ejecutar el script de inicio
start.bat
```

**Mac / Linux:**
```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/MUROTECH-SaaS.git
cd MUROTECH-SaaS

# 2. Dar permisos y ejecutar
chmod +x start.sh
./start.sh
```

El script se encarga de:
- ✅ Crear el entorno virtual (`venv/`)
- ✅ Instalar todas las dependencias
- ✅ Crear el archivo `.env` con configuración por defecto
- ✅ Inicializar la base de datos SQLite
- ✅ Cargar datos de prueba (opcional)
- ✅ Iniciar el servidor en **http://localhost:5001**

### Opción B: Paso a paso

```bash
# 1. Clonar
git clone https://github.com/TU_USUARIO/MUROTECH-SaaS.git
cd MUROTECH-SaaS

# 2. Crear entorno virtual
cd backend
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux

# 6. Iniciar servidor
python run.py
```

---

## 🔐 Credenciales de Prueba

Después de cargar los datos de prueba:

| Campo | Valor |
|-------|-------|
| URL | http://localhost:5001 |
| Email | `admin@qa.com` |
| Password | `admin123` |

> **⚠️ Primera vez:** Al abrir el navegador, ve a **http://localhost:5001/api/seed** para crear los datos de prueba automáticamente.

---

## 📁 Estructura del Proyecto

```
MUROTECH-SaaS/
├── start.bat              # Script de inicio Windows
├── start.sh               # Script de inicio Mac/Linux
├── README.md              # Este archivo
│
├── backend/               # API Flask (Python)
│   ├── run.py             # Punto de entrada
│   ├── requirements.txt   # Dependencias Python
│   ├── .env.example       # Plantilla de configuración
│   ├── .env               # Tu configuración (no se sube a Git)
│   ├── app/               # Aplicación Flask modular
│   │   ├── __init__.py    # Factory (crea la app + sirve frontend)
│   │   ├── config.py      # Configuración por entorno
│   │   ├── models.py      # Modelos SQLAlchemy
│   │   └── api/blueprints/ # Endpoints API
│   ├── fiscal/            # Integración Hacienda CR
│   ├── core/              # Utilidades compartidas
│   └── tests/             # Tests unitarios
│
└── frontend/              # Interfaz web (HTML/CSS/JS)
    ├── index.html          # Punto de entrada
    ├── manifest.json       # PWA manifest
    ├── service-worker.js   # Service Worker PWA
    ├── html/               # Páginas HTML
    ├── css/                # Estilos
    ├── js/                 # Lógica JavaScript
    └── imagenes/           # Imágenes y logos
```

---

## 🔧 Configuración Avanzada

### Conectar a Supabase (PostgreSQL en la nube)

1. Crea un proyecto en [supabase.com](https://supabase.com)
2. Copia la URL de conexión desde **Settings → Database**
3. Edita `backend/.env`:

```env
DATABASE_URL=postgresql://postgres.TU_PROYECTO:TU_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

4. Reinicia el servidor

> Sin `DATABASE_URL`, el sistema usa SQLite automáticamente.

### Generar claves seguras (para producción)

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 🧪 Funcionalidades

- ✅ Facturación electrónica (Hacienda v4.4)
- ✅ Factura Electrónica (01), Tiquete (04), NC (02), ND (03)
- ✅ Modo Contingencia (09, 10)
- ✅ Multi-empresa y multi-sucursal
- ✅ Gestión de clientes, productos e inventario
- ✅ Cotizaciones
- ✅ Panel de administración
- ✅ Auditoría y logs
- ✅ Reportes
- ✅ PWA instalable
- ✅ Validación XSD de comprobantes
- ✅ Firma digital XAdES-BES
- ✅ Rate limiting
- ✅ Programación de envíos a Hacienda (horario hábil)

---

## ❓ Preguntas Frecuentes

### ¿Puedo usarlo sin internet?
Sí. En modo local con SQLite, toda la funcionalidad de facturación funciona sin internet. Solo el envío real a Hacienda requiere conexión.

### ¿Cómo cambio el puerto?
Edita `PORT=5001` en `backend/.env` al puerto que desees.

### ¿Cómo ejecuto los tests?
```bash
cd backend
python -m pytest tests/ -v
```

### El servidor no inicia
1. Verifica que Python 3.10+ esté instalado: `python --version`
2. Elimina `backend/venv/` y vuelve a ejecutar `start.bat`
3. Verifica que el archivo `backend/.env` exista

### Error de CORS
Asegúrate de acceder desde **http://localhost:5001** (no desde `file://`).

---

## 📜 Licencia

Proyecto privado — MUROTECH © 2026
