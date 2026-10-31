#!/usr/bin/env python3
"""Robot « Site voyage » de Digitalia.

Tourne sur le PC du cabinet, à côté de Digitalia (dossier pont_analysis), comme le robot MATU.
À chaque passage :
  1. récupère sur le site les souscriptions nouvelles ou modifiées (payées, émises, annulées) ;
  2. les enregistre dans la base de Digitalia, table « site_souscriptions » (une ligne par souscription) ;
  3. télécharge le reçu, l'attestation de la compagnie et les copies des CIN / passeports
     (dossier « pieces_identite ») dans le dossier des documents ;
  4. appelle integration_digitalia.integrer(...) s'il existe (versement dans clients, contrats,
     encaissements : voir CONSIGNES_CLAUDE_PC.md) ;
  5. confirme l'import au site, qui efface alors les copies des pièces d'identité de son côté.
     Une souscription dont une copie n'a pas pu être téléchargée n'est pas confirmée : elle revient au passage suivant.

Aucune bibliothèque à installer : Python 3.9+ suffit. Ne touche jamais à Analysis.

Usage :
  python robot_site_voyage.py               un passage
  python robot_site_voyage.py --boucle 900  un passage toutes les 15 minutes
  python robot_site_voyage.py --reprise     reprend tout l'historique depuis le début

Réglages dans robot_site_voyage.ini (créé au premier lancement) ou variables d'environnement
SITE_VOYAGE_URL, SITE_VOYAGE_CLE, DIGITALIA_DB, DOSSIER_DOCUMENTS.
"""
from __future__ import annotations

import argparse
import configparser
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
INI = ICI / "robot_site_voyage.ini"

log = logging.getLogger("robot_site_voyage")

TABLE = """
CREATE TABLE IF NOT EXISTS site_souscriptions (
  reference TEXT PRIMARY KEY,
  statut TEXT NOT NULL,               -- payee | emise | annulee
  numero_police TEXT,
  produit TEXT, compagnie TEXT, branche TEXT,
  date_souscription TEXT, date_effet TEXT, date_echeance TEXT, date_emission TEXT,
  prime_ttc REAL,
  encaissement_mode TEXT, encaissement_montant REAL, encaissement_date TEXT,
  transaction_cmi TEXT, autorisation_cmi TEXT,
  telephone TEXT, email TEXT,
  souscripteur_nom TEXT, souscripteur_prenom TEXT, souscripteur_cin TEXT, souscripteur_passeport TEXT,
  souscripteur_naissance TEXT, souscripteur_adresse TEXT,
  assures_json TEXT NOT NULL,         -- liste complète des assurés
  fiche_json TEXT NOT NULL,           -- fiche brute reçue du site
  fichier_recu TEXT, fichier_attestation TEXT,
  fichiers_pieces TEXT,               -- copies CIN / passeport (liste JSON de chemins)
  mis_a_jour_site TEXT,
  version_site INTEGER,              -- augmente à chaque modification sur le site
  recu_le TEXT NOT NULL,              -- 1re réception par le robot
  maj_le TEXT NOT NULL,               -- dernière mise à jour par le robot
  integre_le TEXT,                    -- versée dans les tables de Digitalia (clients, contrats…)
  integration_erreur TEXT
);
CREATE TABLE IF NOT EXISTS site_robot_etat (cle TEXT PRIMARY KEY, valeur TEXT);
"""


def reglages(args) -> dict:
    cp = configparser.ConfigParser()
    if not INI.exists():
        cp["site"] = {"url": "https://VOTRE-SITE", "cle_api": "", "intervalle_secondes": "900"}
        cp["digitalia"] = {"base": str(ICI / "digitalia.db"), "dossier_documents": str(ICI / "documents_site_voyage")}
        with open(INI, "w", encoding="utf-8") as f:
            cp.write(f)
        log.warning("Fichier %s créé : complétez l'adresse du site, la clé API et le chemin de la base.", INI)
    cp.read(INI, encoding="utf-8")
    r = {
        "url": os.environ.get("SITE_VOYAGE_URL") or cp.get("site", "url", fallback=""),
        "cle": os.environ.get("SITE_VOYAGE_CLE") or cp.get("site", "cle_api", fallback=""),
        "base": os.environ.get("DIGITALIA_DB") or cp.get("digitalia", "base", fallback=""),
        "docs": os.environ.get("DOSSIER_DOCUMENTS") or cp.get("digitalia", "dossier_documents", fallback=""),
    }
    for k, v in (("url", args.site), ("cle", args.cle), ("base", args.base), ("docs", args.documents)):
        if v:
            r[k] = v
    r["url"] = r["url"].rstrip("/")
    manque = [k for k in ("url", "cle", "base", "docs") if not r[k] or "VOTRE-SITE" in r[k]]
    if manque:
        raise SystemExit(f"Réglages manquants : {', '.join(manque)} (fichier {INI})")
    return r


