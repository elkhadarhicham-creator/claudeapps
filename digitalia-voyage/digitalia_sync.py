#!/usr/bin/env python3
"""Reprise des souscriptions du site vers Digitalia.

Usage :
  python digitalia_sync.py --site https://votre-site.ma --cle CLE [--tout] [--sortie souscriptions.json]

Par défaut, récupère seulement les souscriptions pas encore importées, les écrit dans un
fichier JSON (une fiche par souscription), puis confirme l'import au site.
--tout reprend tout l'historique (sans confirmer). À brancher sur l'import de Digitalia.
"""
import argparse
import json

import httpx


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--site", required=True)
    a.add_argument("--cle", required=True)
    a.add_argument("--tout", action="store_true")
    a.add_argument("--sortie", default="souscriptions.json")
    o = a.parse_args()
    base, h = o.site.rstrip("/"), {"X-Api-Key": o.cle}
    fiches, curseur = [], None
    while True:
        params = {"limite": 500, "non_importees": str(not o.tout).lower()}
        if curseur:
            params["depuis"] = curseur
        r = httpx.get(f"{base}/api/digitalia/souscriptions", params=params, headers=h, timeout=30)
        r.raise_for_status()
        page = r.json()
        fiches += page["souscriptions"]
        curseur = page["curseur"]
        if not page["suite"]:
            break
    with open(o.sortie, "w", encoding="utf-8") as f:
        json.dump(fiches, f, ensure_ascii=False, indent=2)
    print(f"{len(fiches)} souscription(s) écrite(s) dans {o.sortie}")
    if fiches and not o.tout:
        refs = [x["reference"] for x in fiches]
        for i in range(0, len(refs), 1000):
            httpx.post(f"{base}/api/digitalia/accuse", json={"references": refs[i:i + 1000]},
                       headers=h, timeout=30).raise_for_status()
        print("Import confirmé au site.")


if __name__ == "__main__":
    main()
