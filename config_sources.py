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
# Premier essai: dossier principal
ATTESTATIONS_NETWORK_PATH = r"\\KARIMA\images analisis"
# Alternative si nécessaire: ATTESTATIONS_NETWORK_PATH = r"\\KARIMA\images analisis\A 204570153"

# ================================================================================
# SOURCES DE FICHIERS
# ================================================================================

class SourcesData:
    """Gestionnaire des sources de données."""

    @staticmethod
    def chercher_encaissements(date_str=None):
        """
        Cherche le fichier PDF d'encaissements.
        Format: "Etat des encaissements01.07.2026" (avec ou sans .pdf)

        Args:
            date_str: Date au format DD.MM.YYYY (optionnel)

        Returns:
            Path: Chemin du fichier trouvé, ou None
        """
        if not os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"⚠️ ERREUR: {GOOGLE_DRIVE_PATH} n'existe pas")
            return None

        # Chercher avec TOUS les patterns possibles (avec et sans extension)
        patterns = [
            "Etat des encaissements*.pdf",
            "Etat des encaissements*",
            "*encaissements*.pdf",
            "*encaissements*"
        ]
        fichiers = []

        for pattern in patterns:
            found = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))
            # Filtrer: fichier doit contenir "encaissements" (ignore les dossiers)
            found = [f for f in found if f.is_file() and "encaissements" in f.name.lower()]
            fichiers.extend(found)

        # Supprimer les doublons
        fichiers = list(set(fichiers))

        if not fichiers:
            print(f"❌ Aucun fichier d'encaissements trouvé dans {GOOGLE_DRIVE_PATH}")
            print(f"   Cherchait patterns: Etat des encaissements*")
            return None

        # Si date spécifiée, chercher ce jour exact
        if date_str:
            date_search = date_str.replace("/", ".").replace("-", ".")
            for f in fichiers:
                if date_search in f.name:
                    print(f"✅ Encaissements trouvés: {f.name}")
                    return f

        # Sinon retourner le plus récent
        fichier = sorted(fichiers, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        print(f"✅ Encaissements trouvés: {fichier.name}")
        return fichier

    @staticmethod
    def chercher_rapports_compagnies(date_str=None, verbose=False):
        """
        Cherche les fichiers des rapports des compagnies.
        Format: "RAPPORT MATU 01-07-2026" (avec ou sans .xlsx/.csv)

        Compagnies attendues: MATU, SANLAM, WAFA, MAROC ASSISTANCE

        Args:
            date_str: Date au format DD-MM-YYYY (optionnel)
            verbose: Afficher les détails de la recherche

        Returns:
            Dict: {nom_compagnie: Path}
        """
        if not os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"⚠️ ERREUR: {GOOGLE_DRIVE_PATH} n'existe pas")
            return {}

        # Mapping des noms de compagnies avec leurs alias possibles
        compagnies_map = {
            "MATU": ["MATU"],
            "SANLAM": ["SANLAM", "SANLAMÉ"],
            "WAFA": ["WAFA", "WAFA ASSURANCE"],
            "MAROC ASSISTANCE": ["MAROC ASSISTANCE", "MAROC ASSIST"]
        }

        rapports = {}

        for nom_cie, aliases in compagnies_map.items():
            fichiers = []

            # Essayer chaque alias
            for alias in aliases:
                # Chercher avec TOUS les patterns (avec et sans extension)
                patterns = [
                    f"RAPPORT {alias} *.xlsx",
                    f"RAPPORT {alias} *.csv",
                    f"RAPPORT {alias}*",
                    f"*RAPPORT {alias}*",
                    f"*{alias}*.xlsx",
                    f"*{alias}*.csv",
                    f"*{alias}*"
                ]

                for pattern in patterns:
                    try:
                        found = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))
                        # Filtrer: doit être un fichier et contenir "RAPPORT" et le nom de la cie
                        found = [f for f in found if f.is_file() and "RAPPORT" in f.name.upper() and alias.upper() in f.name.upper()]
                        fichiers.extend(found)

                        if verbose and found:
                            print(f"  Pattern '{pattern}' trouvé {len(found)} fichier(s)")
                    except Exception as e:
                        if verbose:
                            print(f"  Erreur pattern '{pattern}': {e}")

            # Supprimer les doublons
            fichiers = list(set(fichiers))

            if not fichiers:
                if verbose:
                    print(f"⚠️ Aucun rapport trouvé pour {nom_cie}")
                continue

            # Si date spécifiée, chercher ce jour exact
            if date_str:
                date_search = date_str.replace("-", ".").replace("/", ".")
                for f in fichiers:
                    if date_search in f.name or date_str in f.name:
                        rapports[nom_cie] = f
                        print(f"✅ Rapport {nom_cie} trouvé: {f.name}")
                        break

            # Si pas trouvé avec la date, prendre le plus récent
            if nom_cie not in rapports and fichiers:
                f = sorted(fichiers, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                rapports[nom_cie] = f
                print(f"✅ Rapport {nom_cie} trouvé: {f.name}")

        return rapports

    @staticmethod
    def chercher_attestations(numero_attestation=None, verbose=False):
        """
        Cherche les fichiers des attestations.
        Format: [numero].pdf (ex: 001.pdf, 002.jpg)

        Args:
            numero_attestation: Numéro spécifique (optionnel)
            verbose: Afficher les détails

        Returns:
            Dict or Path: Tous les fichiers, ou fichier spécifique
        """
        attestations = {}

        # Vérifier le chemin réseau avec plus de détails
        if not os.path.exists(ATTESTATIONS_NETWORK_PATH):
            if verbose:
                print(f"⚠️ Chemin NON accessible: {ATTESTATIONS_NETWORK_PATH}")
                print("  Tentatives de diagnostic:")
                print("  1. Vérifiez que le partage réseau KARIMA est accessible")
                print("  2. Vérifiez les permissions du dossier A 204570153")
                print("  3. Essayez d'accéder à \\\\KARIMA\\images analisis dans l'Explorateur")

            # Essayer des chemins alternatifs
            chemins_alt = [
                r"\\KARIMA\images analisis\A 204570153",
                r"\\KARIMA\images analisis",
                r"\\KARIMA\images_analisis",
                r"\\KARIMA\A 204570153"
            ]

            for chemin_alt in chemins_alt:
                if os.path.exists(chemin_alt):
                    if verbose:
                        print(f"  ✅ Chemin alternatif trouvé: {chemin_alt}")
                    ATTESTATIONS_NETWORK_PATH = chemin_alt
                    break
            else:
                if verbose:
                    print(f"  ❌ Aucun chemin réseau n'est accessible")
                return {}

        # Lister tous les fichiers (PDF, JPG, PNG, etc.)
        try:
            extensions = ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tif', '*.tiff', '*.PDF', '*.JPG', '*.JPEG', '*.PNG']

            for ext in extensions:
                try:
                    fichiers = list(Path(ATTESTATIONS_NETWORK_PATH).glob(ext))
                    for f in fichiers:
                        # Extraire le numéro du nom du fichier
                        nom_base = f.stem.lower()
                        attestations[nom_base] = f
                except Exception as e:
                    if verbose:
                        print(f"  Erreur lors de la lecture de {ext}: {e}")

            if attestations:
                print(f"✅ {len(attestations)} attestation(s) trouvée(s)")
            elif verbose:
                print(f"⚠️ Aucune attestation trouvée dans {ATTESTATIONS_NETWORK_PATH}")

        except Exception as e:
            if verbose:
                print(f"❌ Erreur lors de l'accès au dossier attestations: {e}")
            return {}

        if numero_attestation:
            numero_norm = str(numero_attestation).lower().zfill(3)
            return attestations.get(numero_norm)

        return attestations

    @staticmethod
    def verifier_connectivite(verbose=False):
        """Vérifie que tous les chemins sont accessibles."""
        print("\n📁 Vérification des chemins...")

        google_ok = False
        reseau_ok = False

        # Vérifier Google Drive
        if os.path.exists(GOOGLE_DRIVE_PATH):
            print(f"✅ Google Drive accessible: {GOOGLE_DRIVE_PATH}")
            google_ok = True
            if verbose:
                try:
                    files = list(Path(GOOGLE_DRIVE_PATH).glob("*"))
                    print(f"   {len(files)} fichiers trouvés")
                except Exception as e:
                    print(f"   ⚠️ Erreur lors de la lecture: {e}")
        else:
            print(f"❌ Google Drive NON accessible: {GOOGLE_DRIVE_PATH}")

        # Vérifier partage réseau
        if os.path.exists(ATTESTATIONS_NETWORK_PATH):
            print(f"✅ Partage réseau accessible: {ATTESTATIONS_NETWORK_PATH}")
            reseau_ok = True
            if verbose:
                try:
                    files = list(Path(ATTESTATIONS_NETWORK_PATH).glob("*"))
                    print(f"   {len(files)} fichiers trouvés")
                except Exception as e:
                    print(f"   ⚠️ Erreur lors de la lecture: {e}")
        else:
            print(f"❌ Partage réseau NON accessible: {ATTESTATIONS_NETWORK_PATH}")
            if verbose:
                print("   Conseil: Essayez d'accéder à \\\\KARIMA\\images analisis dans l'Explorateur Windows")

        print()
        return google_ok  # Au moins Google Drive est nécessaire


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
