@echo off
echo 🚀 Iniciando MUROTECH SaaS Backend...
echo 📍 URL: http://localhost:5001
echo 🔒 Asegúrate de configurar las variables de entorno

echo.
cd /d "%~dp0"

REM Verificar si existe .env y cargarlo (opcional)
if exist .env (
    echo Cargando variables de entorno desde .env...
    for /f "tokens=*" %%i in (.env) do set %%i
)

REM Ejecutar el backend
python run.py

pause