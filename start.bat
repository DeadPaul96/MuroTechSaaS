@echo off
chcp 65001 >nul
title MUROTECH SaaS - Inicio Local

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     MUROTECH SaaS - Inicio Local         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Ir al directorio del backend ──
cd /d "%~dp0backend"

:: ── Verificar Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo Descárgalo de: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ── Crear entorno virtual si no existe ──
if not exist "venv\" (
    echo [1/4] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/4] Entorno virtual ya existe ✓
)

:: ── Activar venv e instalar dependencias ──
echo [2/4] Instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

:: ── Crear .env si no existe ──
if not exist ".env" (
    echo [3/4] Creando archivo .env desde .env.example...
    copy .env.example .env >nul
    echo.
    echo     ⚠  Se creó .env con valores por defecto.
    echo     Si quieres conectar a Supabase, edita backend\.env
    echo     y agrega tu DATABASE_URL.
    echo.
) else (
    echo [3/4] Archivo .env ya existe ✓
)

:: ── Crear base de datos y datos de prueba ──
echo [4/4] Inicializando base de datos...
python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); print('  Base de datos lista ✓')"

:: ── Cargar datos demo ──
echo.
echo ¿Deseas cargar datos de prueba? (admin@qa.com / admin123)
set /p SEED="  [S/n]: "
if /i "%SEED%"=="n" (
    echo Datos de prueba omitidos.
) else (
    echo Cargando datos de prueba...
    python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); app.test_client().get('/api/seed'); print('  Datos de prueba cargados ✓')"
)

:: ── Iniciar servidor ──
echo.
echo  ────────────────────────────────────────────
echo   🚀 Servidor listo en: http://localhost:5001
echo   📧 Demo:  admin@qa.com / admin123
echo  ────────────────────────────────────────────
echo.
echo  Presiona Ctrl+C para detener el servidor.
echo.

python run.py
