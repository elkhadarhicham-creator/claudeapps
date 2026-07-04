#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic - Liste tous les fichiers et vérifie les patterns de recherche
"""

import os
from pathlib import Path

GOOGLE_DRIVE_PATH = r"G:\Mon Drive"

print("\n" + "="*80)
print("DIAGNOSTIC DES FICHIERS - G:\\Mon Drive\\")
print("="*80 + "\n")

# Vérifier si le chemin existe
if not os.path.exists(GOOGLE_DRIVE_PATH):
    print(f"❌ ERREUR: {GOOGLE_DRIVE_PATH} n'existe pas!")
    print("\nVérifiez que:")
    print("  1. Google Drive est mappé sur G:\\")
    print("  2. Le chemin est correct")
    exit(1)

print(f"✅ Chemin accessible: {GOOGLE_DRIVE_PATH}\n")

# Lister TOUS les fichiers
print("-" * 80)
print("TOUS LES FICHIERS:")
print("-" * 80)

all_files = sorted(Path(GOOGLE_DRIVE_PATH).glob("*"))

if not all_files:
    print("❌ Aucun fichier trouvé!")
    exit(1)

fichiers_pdf = []
fichiers_xlsx = []
fichiers_csv = []
autres = []

for i, f in enumerate(all_files, 1):
    if f.is_file():
        ext = f.suffix.lower()
        nom = f.name
        size = f.stat().st_size / 1024  # KB

        print(f"{i:2}. {nom} ({size:.1f} KB)")

        if ext == ".pdf":
            fichiers_pdf.append(f)
        elif ext in [".xlsx", ".xls"]:
            fichiers_xlsx.append(f)
        elif ext == ".csv":
            fichiers_csv.append(f)
        else:
            autres.append(f)

print("\n" + "-" * 80)
print("RÉSUMÉ PAR TYPE:")
print("-" * 80)
print(f"📄 PDFs: {len(fichiers_pdf)}")
print(f"📊 Excel: {len(fichiers_xlsx)}")
print(f"📋 CSV: {len(fichiers_csv)}")
print(f"❓ Autres: {len(autres)}")

# Chercher les encaissements
print("\n" + "="*80)
print("RECHERCHE: ENCAISSEMENTS")
print("="*80)

patterns_enc = ["*encaissements*.pdf", "*encaissements*", "Etat*"]
for pattern in patterns_enc:
    found = list(Path(GOOGLE_DRIVE_PATH).glob(pattern))
    found = [f for f in found if f.is_file() and "encaissements" in f.name.lower()]
    if found:
        print(f"\n✅ Pattern '{pattern}' trouve {len(found)} fichier(s):")
        for f in found:
            print(f"   - {f.name}")
    else:
        print(f"\n❌ Pattern '{pattern}' ne trouve rien")

# Chercher les rapports
print("\n" + "="*80)
print("RECHERCHE: RAPPORTS COMPAGNIES")
print("="*80)

compagnies = ["MATU", "SANLAM", "WAFA", "MAROC ASSISTANCE"]

for cie in compagnies:
    print(f"\n🔍 {cie}:")

    patterns = [
        f"RAPPORT {cie} *",
        f"*{cie}*"
    ]

    found = []
    for pattern in patterns:
        found.extend(Path(GOOGLE_DRIVE_PATH).glob(pattern))

    found = [f for f in found if f.is_file() and "RAPPORT" in f.name.upper() and cie.upper() in f.name.upper()]
    found = list(set(found))  # Supprimer doublons

    if found:
        print(f"  ✅ Trouvé {len(found)} fichier(s):")
        for f in found:
            print(f"     - {f.name}")
    else:
        print(f"  ❌ Aucun fichier trouvé")

# Chercher les attestations
print("\n" + "="*80)
print("RECHERCHE: ATTESTATIONS (réseau)")
print("="*80)

ATTESTATIONS_PATH = r"\\KARIMA\images analisis\A 204570153"

if os.path.exists(ATTESTATIONS_PATH):
    print(f"\n✅ Chemin accessible: {ATTESTATIONS_PATH}")

    att_files = list(Path(ATTESTATIONS_PATH).glob("*"))
    att_files = [f for f in att_files if f.is_file()]

    if att_files:
        print(f"\n📸 {len(att_files)} attestation(s) trouvée(s):")
        for f in sorted(att_files)[:10]:  # Afficher les 10 premières
            print(f"   - {f.name}")
        if len(att_files) > 10:
            print(f"   ... et {len(att_files) - 10} autre(s)")
    else:
        print("\n❌ Aucune attestation trouvée")
else:
    print(f"\n❌ Chemin NON accessible: {ATTESTATIONS_PATH}")
    print("   Vérifiez que le partage réseau KARIMA est accessible")

print("\n" + "="*80)
print("FIN DU DIAGNOSTIC")
print("="*80 + "\n")
