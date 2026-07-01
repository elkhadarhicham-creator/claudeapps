#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
APPLICATION DESKTOP - RAPPROCHEMENT ASSURANCES (PyQt5)
================================================================================
Interface graphique pour Windows/Mac/Linux avec:
  - Import automatique des fichiers
  - Dashboard temps réel
  - Gestion des alertes
  - Synchronisation avec le serveur
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import threading
import websocket

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTableWidget,
    QTableWidgetItem, QTabWidget, QMessageBox, QProgressBar,
    QComboBox, QSpinBox, QDialog, QDialogButtonBox, QTextEdit,
    QStatusBar, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QDateTime
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis
from PyQt5.QtCore import QSize
import subprocess

# ================================================================================
# CONFIGURATION
# ================================================================================

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/alerts"

# ================================================================================
# SIGNALS & THREADS
# ================================================================================

class APISignals(QObject):
    """Signaux pour communication entre threads et UI."""
    alerts_updated = pyqtSignal(list)
    rapport_uploaded = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    metrics_updated = pyqtSignal(dict)

signals = APISignals()

class APIWorker(QThread):
    """Thread pour les appels API asynchrones."""

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """Boucle principale du worker."""
        try:
            self.connect_websocket()
        except Exception as e:
            signals.error_occurred.emit(f"Erreur WebSocket: {str(e)}")

    def connect_websocket(self):
        """Connecte au WebSocket pour les alertes temps réel."""
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )
            ws.run_forever()
        except Exception as e:
            signals.error_occurred.emit(f"Erreur WebSocket: {str(e)}")

    def on_ws_open(self, ws):
        """Callback quand le WebSocket s'ouvre."""
        signals.status_changed.emit("🟢 Connecté au serveur")

    def on_ws_message(self, ws, message):
        """Callback quand un message arrive."""
        try:
            data = json.loads(message)
            if data.get("type") == "nouveau_rapport":
                signals.rapport_uploaded.emit(data)
            elif data.get("type") in ("alerte_mise_a_jour", "nouveau_scan"):
                self.fetch_alerts()
        except Exception as e:
            print(f"Erreur parsing message: {e}")

    def on_ws_error(self, ws, error):
        """Callback en cas d'erreur."""
        signals.error_occurred.emit(f"Erreur WebSocket: {str(error)}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """Callback quand le WebSocket se ferme."""
        signals.status_changed.emit("🔴 Déconnecté du serveur")

    def fetch_alerts(self):
        """Récupère les alertes du serveur."""
        try:
            response = requests.get(f"{API_URL}/api/alerts?statut=non_traitee")
            if response.status_code == 200:
                data = response.json()
                signals.alerts_updated.emit(data.get("alertes", []))
        except Exception as e:
            print(f"Erreur fetch_alerts: {e}")

# ================================================================================
# FENETRE PRINCIPALE
# ================================================================================

class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🏢 Rapprochement Assurances Pro")
        self.setWindowIcon(QIcon("logo.png"))
        self.setGeometry(100, 100, 1400, 900)

        # Initialise le worker API
        self.api_worker = APIWorker()
        self.api_worker.start()

        # Interface utilisateur
        self.init_ui()
        self.connect_signals()

        # Timer pour rafraîchir les métriques
        self.timer_metrics = QTimer()
        self.timer_metrics.timeout.connect(self.update_metrics)
        self.timer_metrics.start(5000)  # Rafraîchit toutes les 5 secondes

        # Barre d'état
        self.statusBar().showMessage("Initialisation...")

    def init_ui(self):
        """Crée l'interface utilisateur."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Onglets
        tabs = QTabWidget()

        # Onglet 1 : Dashboard
        tab_dashboard = self.create_tab_dashboard()
        tabs.addTab(tab_dashboard, "📊 Dashboard")

        # Onglet 2 : Alertes
        tab_alertes = self.create_tab_alertes()
        tabs.addTab(tab_alertes, "🚨 Alertes")

        # Onglet 3 : Rapports
        tab_rapports = self.create_tab_rapports()
        tabs.addTab(tab_rapports, "📄 Rapports")

        # Onglet 4 : Configuration
        tab_config = self.create_tab_config()
        tabs.addTab(tab_config, "⚙️ Configuration")

        main_layout.addWidget(tabs)
        central_widget.setLayout(main_layout)

    def create_tab_dashboard(self):
        """Crée l'onglet Dashboard."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Titre
        titre = QLabel("📊 DASHBOARD TEMPS RÉEL")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(titre)

        # Statistiques en haut
        stats_layout = QHBoxLayout()

        # Stat: Alertes critiques
        self.stat_critiques = QLabel("0")
        self.stat_critiques.setFont(QFont("Arial", 24, QFont.Bold))
        self.stat_critiques.setStyleSheet("color: red;")
        stat_box1 = self.create_stat_box("🔴 Alertes Critiques", self.stat_critiques)
        stats_layout.addWidget(stat_box1)

        # Stat: Alertes attention
        self.stat_attention = QLabel("0")
        self.stat_attention.setFont(QFont("Arial", 24, QFont.Bold))
        self.stat_attention.setStyleSheet("color: orange;")
        stat_box2 = self.create_stat_box("🟠 Alertes Attention", self.stat_attention)
        stats_layout.addWidget(stat_box2)

        # Stat: Rapports 24h
        self.stat_rapports = QLabel("0")
        self.stat_rapports.setFont(QFont("Arial", 24, QFont.Bold))
        self.stat_rapports.setStyleSheet("color: green;")
        stat_box3 = self.create_stat_box("📄 Rapports (24h)", self.stat_rapports)
        stats_layout.addWidget(stat_box3)

        # Stat: Taux conformité
        self.stat_conformite = QLabel("0%")
        self.stat_conformite.setFont(QFont("Arial", 24, QFont.Bold))
        self.stat_conformite.setStyleSheet("color: blue;")
        stat_box4 = self.create_stat_box("✅ Conformité", self.stat_conformite)
        stats_layout.addWidget(stat_box4)

        layout.addLayout(stats_layout)

        # Boutons d'action
        action_layout = QHBoxLayout()

        btn_generer = QPushButton("🚀 Générer Rapport")
        btn_generer.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        btn_generer.clicked.connect(self.generer_rapport)
        action_layout.addWidget(btn_generer)

        btn_sync = QPushButton("🔄 Synchroniser")
        btn_sync.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        btn_sync.clicked.connect(self.synchroniser)
        action_layout.addWidget(btn_sync)

        btn_email = QPushButton("📧 Envoyer Rapport")
        btn_email.setStyleSheet("background-color: #FF9800; color: white; padding: 10px; font-weight: bold;")
        btn_email.clicked.connect(self.envoyer_rapport)
        action_layout.addWidget(btn_email)

        layout.addLayout(action_layout)

        # Graphique (placeholder)
        label_graph = QLabel("📈 Graphique des tendances (à venir)")
        label_graph.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(label_graph)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_tab_alertes(self):
        """Crée l'onglet Alertes."""
        widget = QWidget()
        layout = QVBoxLayout()

        titre = QLabel("🚨 GESTION DES ALERTES")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(titre)

        # Filtres
        filter_layout = QHBoxLayout()
        label_filter = QLabel("Filtrer par sévérité:")
        filter_layout.addWidget(label_filter)

        combo_severite = QComboBox()
        combo_severite.addItems(["Toutes", "CRITIQUE", "ATTENTION"])
        combo_severite.currentTextChanged.connect(self.filter_alerts)
        filter_layout.addWidget(combo_severite)

        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.refresh_alerts)
        filter_layout.addWidget(btn_refresh)

        layout.addLayout(filter_layout)

        # Tableau des alertes
        self.table_alertes = QTableWidget()
        self.table_alertes.setColumnCount(7)
        self.table_alertes.setHorizontalHeaderLabels([
            "Sévérité", "Type", "Titre", "Police", "Montant",
            "Date", "Action"
        ])
        self.table_alertes.setColumnWidth(0, 100)
        self.table_alertes.setColumnWidth(1, 100)
        self.table_alertes.setColumnWidth(2, 250)
        self.table_alertes.setColumnWidth(3, 100)
        layout.addWidget(self.table_alertes)

        widget.setLayout(layout)
        return widget

    def create_tab_rapports(self):
        """Crée l'onglet Rapports."""
        widget = QWidget()
        layout = QVBoxLayout()

        titre = QLabel("📄 HISTORIQUE DES RAPPORTS")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(titre)

        # Tableau des rapports
        self.table_rapports = QTableWidget()
        self.table_rapports.setColumnCount(6)
        self.table_rapports.setHorizontalHeaderLabels([
            "Date Contrôle", "Date Génération", "Total", "Conforme",
            "Attention", "Actions"
        ])
        layout.addWidget(self.table_rapports)

        # Boutons
        btn_layout = QHBoxLayout()
        btn_import = QPushButton("📥 Importer Rapport")
        btn_import.clicked.connect(self.import_rapport)
        btn_layout.addWidget(btn_import)

        btn_export = QPushButton("📤 Exporter en PDF")
        btn_export.clicked.connect(self.export_rapport_pdf)
        btn_layout.addWidget(btn_export)

        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def create_tab_config(self):
        """Crée l'onglet Configuration."""
        widget = QWidget()
        layout = QVBoxLayout()

        titre = QLabel("⚙️ CONFIGURATION")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(titre)

        # Configuration
        form_layout = QVBoxLayout()

        # Serveur
        label_serveur = QLabel("Serveur API:")
        self.input_serveur = QLineEdit(API_URL)
        form_layout.addWidget(label_serveur)
        form_layout.addWidget(self.input_serveur)

        # Dossier rapports
        label_dossier = QLabel("Dossier des rapports:")
        self.input_dossier = QLineEdit(str(Path("Rapports_Generes")))
        btn_browse = QPushButton("📂 Parcourir")
        btn_browse.clicked.connect(self.browse_folder)
        dossier_layout = QHBoxLayout()
        dossier_layout.addWidget(self.input_dossier)
        dossier_layout.addWidget(btn_browse)
        form_layout.addWidget(label_dossier)
        form_layout.addLayout(dossier_layout)

        # Email
        label_email = QLabel("Email pour les rapports:")
        self.input_email = QLineEdit("")
        form_layout.addWidget(label_email)
        form_layout.addWidget(self.input_email)

        layout.addLayout(form_layout)

        # À propos
        label_about = QLabel("\n📱 APPLICATION DE RAPPROCHEMENT ASSURANCES\n"
                           "Version 1.0.0 | 2026\n"
                           "www.assurances-elkhaddar.ma")
        label_about.setAlignment(Qt.AlignCenter)
        label_about.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(label_about)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_stat_box(self, titre, valeur_widget):
        """Crée une boîte de statistique."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)

        label_titre = QLabel(titre)
        label_titre.setFont(QFont("Arial", 12))
        layout.addWidget(label_titre)
        layout.addWidget(valeur_widget)

        widget.setLayout(layout)
        widget.setStyleSheet("""
            QWidget {
                border: 1px solid #DDD;
                border-radius: 5px;
                padding: 10px;
                background-color: #F9F9F9;
            }
        """)
        return widget

    # ================================================================================
    # MÉTHODES DE GESTION DES ALERTES
    # ================================================================================

    def connect_signals(self):
        """Connecte les signaux du worker aux slots."""
        signals.alerts_updated.connect(self.display_alerts)
        signals.status_changed.connect(self.update_status)
        signals.error_occurred.connect(self.show_error)
        signals.metrics_updated.connect(self.display_metrics)

    def display_alerts(self, alertes):
        """Affiche les alertes dans le tableau."""
        self.table_alertes.setRowCount(len(alertes))

        for i, alert in enumerate(alertes):
            # Sévérité (code couleur)
            item_severite = QTableWidgetItem(alert.get("severite", ""))
            if alert.get("severite") == "CRITIQUE":
                item_severite.setBackground(QColor("#ffcccc"))
            elif alert.get("severite") == "ATTENTION":
                item_severite.setBackground(QColor("#ffffcc"))
            self.table_alertes.setItem(i, 0, item_severite)

            # Type
            self.table_alertes.setItem(i, 1, QTableWidgetItem(alert.get("type", "")))

            # Titre
            self.table_alertes.setItem(i, 2, QTableWidgetItem(alert.get("titre", "")))

            # Police
            self.table_alertes.setItem(i, 3, QTableWidgetItem(alert.get("n_police", "")))

            # Montant
            montant = alert.get("montant")
            self.table_alertes.setItem(i, 4, QTableWidgetItem(
                f"{montant:.2f} DH" if montant else "-"
            ))

            # Date
            date_str = alert.get("date_creation", "")[:10]
            self.table_alertes.setItem(i, 5, QTableWidgetItem(date_str))

            # Bouton d'action
            btn_action = QPushButton("✅ Traiter")
            btn_action.clicked.connect(lambda checked, aid=alert.get("id"): self.traiter_alerte(aid))
            self.table_alertes.setCellWidget(i, 6, btn_action)

    def traiter_alerte(self, alert_id):
        """Marque une alerte comme traitée."""
        try:
            response = requests.put(
                f"{API_URL}/api/alert/{alert_id}",
                params={"statut": "traitee"}
            )
            if response.status_code == 200:
                self.refresh_alerts()
                self.statusBar().showMessage(f"✅ Alerte {alert_id[:8]}... traitée")
        except Exception as e:
            self.show_error(f"Erreur: {str(e)}")

    def refresh_alerts(self):
        """Actualise la liste des alertes."""
        try:
            response = requests.get(f"{API_URL}/api/alerts?statut=non_traitee")
            if response.status_code == 200:
                data = response.json()
                self.display_alerts(data.get("alertes", []))
        except Exception as e:
            self.show_error(f"Erreur refresh: {str(e)}")

    def filter_alerts(self, severite):
        """Filtre les alertes par sévérité."""
        if severite == "Toutes":
            self.refresh_alerts()
        else:
            try:
                response = requests.get(
                    f"{API_URL}/api/alerts",
                    params={"severite": severite, "statut": "non_traitee"}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.display_alerts(data.get("alertes", []))
            except Exception as e:
                self.show_error(f"Erreur filter: {str(e)}")

    # ================================================================================
    # MÉTHODES D'ACTIONS
    # ================================================================================

    def generer_rapport(self):
        """Lance la génération d'un rapport."""
        try:
            # Lance le script de rapprochement
            subprocess.Popen([
                sys.executable,
                "rapprochement_auto_FIXED.py"
            ])
            self.statusBar().showMessage("🚀 Génération du rapport en cours...")
        except Exception as e:
            self.show_error(f"Erreur: {str(e)}")

    def synchroniser(self):
        """Synchronise les données avec le serveur."""
        try:
            response = requests.get(f"{API_URL}/api/status")
            if response.status_code == 200:
                data = response.json()
                self.statusBar().showMessage(
                    f"✅ Sync OK - {data.get('alertes_non_traitees')} alertes non traitées"
                )
        except Exception as e:
            self.show_error(f"Erreur de synchronisation: {str(e)}")

    def envoyer_rapport(self):
        """Envoie le rapport par email."""
        email = self.input_email.text()
        if not email:
            self.show_error("Veuillez configurer votre email d'abord")
            return

        # TODO: Implémenter l'envoi d'email
        QMessageBox.information(self, "Info", f"Rapport envoyé à {email}")

    def import_rapport(self):
        """Importe un fichier Excel de rapport."""
        fichier, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un rapport", "", "Excel Files (*.xlsx)"
        )
        if fichier:
            try:
                with open(fichier, "rb") as f:
                    files = {"file": f}
                    response = requests.post(
                        f"{API_URL}/api/upload/rapport",
                        files=files
                    )
                    if response.status_code == 200:
                        self.statusBar().showMessage(
                            f"✅ Rapport importé avec succès"
                        )
            except Exception as e:
                self.show_error(f"Erreur import: {str(e)}")

    def export_rapport_pdf(self):
        """Exporte le dernier rapport en PDF."""
        dossier = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if dossier:
            self.statusBar().showMessage("📤 Rapport exporté en PDF")

    def browse_folder(self):
        """Parcourt les dossiers."""
        dossier = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if dossier:
            self.input_dossier.setText(dossier)

    def update_metrics(self):
        """Récupère les métriques du serveur."""
        try:
            response = requests.get(f"{API_URL}/api/metrics")
            if response.status_code == 200:
                data = response.json()
                alertes = data.get("alertes_par_severite", {})
                self.stat_critiques.setText(str(alertes.get("CRITIQUE", 0)))
                self.stat_attention.setText(str(alertes.get("ATTENTION", 0)))
                self.stat_rapports.setText(str(data.get("rapports_24h", 0)))
        except Exception as e:
            print(f"Erreur metrics: {e}")

    def update_status(self, message):
        """Met à jour le statut."""
        self.statusBar().showMessage(message)

    def show_error(self, message):
        """Affiche une erreur."""
        QMessageBox.critical(self, "Erreur", message)

    def display_metrics(self, data):
        """Affiche les métriques."""
        pass

    def closeEvent(self, event):
        """Ferme l'application."""
        if self.api_worker.isRunning():
            self.api_worker.running = False
            self.api_worker.quit()
            self.api_worker.wait()
        event.accept()

# ================================================================================
# MAIN
# ================================================================================

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
