#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic ciblé : pourquoi le RAPPORT MATU du jour n'est-il pas chargé ?
Liste les fichiers MATU du Drive, teste la recherche par date et la lecture.
"""
import os
from pathlib import Path

print("\n" + "="*78)
print("  DIAGNOSTIC RAPPORT MATU")
print("="*78 + "\n")

try:
    from config_sources import SourcesData, GOOGLE_DRIVE_PATH
except Exception as e:
    print(f"❌ Impossible d'importer config_sources : {e}")
    input("\nENTRÉE pour fermer..."); raise SystemExit

# Date à tester
date_test = input("Quelle date contrôlez-vous ? (JJ/MM/AAAA) [défaut 04/07/2026] : ").strip() or "04/07/2026"
date_str = date_test.replace("/", ".").replace("-", ".")
print(f"\nDate testée : {date_test}  (recherche : {date_str})\n")

# 1) Lister TOUS les fichiers contenant MATU
print("-"*78)
print("1) FICHIERS CONTENANT 'MATU' DANS G:\\Mon Drive :")
print("-"*78)
if not os.path.exists(GOOGLE_DRIVE_PATH):
    print(f"❌ {GOOGLE_DRIVE_PATH} inaccessible !")
else:
    trouves = [f for f in Path(GOOGLE_DRIVE_PATH).glob("*") if f.is_file() and "MATU" in f.name.upper()]
    if not trouves:
        print("❌ AUCUN fichier contenant 'MATU' trouvé !")
    for f in sorted(trouves):
        print(f"   • «{f.name}»   ({f.stat().st_size//1024} Ko)")

# 2) Variantes de date générées
print("\n" + "-"*78)
print("2) VARIANTES DE DATE RECHERCHÉES :")
print("-"*78)
variantes = SourcesData.variantes_date(date_str)
print("  ", ", ".join(sorted(variantes)))

# 3) Est-ce qu'un fichier MATU correspond à la date ?
print("\n" + "-"*78)
print("3) CORRESPONDANCE FICHIER MATU <-> DATE :")
print("-"*78)
if os.path.exists(GOOGLE_DRIVE_PATH):
    for f in sorted(trouves):
        match = any(v in f.name for v in variantes)
        print(f"   {'✅ CORRESPOND' if match else '❌ ne correspond pas'} : «{f.name}»")

# 4) Test complet de la recherche + lecture
print("\n" + "-"*78)
print("4) TEST OFFICIEL (comme le programme principal) :")
print("-"*78)
rapports = SourcesData.chercher_rapports_compagnies(date_str, verbose=True)
if "MATU" in rapports:
    chemin = rapports["MATU"]
    print(f"\n✅ MATU sélectionné : {chemin.name}")
    try:
        from rapprochement_auto_FIXED import lire_rapport_compagnie
        df = lire_rapport_compagnie(str(chemin), "MATU")
        print(f"✅ Lecture réussie : {len(df)} ligne(s)")
        if not df.empty:
            print("   Clients :", ", ".join(str(c)[:15] for c in df['client'].head(6)))
    except Exception as e:
        print(f"❌ Erreur de lecture : {e}")
else:
    print("\n❌ MATU N'A PAS ÉTÉ SÉLECTIONNÉ pour cette date.")
    print("   => C'est la cause du problème. Voir la section 3 ci-dessus.")

print("\n" + "="*78)
input("Copiez cet écran et envoyez-le. ENTRÉE pour fermer...")