class Site:
    def __init__(self, url: str, cle: str):
        self.url, self.cle = url, cle

    def _req(self, chemin: str, data: bytes | None = None, ctype: str | None = None):
        req = urllib.request.Request(self.url + chemin, data=data, headers={"X-Api-Key": self.cle, "User-Agent": "robot-digitalia"})
        if ctype:
            req.add_header("Content-Type", ctype)
        return urllib.request.urlopen(req, timeout=60)

    def json(self, chemin: str, params: dict | None = None, corps: dict | None = None):
        if params:
            chemin += "?" + urllib.parse.urlencode(params)
        data = json.dumps(corps).encode() if corps is not None else None
        with self._req(chemin, data, "application/json" if data else None) as r:
            return json.loads(r.read().decode("utf-8"))

    def fichier(self, chemin: str, dest: Path, images: bool = False) -> bool:
        """Télécharge un PDF (ou, avec images=True, aussi une photo JPEG / PNG / WebP / GIF)."""
        try:
            with self._req(chemin) as r:
                contenu = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise
        signatures = (b"%PDF",) + ((b"\xff\xd8\xff", b"\x89PNG", b"RIFF", b"GIF8") if images else ())
        if not contenu.startswith(signatures):
            return False
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(contenu)
        tmp.replace(dest)
        return True


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def nom_fichier(texte: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in texte)


def enregistrer(conn: sqlite3.Connection, f: dict, docs: dict) -> bool:
    """Insère ou met à jour la souscription. Renvoie True si elle est nouvelle ou a changé."""
    sous = next((a for a in f["assures"] if a.get("lien") == "Souscripteur"), f["assures"][0] if f["assures"] else {})
    enc = f.get("encaissement") or {}
    ligne = {
        "reference": f["reference"], "statut": f.get("statut"), "numero_police": f.get("numero_police"),
        "produit": f.get("produit"), "compagnie": f.get("compagnie"), "branche": f.get("branche"),
        "date_souscription": f.get("date_souscription"), "date_effet": f.get("date_effet"),
        "date_echeance": f.get("date_echeance"), "date_emission": f.get("date_emission"),
        "prime_ttc": f.get("prime_ttc"),
        "encaissement_mode": enc.get("mode"), "encaissement_montant": enc.get("montant"), "encaissement_date": enc.get("date"),
        "transaction_cmi": enc.get("transaction"), "autorisation_cmi": enc.get("autorisation"),
        "telephone": (f.get("souscripteur") or {}).get("telephone_whatsapp"), "email": (f.get("souscripteur") or {}).get("email"),
        "souscripteur_nom": sous.get("nom"), "souscripteur_prenom": sous.get("prenom"), "souscripteur_cin": sous.get("cin"),
        "souscripteur_passeport": sous.get("passeport"), "souscripteur_naissance": sous.get("naissance"),
        "souscripteur_adresse": sous.get("adresse"),
        "assures_json": json.dumps(f["assures"], ensure_ascii=False), "fiche_json": json.dumps(f, ensure_ascii=False),
        "fichier_recu": docs.get("recu"), "fichier_attestation": docs.get("attestation"),
        "fichiers_pieces": json.dumps(docs["pieces"], ensure_ascii=False) if docs.get("pieces") else None,
        "mis_a_jour_site": f.get("mis_a_jour_le"), "version_site": f.get("version"),
    }
    avant = conn.execute("SELECT version_site, statut, fichier_attestation FROM site_souscriptions WHERE reference=?",
                         (f["reference"],)).fetchone()
    t = maintenant()
    if avant is None:
        ligne.update(recu_le=t, maj_le=t)
        cols = ",".join(ligne)
        conn.execute(f"INSERT INTO site_souscriptions ({cols}) VALUES ({','.join('?' * len(ligne))})", tuple(ligne.values()))
        return True
    change = (avant[0], avant[1], avant[2]) != (ligne["version_site"], ligne["statut"], ligne["fichier_attestation"])
    if change:
        ligne["maj_le"] = t
        ligne["integre_le"] = None  # à reverser dans Digitalia (ex. n° de police arrivé)
    if not ligne["fichiers_pieces"]:  # copies déjà reçues puis effacées du site : on garde les chemins
        del ligne["fichiers_pieces"]
    sets = ",".join(f"{k}=?" for k in ligne)
    conn.execute(f"UPDATE site_souscriptions SET {sets} WHERE reference=?", (*ligne.values(), f["reference"]))
    return change


def charger_integration():
    """Module écrit pour Digitalia (voir CONSIGNES_CLAUDE_PC.md) ; facultatif."""
    sys.path.insert(0, str(ICI))
    try:
        import integration_digitalia  # noqa: PLC0415
        return integration_digitalia.integrer
    except ImportError:
        return None


