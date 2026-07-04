#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple - Vérifier que tout fonctionne avec les bons chemins
"""

from config_sources import SourcesData

print("\n" + "="*60)
print("TEST DE DÉCOUVERTE DE FICHIERS")
print("="*60 + "\n")

# Test 1: Encaissements
print("1️⃣  ENCAISSEMENTS")
print("-" * 60)
enc = SourcesData.chercher_encaissements()
if enc:
    print(f"✅ Encaissements trouvés: {enc.name}\n")
else:
    print("❌ Aucun fichier d'encaissements trouvé\n")

# Test 2: Compagnies
print("2️⃣  COMPAGNIES")
print("-" * 60)
rapports = SourcesData.chercher_rapports_compagnies()
if rapports:
    print(f"✅ {len(rapports)} compagnie(s) trouvée(s):")
    for nom, chemin in rapports.items():
        print(f"   • {nom}: {chemin.name}")
    print()
else:
    print("❌ Aucune compagnie trouvée\n")

# Test 3: Attestations réseau
print("3️⃣  ATTESTATIONS RÉSEAU")
print("-" * 60)
att = SourcesData.chercher_attestations()
if att:
    print(f"✅ {len(att)} attestation(s) trouvée(s)\n")
else:
    print("❌ Aucune attestation trouvée (chemin réseau peut ne pas être accessible)\n")

# Résumé
print("="*60)
print("RÉSUMÉ")
print("="*60)

if enc:
    print("✅ Encaissements: OK")
else:
    print("❌ Encaissements: Pas trouvé")

if rapports:
    print(f"✅ Compagnies: OK ({', '.join(rapports.keys())})")
else:
    print("❌ Compagnies: Pas trouvé")

if att:
    print("✅ Attestations: OK")
else:
    print("⚠️  Attestations: Non accessible (optionnel)")

print("\n" + "="*60)

input("Appuyez sur ENTRÉE pour fermer...")
