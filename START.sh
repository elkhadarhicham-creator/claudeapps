#!/bin/bash

clear

echo ""
echo "========================================================"
echo "  RAPPROCHEMENT ASSURANCES - Plateforme Complete"
echo "  Version 1.0.0"
echo "========================================================"
echo ""

# Verifier si Python est installe
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 n'est pas installe"
    echo "Installez Python 3.9+ avec: brew install python3 (Mac) ou apt install python3 (Linux)"
    exit 1
fi

echo "[1/3] Activation de l'environnement virtuel..."
if [ ! -d "venv" ]; then
    echo "Creation de l'environnement virtuel..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "[2/3] Installation des dependances..."
pip install -r requirements.txt > /dev/null 2>&1

echo "[3/3] Demarrage du serveur backend..."
echo ""
echo "========================================================"
echo "  Serveur API en cours de demarrage..."
echo "  URL: http://localhost:8000"
echo "  Documentation: http://localhost:8000/docs"
echo "========================================================"
echo ""

# Ouvrir dans le navigateur (optionnel)
if command -v open &> /dev/null; then
    open http://localhost:8000/docs  # Mac
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000/docs  # Linux
fi

python backend_api.py
