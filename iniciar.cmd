@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero instala el entorno siguiendo las instrucciones del README.
  pause
  exit /b 1
)
echo Abre http://127.0.0.1:7860/ y manten esta ventana abierta.
".venv\Scripts\python.exe" app.py
pause
