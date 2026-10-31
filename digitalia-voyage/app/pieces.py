"""Copies des pièces d'identité (CIN, passeport) jointes à la souscription.

Parcours d'une copie :
  1. le client photographie ou joint sa pièce : elle est rangée dans pieces_tmp/ sous un identifiant aléatoire ;
  2. à la création de la souscription, les copies citées sont déplacées dans pieces/<référence>/ ;
  3. Digitalia les télécharge avec la fiche (API protégée par clé) ;
  4. dès que Digitalia accuse réception, elles sont effacées du site : le dossier client vit dans Digitalia.
Les copies jamais rattachées sont effacées après 24 h ; celles d'une souscription jamais payée, après 30 jours.
"""
import logging
import re
import secrets
import shutil
import time
from pathlib import Path

from . import config

log = logging.getLogger("digitalia.pieces")

TMP = config.DATA_DIR / "pieces_tmp"
DOSSIER = config.DATA_DIR / "pieces"
TMP.mkdir(exist_ok=True)
DOSSIER.mkdir(exist_ok=True)

ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,40}$")
NOM_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "application/pdf": "pdf"}
MAX_PAR_ASSURE = 4


def deposer(data: bytes, media: str) -> str:
    """Range une copie en attente et renvoie son identifiant."""
    purger_tmp()
    pid = secrets.token_urlsafe(18)
    (TMP / f"{pid}.{EXT.get(media, 'jpg')}").write_bytes(data)
    return pid


def _tmp(pid: str) -> Path | None:
    if not ID_RE.match(pid):
        return None
    return next(TMP.glob(f"{pid}.*"), None)


def rattacher(ref: str, assures: list[dict]) -> None:
    """Déplace les copies citées par chaque assuré dans le dossier de la souscription.
    Remplace, dans chaque assuré, la liste d'identifiants par la liste des noms de fichiers."""
    for i, a in enumerate(assures, 1):
        noms = []
        for k, pid in enumerate(a.get("pieces") or [], 1):
            src = _tmp(pid)
            if not src:
                log.warning("%s : copie %s introuvable ou expirée", ref, pid[:6])
                continue
            dest_dir = DOSSIER / ref
            dest_dir.mkdir(exist_ok=True)
            lien = re.sub(r"[^a-z]", "", a.get("lien", "").lower())[:12] or "assure"
            nom = f"{ref}-{i}-{lien}-{k}{src.suffix}"
            shutil.move(str(src), dest_dir / nom)
            noms.append(nom)
        a["pieces"] = noms


def chemin(ref: str, nom: str) -> Path | None:
    if not NOM_RE.match(nom) or not NOM_RE.match(ref) or not nom.startswith(ref + "-"):
        return None
    p = DOSSIER / ref / nom
    return p if p.is_file() else None


def presentes(s: dict) -> list[dict]:
    """Copies encore sur le site pour cette souscription."""
    out = []
    for i, a in enumerate(s.get("assures") or [], 1):
        for nom in a.get("pieces") or []:
            if chemin(s["ref"], nom):
                out.append({"assure": i, "lien": a.get("lien"), "nom": nom})
    return out


def effacer(ref: str) -> None:
    if NOM_RE.match(ref):
        shutil.rmtree(DOSSIER / ref, ignore_errors=True)


def purger_tmp(age_s: int = 24 * 3600) -> None:
    limite = time.time() - age_s
    for f in TMP.iterdir():
        try:
            if f.stat().st_mtime < limite:
                f.unlink()
        except OSError:
            pass


def purger_impayees(db, jours: int = 30) -> None:
    """Efface les copies des souscriptions jamais payées, passé un délai."""
    limite = time.time() - jours * 86400
    for d in DOSSIER.iterdir():
        if d.is_dir() and d.stat().st_mtime < limite:
            s = db.get_souscription(d.name)
            if not s or s["statut"] in ("attente_paiement", "echec_paiement"):
                shutil.rmtree(d, ignore_errors=True)
