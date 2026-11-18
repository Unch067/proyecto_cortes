@echo off
cd /d "%~dp0"
echo ==============================================
echo Optimizador de Cortes - Grupo 3
echo Preparando entorno local...
echo ==============================================

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

echo Instalando/verificando dependencias en venv...
.\venv\Scripts\python.exe -m pip install -r requirements.txt -q

echo Iniciando aplicacion desde venv...
.\venv\Scripts\python.exe -m streamlit run app.py
pause