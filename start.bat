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

:: Iniciar servidor
echo.
echo  ----------------------------------------
echo   Servidor listo en: http://localhost:5001
echo   Usuarios disponibles:
echo     superadmin@murotech.com / SuperAdmin2026!
echo     admin@murotech.com      / Admin2026!
echo     admin@qa.com            / admin123
echo  ----------------------------------------
echo.
echo  Abre: frontend\html\inicioSesion.html
echo  Presiona Ctrl+C para detener el servidor.
echo.

python run.py
