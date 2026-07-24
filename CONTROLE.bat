@echo off
chcp 65001 >nul
cls
echo.
echo  ================================================================
echo    CONTROLE QUOTIDIEN - RAPPROCHEMENT ASSURANCES
echo  ================================================================
echo.
echo    Ce programme va :
echo      1. Demander une DATE ou une PERIODE (date de debut -^> date de fin)
echo      2. Lire les encaissements et rapports compagnies de la periode
echo      3. Verifier les attestations scannees (\\KARIMA\images analisis)
echo      4. Generer le rapport Excel dans le dossier Rapports_Generes
echo.
echo    Astuce : pour un seul jour, laissez la date de FIN vide (Entree).
echo.
echo  ================================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR : Python n'est pas installe.
    echo  Telechargez-le depuis : https://www.python.org/downloads/
    pause
    exit /b 1
)

python rapprochement_auto_FIXED.py

if errorlevel 1 (
    echo.
    echo  Une erreur est survenue. Envoyez une capture d'ecran pour assistance.
    pause
)
