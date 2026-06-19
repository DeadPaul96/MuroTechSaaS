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
    echo [1/4] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/4] Entorno virtual ya existe.
)

:: Activar venv e instalar dependencias
echo [2/4] Instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

:: Crear .env si no existe
if not exist ".env" (
    echo [3/4] Creando archivo .env y generando claves seguras...
    copy .env.example .env >nul

    :: Generar SECRET_KEY unica
    for /f "delims=" %%K in ('python -c "import secrets; print(secrets.token_hex(32))"') do set GEN_SECRET=%%K
    powershell -Command "(Get-Content .env) -replace 'SECRET_KEY=TU_SECRET_KEY_AQUI', 'SECRET_KEY=%GEN_SECRET%' | Set-Content .env"

    :: Generar ENCRYPTION_KEY unica
    for /f "delims=" %%E in ('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"') do set GEN_ENC=%%E
    powershell -Command "(Get-Content .env) -replace 'ENCRYPTION_KEY=TU_ENCRYPTION_KEY_AQUI', 'ENCRYPTION_KEY=%GEN_ENC%' | Set-Content .env"

    :: Generar CSRF_SECRET unico
    for /f "delims=" %%C in ('python -c "import secrets; print(secrets.token_hex(24))"') do set GEN_CSRF=%%C
    powershell -Command "(Get-Content .env) -replace 'CSRF_SECRET=TU_CSRF_SECRET_AQUI', 'CSRF_SECRET=%GEN_CSRF%' | Set-Content .env"

    echo.
    echo     .env creado con claves seguras generadas automaticamente.
    echo     Si quieres Supabase, edita backend\.env y agrega DATABASE_URL.
    echo.
) else (
    echo [3/4] Archivo .env ya existe.
)

:: Inicializar base de datos
echo [4/4] Inicializando base de datos...
python -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); print('  Base de datos lista')"
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo inicializar la base de datos.
    echo Revisa los errores de arriba y asegurate de que requirements.txt se instalo correctamente.
    pause
    exit /b 1
)

:: Cargar datos demo
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
echo  Presiona Ctrl+C para detener el servidor.
echo.

python run.py
