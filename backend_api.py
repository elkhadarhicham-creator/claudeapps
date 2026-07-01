#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
BACKEND API - RAPPROCHEMENT ASSURANCES (FastAPI)
================================================================================
API REST pour synchronisation desktop + mobile, gestion des rapports,
alertes temps réel via WebSocket.

Endpoints:
  GET  /api/status           - État du système
  POST /api/upload/pdf       - Upload PDF encaissements
  GET  /api/rapports         - Liste des rapports
  GET  /api/rapport/{id}     - Détail d'un rapport
  GET  /api/alerts           - Alertes non traitées
  PUT  /api/alert/{id}       - Mettre à jour une alerte
  GET  /ws/alerts            - WebSocket pour alertes temps réel
"""

from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import uuid

app = FastAPI(title="API Rapprochement Assurances", version="1.0.0")

# CORS - Permet la communication avec les apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_PATH = "rapprochement.db"
UPLOADS_PATH = Path("uploads")
UPLOADS_PATH.mkdir(exist_ok=True)

# Stockage des connexions WebSocket actives
active_connections = []

# ================================================================================
# DATABASE INITIALIZATION
# ================================================================================

def init_db():
    """Crée les tables de la base de données."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rapports (
            id TEXT PRIMARY KEY,
            date_controle TEXT NOT NULL,
            date_generation TEXT NOT NULL,
            nb_total INTEGER,
            nb_conforme INTEGER,
            nb_attention INTEGER,
            nb_critique INTEGER,
            taux_conformite REAL,
            fichier_excel TEXT,
            statut TEXT DEFAULT 'en_cours'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id TEXT PRIMARY KEY,
            rapport_id TEXT NOT NULL,
            type TEXT NOT NULL,
            severite TEXT DEFAULT 'ATTENTION',
            titre TEXT NOT NULL,
            description TEXT,
            n_quittance TEXT,
            n_police TEXT,
            assuré TEXT,
            montant REAL,
            date_creation TEXT,
            date_resolution TEXT,
            statut TEXT DEFAULT 'non_traitee',
            FOREIGN KEY (rapport_id) REFERENCES rapports(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            n_attestation TEXT NOT NULL UNIQUE,
            date_scan TEXT,
            fichier_chemin TEXT,
            date_upload TEXT,
            statut TEXT DEFAULT 'present'
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def get_db():
    """Retourne une connexion à la base de données."""
    return sqlite3.connect(DB_PATH)

def notify_clients(message):
    """Envoie une notification à tous les clients WebSocket connectés."""
    asyncio.create_task(_broadcast(message))

async def _broadcast(message):
    """Diffuse le message à tous les clients."""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)

    for connection in disconnected:
        active_connections.remove(connection)

# ================================================================================
# ENDPOINTS
# ================================================================================

@app.get("/")
async def root():
    """Page d'accueil."""
    return {
        "nom": "API Rapprochement Assurances",
        "version": "1.0.0",
        "status": "🟢 En ligne",
        "docs": "/docs"
    }

