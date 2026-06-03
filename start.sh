#!/usr/bin/env bash
set -e

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     MUROTECH SaaS - Inicio Local         ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── Ir al directorio del backend ──
cd "$(dirname "$0")/backend"

# ── Verificar Python ──
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado."
    echo "Instálalo con: brew install python3  o  sudo apt install python3 python3-venv"
    exit 1
fi

# ── Crear entorno virtual si no existe ──
if [ ! -d "venv" ]; then
    echo "[1/4] Creando entorno virtual..."
    python3 -m venv venv
else
    echo "[1/4] Entorno virtual ya existe ✓"
fi

# ── Activar venv e instalar dependencias ──
echo "[2/4] Instalando dependencias..."
source venv/bin/activate
pip install -r requirements.txt -q

# ── Crear .env si no existe ──
if [ ! -f ".env" ]; then
    echo "[3/4] Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo ""
    echo "    ⚠  Se creó .env con valores por defecto."
    echo "    Si quieres conectar a Supabase, edita backend/.env"
    echo "    y agrega tu DATABASE_URL."
    echo ""
else
    echo "[3/4] Archivo .env ya existe ✓"
fi

# ── Crear base de datos ──
echo "[4/4] Inicializando base de datos..."
python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); print('  Base de datos lista ✓')"

# ── Cargar datos demo ──
echo ""
read -p "¿Deseas cargar datos de prueba? (admin@qa.com / admin123) [S/n]: " SEED
if [ "$SEED" = "n" ] || [ "$SEED" = "N" ]; then
    echo "Datos de prueba omitidos."
else
    echo "Cargando datos de prueba..."
    python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); app.test_client().get('/api/seed'); print('  Datos de prueba cargados ✓')"
fi

# ── Iniciar servidor ──
echo ""
echo "  ────────────────────────────────────────────"
echo "   🚀 Servidor listo en: http://localhost:5001"
echo "   📧 Demo:  admin@qa.com / admin123"
echo "  ────────────────────────────────────────────"
echo ""
echo "  Presiona Ctrl+C para detener el servidor."
echo ""

python run.py
