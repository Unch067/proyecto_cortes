@echo off
echo ==============================================
echo Optimizador de Cortes - Grupo 3
echo Preparando entorno local...
echo ==============================================

python -m venv venv
call venv\Scripts\activate
echo Instalando dependencias...
pip install -r requirements.txt -q
echo Iniciando aplicacion...
streamlit run app.py
pause