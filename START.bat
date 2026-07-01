@echo off
cls
echo.
echo ========================================================
echo  RAPPROCHEMENT ASSURANCES - Plateforme Complete
echo  Version 1.0.0
echo ========================================================
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python n'est pas installe ou pas dans le PATH
    echo Telecharger Python 3.9+ depuis: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Activation de l'environnement virtuel...
if not exist venv (
    echo Creation de l'environnement virtuel...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/3] Installation des dependances...
pip install -r requirements.txt >nul 2>&1

echo [3/3] Demarrage du serveur backend...
echo.
echo ========================================================
echo  Serveur API en cours de demarrage...
echo  URL: http://localhost:8000
echo  Documentation: http://localhost:8000/docs
echo ========================================================
echo.

start http://localhost:8000/docs
python backend_api.py

pause
