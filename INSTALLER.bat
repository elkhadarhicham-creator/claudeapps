@echo off
chcp 65001 >nul
color 0A
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║   RAPPROCHEMENT ASSURANCES - INSTALLATION AUTOMATIQUE     ║
echo ║   Version 1.0.0                                           ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Vérifier si Python est installé
echo [1/5] Vérification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERREUR: Python n'est pas installé!
    echo.
    echo SOLUTION:
    echo 1. Allez sur: https://www.python.org/downloads/
    echo 2. Cliquez sur "Download Python 3.11"
    echo 3. Lancez l'installateur
    echo 4. IMPORTANT: Cochez "Add Python to PATH"
    echo 5. Cliquez "Install Now"
    echo 6. Redémarrez votre ordinateur
    echo 7. Relancez ce fichier
    echo.
    pause
    exit /b 1
)
echo ✅ Python trouvé!
python --version

echo.
echo [2/5] Création de l'environnement virtuel...
if not exist venv (
    python -m venv venv
    echo ✅ Environnement créé!
) else (
    echo ✅ Environnement déjà existe!
)

echo.
echo [3/5] Activation de l'environnement...
call venv\Scripts\activate.bat
echo ✅ Activé!

echo.
echo [4/5] Installation des dépendances Python...
echo      (Cela peut prendre 2-3 minutes...)
pip install -q fastapi uvicorn pandas pdfplumber openpyxl PyQt5 websocket-client requests python-multipart
echo ✅ Dépendances installées!

echo.
echo [5/5] Création des raccourcis...

REM Créer un raccourci pour démarrer le backend
echo @echo off > DEMARRER_SERVEUR.bat
echo cd /d "%%~dp0" >> DEMARRER_SERVEUR.bat
echo call venv\Scripts\activate.bat >> DEMARRER_SERVEUR.bat
echo python backend_api.py >> DEMARRER_SERVEUR.bat
echo pause >> DEMARRER_SERVEUR.bat

REM Créer un raccourci pour démarrer l'app desktop
echo @echo off > DEMARRER_APP.bat
echo cd /d "%%~dp0" >> DEMARRER_APP.bat
echo call venv\Scripts\activate.bat >> DEMARRER_APP.bat
echo python app_desktop.py >> DEMARRER_APP.bat
echo pause >> DEMARRER_APP.bat

echo ✅ Raccourcis créés!

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          ✅ INSTALLATION RÉUSSIE!                          ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📁 Vous avez maintenant 2 nouveaux fichiers:
echo.
echo    1️⃣  DEMARRER_SERVEUR.bat
echo        → Double-cliquez pour lancer le serveur
echo        → Laissez-le ouvert!
echo.
echo    2️⃣  DEMARRER_APP.bat
echo        → Double-cliquez pour lancer l'application
echo        → Cela ouvre la fenêtre principale
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo 🚀 COMMENCEZ PAR:
echo.
echo    ÉTAPE 1: Double-cliquez sur "DEMARRER_SERVEUR.bat"
echo             (Laissez le terminal noir ouvert)
echo.
echo    ÉTAPE 2: Double-cliquez sur "DEMARRER_APP.bat"
echo             (L'application s'ouvre)
echo.
echo    ÉTAPE 3: Ouvrez http://localhost:8000/docs
echo             pour voir la documentation
echo.
echo ════════════════════════════════════════════════════════════
echo.

pause
