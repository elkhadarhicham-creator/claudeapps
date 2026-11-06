"""Lecture d'une CIN marocaine ou d'un passeport avec Claude (vision).

L'image est traitée en mémoire puis oubliée : elle n'est jamais enregistrée.
"""
import base64
import json
import logging

import anthropic

from . import config

log = logging.getLogger("digitalia.ocr")

PROMPT = (
    "Ce document (photo ou PDF) doit être une carte nationale d'identité marocaine (CIN, recto ou verso) ou la page d'identité d'un passeport. "
    "Le recto de la CIN porte le lieu de naissance (« né(e) à ») ; le verso porte l'adresse : mets la ville de l'adresse dans « ville ». la bande MRZ confirme le nom, la date de naissance et le numéro. "
    "Lis le texte latin, le texte arabe et la bande MRZ si elle est présente, puis remplis les champs. "
    "Noms et prénoms en majuscules latines, tels qu'écrits sur la pièce. Dates au format AAAA-MM-JJ. "
    "Sur un passeport marocain, le numéro de CIN figure souvent comme « numéro personnel ». "
    "Laisse une chaîne vide pour tout champ absent ou illisible : n'invente rien. "
    "Si l'image n'est pas une pièce d'identité, mets lisible à false."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "lisible": {"type": "boolean"},
        "type": {"type": "string", "enum": ["CIN", "PASSEPORT", "AUTRE"]},
        "nom": {"type": "string"},
        "prenom": {"type": "string"},
        "naissance": {"type": "string"},
        "sexe": {"type": "string", "enum": ["M", "F", ""]},
        "cin": {"type": "string"},
        "passeport": {"type": "string"},
        "exp_passeport": {"type": "string"},
        "adresse": {"type": "string"},
        "ville": {"type": "string"},
        "lieu_naissance": {"type": "string"},
    },
    "required": ["lisible", "type", "nom", "prenom", "naissance", "sexe", "cin", "passeport", "exp_passeport", "adresse", "ville", "lieu_naissance"],
    "additionalProperties": False,
}

MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}


class OCRIndisponible(Exception):
    pass


class OCRErreur(Exception):
    pass


_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=60.0, max_retries=2)
    return _client


def disponible() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def lire_piece(image: bytes, media_type: str) -> dict:
    if not disponible():
        raise OCRIndisponible()
    if media_type not in MEDIA_TYPES:
        raise OCRErreur("format")
    try:
        r = _get_client().beta.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "document" if media_type == "application/pdf" else "image",
                     "source": {"type": "base64", "media_type": media_type,
                                "data": base64.standard_b64encode(image).decode()}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        )
    except anthropic.BadRequestError as e:
        log.warning("Image refusée par l'API : %s", e.message)
        raise OCRErreur("image") from e
    except anthropic.RateLimitError as e:
        raise OCRErreur("occupe") from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        log.error("Erreur API Claude : %s", e)
        raise OCRErreur("indisponible") from e

    if r.stop_reason == "refusal":
        raise OCRErreur("image")
    texte = next((b.text for b in r.content if b.type == "text"), "")
    try:
        data = json.loads(texte)
    except json.JSONDecodeError as e:
        raise OCRErreur("illisible") from e
    # Nettoyage : on ne garde que les dates bien formées
    for k in ("naissance", "exp_passeport"):
        v = data.get(k) or ""
        if not (len(v) == 10 and v[4] == "-" and v[7] == "-"):
            data[k] = ""
    return data
