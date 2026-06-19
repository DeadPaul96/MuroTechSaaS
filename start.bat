@echo off
chcp 65001 >nul
title MUROTECH SaaS - Inicio Local

echo.
echo  MUROTECH SaaS - Inicio Local
echo  ===============================
echo.

:: Ir al directorio del backend
cd /d "%~dp0backend"

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Descargalo de: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Crear entorno virtual si no existe
if not exist "venv\" (
    echo [1/5] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/5] Entorno virtual ya existe.
)

:: Activar venv e instalar dependencias
echo [2/5] Instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

:: Crear .env si no existe
if not exist ".env" (
    echo [3/5] Creando archivo .env...
    copy .env.example .env >nul
    echo     .env creado con configuracion de Supabase lista.
) else (
    echo [3/5] Archivo .env ya existe.
)

:: Aplicar migraciones (agrega columnas faltantes sin borrar datos)
echo [4/5] Aplicando migraciones de base de datos...
python scripts\migrate_db.py
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo conectar a la base de datos.
    echo Verifica tu conexion a internet - el proyecto usa Supabase en la nube.
    pause
    exit /b 1
)

:: Cargar datos demo
echo [5/5] Verificando datos de prueba...
echo.
set /p SEED="Deseas cargar datos de prueba? (admin@qa.com / admin123) [S/n]: "
if /i "%SEED%"=="n" (
    echo Datos de prueba omitidos.
) else (
    echo Cargando datos de prueba...
    python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); app.test_client().get('/api/seed'); print('  Datos de prueba cargados')"
)

:: Iniciar servidor
echo.
echo  ----------------------------------------
echo   Servidor listo en: http://localhost:5001
echo   Demo: admin@qa.com / admin123
echo  ----------------------------------------
echo.
echo  Abre tu navegador y ve a: http://localhost:5001
echo  Presiona Ctrl+C para detener el servidor.
echo.

python run.py
