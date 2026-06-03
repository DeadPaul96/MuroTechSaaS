@echo off
echo 🌐 Abriendo MUROTECH Frontend en Google Chrome...
echo 📍 Archivo: frontend/index.html
echo 🔗 Backend debe estar corriendo en http://localhost:5000
echo.

cd /d "%~dp0"

REM Ruta completa al archivo index.html
set FRONTEND_PATH=%~dp0frontend\index.html

REM Abrir en Chrome
start chrome "%FRONTEND_PATH%"

echo ✅ Frontend abierto en Chrome
echo 💡 Si no se abre, verifica que Chrome esté instalado
pause