def passage(r: dict, reprise: bool = False) -> dict:
    site = Site(r["url"], r["cle"])
    docs_dir = Path(r["docs"])
    docs_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(r["base"], timeout=30)
    conn.executescript(TABLE)
    try:  # bases créées avant l'ajout des copies de pièces
        conn.execute("ALTER TABLE site_souscriptions ADD COLUMN fichiers_pieces TEXT")
    except sqlite3.OperationalError:
        pass
    integrer = charger_integration()
    cur = None if reprise else (conn.execute("SELECT valeur FROM site_robot_etat WHERE cle='curseur'").fetchone() or [None])[0]
    bilan = {"recues": 0, "nouvelles_ou_modifiees": 0, "integrees": 0, "erreurs": 0}
    refs = []

    def traiter(f):
        bilan["recues"] += 1
        ref = nom_fichier(f["reference"])
        fichiers = {}
        d = f.get("documents") or {}
        if d.get("recu"):
            dest = docs_dir / f"{ref}-recu.pdf"
            if dest.exists() or site.fichier(d["recu"], dest):
                fichiers["recu"] = str(dest)
        if d.get("attestation"):
            base_nom = nom_fichier(f.get("numero_police") or f["reference"])
            dest = docs_dir / f"{base_nom}-attestation.pdf"
            if site.fichier(d["attestation"], dest):
                fichiers["attestation"] = str(dest)
        complet = True
        if d.get("pieces"):
            pdir = docs_dir / "pieces_identite"
            pdir.mkdir(exist_ok=True)
            fichiers["pieces"] = []
            for p in d["pieces"]:
                dest = pdir / nom_fichier(p["nom"])
                if dest.exists() or site.fichier(p["url"], dest, images=True):
                    fichiers["pieces"].append(str(dest))
                else:
                    complet = False
        with conn:
            if enregistrer(conn, f, fichiers):
                bilan["nouvelles_ou_modifiees"] += 1
        if complet:
            refs.append(f["reference"])
        else:
            log.warning("%s : copie de pièce non téléchargée, import non confirmé (nouvel essai au prochain passage)", ref)

    while True:
        params = {"limite": 200}
        if cur:
            params["depuis"] = cur
        page = site.json("/api/digitalia/souscriptions", params)
        for f in page["souscriptions"]:
            traiter(f)
        cur = page["curseur"]
        with conn:  # curseur sauvé page par page : une coupure ne fait rien perdre
            conn.execute("INSERT OR REPLACE INTO site_robot_etat(cle, valeur) VALUES ('curseur', ?)", (cur,))
            conn.execute("INSERT OR REPLACE INTO site_robot_etat(cle, valeur) VALUES ('dernier_passage', ?)", (maintenant(),))
        if not page["suite"]:
            break

    # Souscriptions pas encore confirmées (ex. copie de pièce non téléchargée au passage précédent)
    if not reprise:
        deja = set(refs)
        for f in site.json("/api/digitalia/souscriptions", {"non_importees": "true", "limite": 200})["souscriptions"]:
            if f["reference"] not in deja:
                traiter(f)

    if integrer:
        a_faire = conn.execute("SELECT reference FROM site_souscriptions WHERE integre_le IS NULL ORDER BY recu_le").fetchall()
        for (ref,) in a_faire:
            ligne = conn.execute("SELECT * FROM site_souscriptions WHERE reference=?", (ref,)).fetchone()
            noms = [c[0] for c in conn.execute("SELECT * FROM site_souscriptions LIMIT 0").description]
            try:
                with conn:  # tout ou rien pour chaque souscription
                    fait = integrer(conn, dict(zip(noms, ligne)))
                    if fait is not False:  # False = « pas encore » (ex. n° de police pas encore émis)
                        conn.execute("UPDATE site_souscriptions SET integre_le=?, integration_erreur=NULL WHERE reference=?",
                                     (maintenant(), ref))
                if fait is not False:
                    bilan["integrees"] += 1
            except Exception as e:  # noqa: BLE001 - on note l'erreur et on passe à la suivante
                bilan["erreurs"] += 1
                log.exception("Intégration %s impossible", ref)
                with conn:
                    conn.execute("UPDATE site_souscriptions SET integration_erreur=? WHERE reference=?", (str(e)[:500], ref))

    for i in range(0, len(refs), 500):
        site.json("/api/digitalia/accuse", corps={"references": refs[i:i + 500]})
    conn.close()
    return bilan


def main():
    a = argparse.ArgumentParser(description="Robot Site voyage → Digitalia")
    a.add_argument("--boucle", type=int, metavar="SECONDES", help="relancer toutes les N secondes (900 = 15 min)")
    a.add_argument("--reprise", action="store_true", help="reprendre tout l'historique du site")
    a.add_argument("--site")
    a.add_argument("--cle")
    a.add_argument("--base")
    a.add_argument("--documents")
    args = a.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(ICI / "robot_site_voyage.log", encoding="utf-8")])
    r = reglages(args)
    premiere = True
    while True:
        try:
            b = passage(r, reprise=args.reprise and premiere)
            log.info("Passage terminé : %s", b)
        except (urllib.error.URLError, OSError, sqlite3.Error, ValueError) as e:
            log.error("Passage interrompu : %s (nouvel essai au prochain passage)", e)
            if not args.boucle:
                sys.exit(1)
        premiere = False
        if not args.boucle:
            break
        time.sleep(args.boucle)


if __name__ == "__main__":
    main()
