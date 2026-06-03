# Configuración para ejecutar MUROTECH SaaS

**Actualizado:** 2 Junio 2026

## 🚀 Inicio Rápido

### Opción A: Un comando (recomendado)

**Windows:**
```bash
start.bat
```

**Mac/Linux:**
```bash
chmod +x start.sh && ./start.sh
```

### Opción B: Paso a paso

```bash
# 1. Ir al backend
cd backend

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar (copiar plantilla)
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux

# 6. Iniciar servidor
python run.py
```

## URL y credenciales

- **URL:** http://localhost:5001
- **Email:** admin@qa.com
- **Password:** admin123
- **Datos de prueba:** http://localhost:5001/api/seed

## Notas

- Si NO configuras Supabase, el sistema usa SQLite automáticamente
- Flask sirve frontend + API en el mismo puerto (5001)
- No necesitas Node.js, PostgreSQL ni Redis para desarrollo local
- Para producción: configurar `DATABASE_URL` (Supabase) y `RATELIMIT_STORAGE_URL` (Redis)
