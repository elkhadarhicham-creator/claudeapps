#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic avancé - Recherche détaillée des fichiers
Teste tous les patterns de recherche et affiche exactement ce qui est trouvé
"""

import os
from pathlib import Path
from config_sources import SourcesData, GOOGLE_DRIVE_PATH, ATTESTATIONS_NETWORK_PATH

print("\n" + "="*80)
print("DIAGNOSTIC AVANCÉ - Recherche détaillée des fichiers")
print("="*80 + "\n")

# 1. Vérification de la connectivité
print("ÉTAPE 1 : VÉRIFICATION DES CHEMINS")
print("-" * 80)
SourcesData.verifier_connectivite(verbose=True)

# 2. Diagnostic des encaissements
print("\n" + "="*80)
print("ÉTAPE 2 : RECHERCHE DES ENCAISSEMENTS")
print("="*80)

print(f"\nChemin de recherche: {GOOGLE_DRIVE_PATH}\n")

patterns_enc = [
    "Etat des encaissements*.pdf",
    "Etat des encaissements*",
    "*encaissements*.pdf",
    "*encaissements*",
    "Etat*"
]

print("Patterns testés:")
for pattern in patterns_enc:
    try:
        found = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))
        found = [f for f in found if f.is_file() and "encaissements" in f.name.lower()]
        if found:
            print(f"✅ '{pattern}' -> {len(found)} fichier(s)")
            for f in found:
                size = f.stat().st_size / 1024
                print(f"   - {f.name} ({size:.1f} KB)")
        else:
            print(f"❌ '{pattern}' -> 0 fichiers")
    except Exception as e:
        print(f"❌ '{pattern}' -> ERREUR: {e}")

# 3. Diagnostic des rapports compagnies - avec affichage exhaustif
print("\n" + "="*80)
print("ÉTAPE 3 : RECHERCHE DES RAPPORTS COMPAGNIES")
print("="*80)

print(f"\nChemin de recherche: {GOOGLE_DRIVE_PATH}\n")

# Afficher d'abord TOUS les fichiers Excel
print("TOUS LES FICHIERS EXCEL ET CSV DANS LE DOSSIER:")
print("-" * 80)
try:
    all_files = sorted(Path(GOOGLE_DRIVE_PATH).glob("*"))
    excel_files = [f for f in all_files if f.is_file() and f.suffix.lower() in ['.xlsx', '.csv', '.xls']]

    if excel_files:
        for i, f in enumerate(excel_files, 1):
            print(f"{i}. {f.name}")
    else:
        print("❌ Aucun fichier Excel/CSV trouvé")
except Exception as e:
    print(f"Erreur: {e}")

# Maintenant tester les patterns pour chaque compagnie
print("\n" + "-" * 80)
print("PATTERNS DE RECHERCHE PAR COMPAGNIE:")
print("-" * 80 + "\n")

compagnies_config = {
    "MATU": ["MATU"],
    "SANLAM": ["SANLAM", "SANLAMÉ"],
    "WAFA": ["WAFA", "WAFA ASSURANCE"],
    "MAROC ASSISTANCE": ["MAROC ASSISTANCE", "MAROC ASSIST"]
}

for nom_cie, aliases in compagnies_config.items():
    print(f"\n🔍 {nom_cie}:")

    fichiers_trouves = []

    for alias in aliases:
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
                found = [f for f in found if f.is_file() and "RAPPORT" in f.name.upper() and alias.upper() in f.name.upper()]

                if found:
                    print(f"  ✅ Pattern '{pattern}' -> {len(found)} fichier(s)")
                    for f in found:
                        print(f"     - {f.name}")
                        fichiers_trouves.append(f)

            except Exception as e:
                print(f"  ❌ Pattern '{pattern}' -> ERREUR: {e}")

    if not fichiers_trouves:
        print(f"  ⚠️ Aucun fichier trouvé pour {nom_cie}")
    else:
        # Afficher le plus récent
        plus_recent = sorted(fichiers_trouves, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        print(f"  📌 Plus récent: {plus_recent.name}")

# 4. Test de la méthode chercher_rapports_compagnies
print("\n" + "="*80)
print("ÉTAPE 4 : TEST DES MÉTHODES DE RECHERCHE")
print("="*80 + "\n")

print("Test de SourcesData.chercher_rapports_compagnies()...")
rapports = SourcesData.chercher_rapports_compagnies(verbose=True)

if rapports:
    print(f"\n✅ {len(rapports)} compagnie(s) trouvée(s):")
    for nom_cie, chemin in rapports.items():
        print(f"   - {nom_cie}: {chemin.name}")
else:
    print("\n⚠️ Aucune compagnie trouvée")

# 5. Test des attestations réseau
print("\n" + "="*80)
print("ÉTAPE 5 : VÉRIFICATION DES ATTESTATIONS RÉSEAU")
print("="*80 + "\n")

print(f"Chemin de recherche: {ATTESTATIONS_NETWORK_PATH}\n")

if os.path.exists(ATTESTATIONS_NETWORK_PATH):
    print("✅ Chemin accessible!")
    try:
        attestations = SourcesData.chercher_attestations(verbose=True)
        if attestations:
            print(f"\n{len(attestations)} attestation(s) trouvée(s):")
            for i, (nom, chemin) in enumerate(list(attestations.items())[:10], 1):
                print(f"   {i}. {nom} -> {chemin.name}")
            if len(attestations) > 10:
                print(f"   ... et {len(attestations) - 10} autre(s)")
    except Exception as e:
        print(f"Erreur: {e}")
else:
    print("❌ Chemin NON accessible")
    print(f"   Essayé: {ATTESTATIONS_NETWORK_PATH}")
    print("\n   Tentatives alternatives:")

    chemins_alt = [
        r"\\KARIMA\images analisis\A 204570153",
        r"\\KARIMA\images analisis",
        r"\\KARIMA\images_analisis",
        r"\\KARIMA\A 204570153"
    ]

    for chemin in chemins_alt:
        if os.path.exists(chemin):
            print(f"   ✅ {chemin}")
        else:
            print(f"   ❌ {chemin}")

# 6. Résumé final
print("\n" + "="*80)
print("RÉSUMÉ FINAL")
print("="*80 + "\n")

if os.path.exists(GOOGLE_DRIVE_PATH):
    enc = SourcesData.chercher_encaissements()
    raps = SourcesData.chercher_rapports_compagnies()

    print("✅ Google Drive accessible")
    print(f"   - Encaissements: {'✅ Trouvé' if enc else '❌ Non trouvé'}")
    print(f"   - Compagnies trouvées: {len(raps)} ({', '.join(raps.keys()) if raps else 'aucune'})")
else:
    print("❌ Google Drive NON accessible")

if os.path.exists(ATTESTATIONS_NETWORK_PATH):
    att = SourcesData.chercher_attestations()
    print(f"✅ Attestations réseau: {len(att)} fichiers trouvés")
else:
    print("❌ Attestations réseau: Non accessible")

print("\n" + "="*80)
print("FIN DU DIAGNOSTIC AVANCÉ")
print("="*80 + "\n")

input("Appuyez sur ENTRÉE pour fermer...")
