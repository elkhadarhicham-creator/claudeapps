#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration des sources de fichiers pour le rapprochement automatique.
Gère les chemins locaux et réseau.
"""

import os
import re
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
    def variantes_date(date_str):
        """
        Génère toutes les écritures possibles d'une date.
        '29.06.2026' -> {'29.06.2026', '29-06-2026', '29/06/2026',
                         '29.06.26', '29-06-26', '29/06/26'}
        """
        if not date_str:
            return set()
        base = str(date_str).replace("/", ".").replace("-", ".")
        variantes = {base, base.replace(".", "-"), base.replace(".", "/")}
        parts = base.split(".")
        if len(parts) == 3 and len(parts[2]) == 4:
            courte = f"{parts[0]}.{parts[1]}.{parts[2][2:]}"
            variantes.update({courte, courte.replace(".", "-"), courte.replace(".", "/")})
        return variantes

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

        # Si date spécifiée, chercher ce jour exact (tous formats: 29.06.2026, 29-06-2026...)
        if date_str:
            variantes = SourcesData.variantes_date(date_str)
            for f in fichiers:
                if any(v in f.name for v in variantes):
                    print(f"✅ Encaissements trouvés: {f.name}")
                    return f
            print(f"⚠️ Pas d'encaissements daté du {date_str}, utilisation du plus récent")

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

            # Si date spécifiée : chercher UNIQUEMENT ce jour exact.
            # Pas de rapport à cette date = pas de production ce jour-là -> on ne charge rien
            # (ne JAMAIS prendre un autre jour, ça fausserait le rapprochement).
            if date_str:
                variantes = SourcesData.variantes_date(date_str)
                for f in fichiers:
                    if any(v in f.name for v in variantes):
                        rapports[nom_cie] = f
                        print(f"✅ Rapport {nom_cie} trouvé: {f.name}")
                        break
                if nom_cie not in rapports:
                    print(f"ℹ️ Pas de rapport {nom_cie} daté du {date_str} → pas de production {nom_cie} ce jour-là.")
            else:
                # Aucune date demandée : prendre le plus récent
                f = sorted(fichiers, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                rapports[nom_cie] = f
                print(f"✅ Rapport {nom_cie} trouvé: {f.name}")

        return rapports

    @staticmethod
    def normaliser_numero(valeur):
        """
        Normalise un numéro d'attestation pour la comparaison.
        'A 204570153' -> 'A204570153' (majuscules, sans espaces ni tirets)
        """
        if valeur is None:
            return ""
        return re.sub(r"[^A-Z0-9]", "", str(valeur).upper())

    @staticmethod
    def chercher_attestations(numero_attestation=None, verbose=False):
        """
        Cherche les attestations scannées sur le réseau.
        Les noms peuvent contenir des espaces: 'A 204570153.pdf' ou dossier 'A 204570153'.
        La comparaison ignore les espaces et la casse.

        Args:
            numero_attestation: Numéro spécifique (optionnel)
            verbose: Afficher les détails

        Returns:
            Dict {numero_normalise: Path} ou Path si numero_attestation fourni
        """
        attestations = {}

        # Trouver un chemin réseau accessible
        chemins_possibles = [
            ATTESTATIONS_NETWORK_PATH,
            r"\\KARIMA\images analisis",
            r"\\KARIMA\images_analisis",
        ]

        chemin = None
        for c in chemins_possibles:
            if os.path.exists(c):
                chemin = c
                break

        if chemin is None:
            if verbose:
                print(f"⚠️ Chemin NON accessible: {ATTESTATIONS_NETWORK_PATH}")
                print("  1. Vérifiez que le partage réseau KARIMA est accessible")
                print("  2. Essayez d'ouvrir \\\\KARIMA\\images analisis dans l'Explorateur Windows")
            return {}

        # Parcourir tous les éléments (fichiers ET dossiers)
        # Chaque attestation peut être un fichier 'A 204570153.pdf' ou un dossier 'A 204570153'
        try:
            with os.scandir(chemin) as it:
                for entry in it:
                    nom = entry.name
                    if entry.is_file():
                        nom = os.path.splitext(nom)[0]
                    cle = SourcesData.normaliser_numero(nom)
                    if cle:
                        attestations[cle] = Path(entry.path)

            if attestations:
                print(f"✅ {len(attestations)} attestation(s) trouvée(s) sur le réseau")
            elif verbose:
                print(f"⚠️ Aucune attestation trouvée dans {chemin}")

        except Exception as e:
            print(f"❌ Erreur lors de l'accès au dossier attestations: {e}")
            return {}

        if numero_attestation:
            return attestations.get(SourcesData.normaliser_numero(numero_attestation))

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
