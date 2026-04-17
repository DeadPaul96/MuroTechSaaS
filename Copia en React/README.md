# MUROTECH SaaS - Copia en React & Python

Esta es una copia idéntica del sistema de facturación MUROTECH, migrada a una arquitectura moderna utilizando **React** para el frontend y **Python (Flask)** para el backend.

## Estructura del Proyecto

- `/frontend`: Proyecto React inicializado con Vite.
  - Usa `react-router-dom` para la navegación.
  - Implementa el diseño **Flat & Dense** original.
  - Totalmente responsivo y optimizado para dispositivos móviles.
- `/backend`: Servidor API en Python (Flask) configurado para conexión con SQL Server.

## Cómo ejecutar

### Frontend
1. Entra a la carpeta `frontend`.
2. Ejecuta `npm install` para instalar las dependencias.
3. Ejecuta `npm run dev` para iniciar el servidor de desarrollo.

### Backend
1. Entra a la carpeta `backend`.
2. Asegúrate de tener Python instalado.
3. Instala los requerimientos: `pip install -r requirements.txt`.
4. Ejecuta el servidor: `python api/app.py`.

## Características Migradas
- [x] Identidad Visual (Logos y Colores).
- [x] Fondo Animado con Blobs Dinámicos.
- [x] Pantalla de Inicio de Sesión (React).
- [x] Pantalla de Registro (React).
- [x] Sistema de Tokens de Diseño.