@app.get("/api/status")
async def get_status():
    """État du système."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM rapports")
    nb_rapports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alertes WHERE statut = 'non_traitee'")
    nb_alertes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM scans")
    nb_scans = cursor.fetchone()[0]

    conn.close()

    return {
        "status": "en_ligne",
        "timestamp": datetime.now().isoformat(),
        "rapports_generes": nb_rapports,
        "alertes_non_traitees": nb_alertes,
        "scans_traites": nb_scans,
        "version": "1.0.0"
    }

@app.post("/api/upload/rapport")
async def upload_rapport(file: UploadFile = File(...)):
    """Upload un fichier Excel de rapport généré."""
    try:
        rapport_id = str(uuid.uuid4())
        fichier_chemin = UPLOADS_PATH / f"{rapport_id}_{file.filename}"

        # Sauvegarde le fichier
        contenu = await file.read()
        with open(fichier_chemin, "wb") as f:
            f.write(contenu)

        # Enregistre en base de données
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO rapports
            (id, date_controle, date_generation, fichier_excel, statut)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rapport_id,
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().isoformat(),
            str(fichier_chemin),
            "en_cours"
        ))

        conn.commit()
        conn.close()

        # Notifie les clients
        notify_clients({
            "type": "nouveau_rapport",
            "rapport_id": rapport_id,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "success",
            "rapport_id": rapport_id,
            "message": "Rapport uploadé avec succès"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/rapports")
async def list_rapports():
    """Liste tous les rapports."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date_controle, date_generation, nb_total,
               nb_conforme, nb_attention, nb_critique, taux_conformite, statut
        FROM rapports
        ORDER BY date_generation DESC
        LIMIT 30
    """)

    rapports = []
    for row in cursor.fetchall():
        rapports.append({
            "id": row[0],
            "date_controle": row[1],
            "date_generation": row[2],
            "nb_total": row[3],
            "nb_conforme": row[4],
            "nb_attention": row[5],
            "nb_critique": row[6],
            "taux_conformite": row[7],
            "statut": row[8]
        })

    conn.close()
    return {"rapports": rapports}

@app.get("/api/rapport/{rapport_id}")
async def get_rapport(rapport_id: str):
    """Détail d'un rapport."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date_controle, date_generation, nb_total,
               nb_conforme, nb_attention, nb_critique, taux_conformite, statut
        FROM rapports WHERE id = ?
    """, (rapport_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Rapport non trouvé")

    rapport = {
        "id": row[0],
        "date_controle": row[1],
        "date_generation": row[2],
        "nb_total": row[3],
        "nb_conforme": row[4],
        "nb_attention": row[5],
        "nb_critique": row[6],
        "taux_conformite": row[7],
        "statut": row[8]
    }

    # Alertes du rapport
    cursor.execute("""
        SELECT id, type, severite, titre, description, n_quittance,
               n_police, assuré, montant, date_creation, statut
        FROM alertes WHERE rapport_id = ?
        ORDER BY date_creation DESC
    """, (rapport_id,))

    alertes = []
    for row in cursor.fetchall():
        alertes.append({
            "id": row[0],
            "type": row[1],
            "severite": row[2],
            "titre": row[3],
            "description": row[4],
            "n_quittance": row[5],
            "n_police": row[6],
            "assuré": row[7],
            "montant": row[8],
            "date_creation": row[9],
            "statut": row[10]
        })

    rapport["alertes"] = alertes
    conn.close()

    return rapport

@app.get("/api/alerts")
async def list_alerts(severite: str = None, statut: str = "non_traitee"):
    """Liste les alertes."""
    conn = get_db()
    cursor = conn.cursor()

    if severite:
        cursor.execute("""
            SELECT id, rapport_id, type, severite, titre, description,
                   n_quittance, n_police, assuré, montant, date_creation, statut
            FROM alertes
            WHERE severite = ? AND statut = ?
            ORDER BY date_creation DESC
            LIMIT 100
        """, (severite, statut))
    else:
        cursor.execute("""
            SELECT id, rapport_id, type, severite, titre, description,
                   n_quittance, n_police, assuré, montant, date_creation, statut
            FROM alertes
            WHERE statut = ?
            ORDER BY date_creation DESC
            LIMIT 100
        """, (statut,))

    alertes = []
    for row in cursor.fetchall():
        alertes.append({
            "id": row[0],
            "rapport_id": row[1],
            "type": row[2],
            "severite": row[3],
            "titre": row[4],
            "description": row[5],
            "n_quittance": row[6],
            "n_police": row[7],
            "assuré": row[8],
            "montant": row[9],
            "date_creation": row[10],
            "statut": row[11]
        })

    conn.close()
    return {"alertes": alertes}

@app.put("/api/alert/{alert_id}")
async def update_alert(alert_id: str, statut: str = "traitee", notes: str = None):
    """Marque une alerte comme traitée."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE alertes
        SET statut = ?, date_resolution = ?
        WHERE id = ?
    """, (statut, datetime.now().isoformat(), alert_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Alerte non trouvée")

    conn.commit()
    conn.close()

    # Notifie les clients
    notify_clients({
        "type": "alerte_mise_a_jour",
        "alert_id": alert_id,
        "nouveau_statut": statut,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "success",
        "message": f"Alerte {alert_id} marquée comme {statut}"
    }

@app.post("/api/scan/register")
async def register_scan(n_attestation: str, date_scan: str):
    """Enregistre un scan d'attestation."""
    conn = get_db()
    cursor = conn.cursor()

    scan_id = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO scans (id, n_attestation, date_scan, date_upload, statut)
        VALUES (?, ?, ?, ?, ?)
    """, (
        scan_id,
        n_attestation,
        date_scan,
        datetime.now().isoformat(),
        "present"
    ))

    conn.commit()
    conn.close()

    notify_clients({
        "type": "nouveau_scan",
        "n_attestation": n_attestation,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "success",
        "scan_id": scan_id
    }

# ================================================================================
# WEBSOCKET - ALERTES TEMPS RÉEL
# ================================================================================

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket pour les alertes temps réel."""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        # Envoie l'état initial
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM alertes WHERE statut = 'non_traitee'
        """)
        nb_alertes = cursor.fetchone()[0]
        conn.close()

        await websocket.send_json({
            "type": "initial_state",
            "alertes_non_traitees": nb_alertes,
            "timestamp": datetime.now().isoformat()
        })

        # Garde la connexion ouverte
        while True:
            data = await websocket.receive_text()
            # Peut être utilisé pour des commands du client
            print(f"Message reçu: {data}")
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
    finally:
        active_connections.remove(websocket)

# ================================================================================
# HEALTH CHECK & METRICS
# ================================================================================

@app.get("/api/health")
async def health_check():
    """Vérification de santé du système."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/metrics")
async def get_metrics():
    """Métriques du système."""
    conn = get_db()
    cursor = conn.cursor()

    # Compte les alertes par sévérité
    cursor.execute("""
        SELECT severite, COUNT(*)
        FROM alertes
        WHERE statut = 'non_traitee'
        GROUP BY severite
    """)

    alertes_par_severite = {}
    for row in cursor.fetchall():
        alertes_par_severite[row[0]] = row[1]

    # Rapports du dernier jour
    cursor.execute("""
        SELECT COUNT(*) FROM rapports
        WHERE date_generation >= datetime('now', '-1 day')
    """)
    rapports_24h = cursor.fetchone()[0]

    conn.close()

    return {
        "timestamp": datetime.now().isoformat(),
        "alertes_par_severite": alertes_par_severite,
        "rapports_24h": rapports_24h,
        "connexions_websocket": len(active_connections)
    }

# ================================================================================
# RUN
# ================================================================================

if __name__ == "__main__":
    print("🚀 Démarrage du serveur API...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
