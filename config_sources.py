#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration des sources de fichiers pour le rapprochement automatique.
Gère les chemins locaux et réseau.
"""

import os
from pathlib import Path

# ================================================================================
# CONFIGURATION DES SOURCES DE DONNÉES
# ================================================================================

# Google Drive mappé localement
GOOGLE_DRIVE_PATH = r"G:\Mon Drive"

# Partage réseau pour les attestations
ATTESTATIONS_NETWORK_PATH = r"\\KARIMA\images analisis\A 204570153"

# ================================================================================
# SOURCES DE FICHIERS
# ================================================================================

class SourcesData:
    """Gestionnaire des sources de données."""

    @staticmethod
    def chercher_encaissements(date_str=None):
        """
        Cherche le fichier PDF d'encaissements.
        Format: Etat des encaissements01.07.2026.pdf

        Args:
            date_str: Date au format DD.MM.YYYY (optionnel)

        Returns:
            Path: Chemin du fichier trouvé, ou None
        """
        if not os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"⚠️ ERREUR: {GOOGLE_DRIVE_PATH} n'existe pas")
            return None

        pattern = "Etat des encaissements*.pdf"
        fichiers = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))

        if not fichiers:
            print(f"❌ Aucun fichier trouvé matching '{pattern}' dans {GOOGLE_DRIVE_PATH}")
            return None

        # Si date spécifiée, chercher ce jour exact
        if date_str:
            for f in fichiers:
                if date_str in f.name:
                    return f

        # Sinon retourner le plus récent
        fichier = sorted(fichiers, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        print(f"✅ Encaissements trouvés: {fichier.name}")
        return fichier

    @staticmethod
    def chercher_rapports_compagnies(date_str=None):
        """
        Cherche les fichiers Excel des rapports des compagnies.
        Format: RAPPORT [COMPAGNIE] DD-MM-YYYY.xlsx

        Compagnies attendues: MATU, SANLAM, WAFA, MAROC ASSISTANCE

        Args:
            date_str: Date au format DD-MM-YYYY (optionnel)

        Returns:
            Dict: {nom_compagnie: Path}
        """
        if not os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"⚠️ ERREUR: {GOOGLE_DRIVE_PATH} n'existe pas")
            return {}

        compagnies = ["MATU", "SANLAM", "WAFA", "MAROC ASSISTANCE"]
        rapports = {}

        for cie in compagnies:
            pattern = f"RAPPORT {cie} *.xlsx"
            fichiers = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))

            if not fichiers:
                print(f"⚠️ Aucun rapport trouvé pour {cie}")
                continue

            # Si date spécifiée, chercher ce jour exact
            if date_str:
                for f in fichiers:
                    if date_str in f.name:
                        rapports[cie] = f
                        print(f"✅ Rapport {cie} trouvé: {f.name}")
                        break
            else:
                # Sinon retourner le plus récent
                f = sorted(fichiers, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                rapports[cie] = f
                print(f"✅ Rapport {cie} trouvé: {f.name}")

        return rapports

    @staticmethod
    def chercher_attestations(numero_attestation=None):
        """
        Cherche les fichiers des attestations.
        Format: [numero].pdf (ex: 001.pdf, 002.jpg)

        Args:
            numero_attestation: Numéro spécifique (optionnel)

        Returns:
            Dict or Path: Tous les fichiers, ou fichier spécifique
        """
        if not os.path.exists(ATTESTATIONS_NETWORK_PATH):
            print(f"⚠️ ERREUR: {ATTESTATIONS_NETWORK_PATH} n'existe pas")
            return {}

        # Lister tous les fichiers (PDF, JPG, PNG, etc.)
        attestations = {}
        extensions = ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tif', '*.tiff']

        for ext in extensions:
            fichiers = list(Path(ATTESTATIONS_NETWORK_PATH).glob(ext))
            for f in fichiers:
                # Extraire le numéro du nom du fichier
                nom_base = f.stem.lower()
                attestations[nom_base] = f

        if attestations:
            print(f"✅ {len(attestations)} attestation(s) trouvée(s)")
        else:
            print(f"⚠️ Aucune attestation trouvée dans {ATTESTATIONS_NETWORK_PATH}")

        if numero_attestation:
            numero_norm = str(numero_attestation).lower().zfill(3)
            return attestations.get(numero_norm)

        return attestations

    @staticmethod
    def verifier_connectivite():
        """Vérifie que tous les chemins sont accessibles."""
        print("\n📁 Vérification des chemins...")

        # Vérifier Google Drive
        if os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"✅ Google Drive accessible: {GOOGLE_DRIVE_PATH}")
        else:
            print(f"❌ Google Drive NON accessible: {GOOGLE_DRIVE_PATH}")
            return False

        # Vérifier partage réseau
        if os.path.exists(ATTESTATIONS_NETWORK_PATH):
            print(f"✅ Partage réseau accessible: {ATTESTATIONS_NETWORK_PATH}")
        else:
            print(f"❌ Partage réseau NON accessible: {ATTESTATIONS_NETWORK_PATH}")
            return False

        print("✅ Tous les chemins sont accessibles!\n")
        return True


if __name__ == "__main__":
    # Test
    print("=" * 60)
    print("TEST DES SOURCES DE DONNÉES")
    print("=" * 60)

    SourcesData.verifier_connectivite()

    print("\n📄 Recherche des encaissements...")
    enc = SourcesData.chercher_encaissements()

    print("\n📊 Recherche des rapports compagnies...")
    raps = SourcesData.chercher_rapports_compagnies()

    print("\n🖼️ Recherche des attestations...")
    att = SourcesData.chercher_attestations()

    print("\n" + "=" * 60)
