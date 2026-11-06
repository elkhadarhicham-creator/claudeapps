"""Passerelle de paiement CMI (Centre Monétique Interbancaire), mode 3D_PAY_HOSTING.

Le client est redirigé vers la page 3-D Secure de la banque : le site ne voit
jamais le numéro de carte. Le CMI rappelle ensuite le serveur (callbackUrl)
pour confirmer le paiement ; seule cette confirmation signée fait foi.

Calcul du hachage « ver3 » (kit d'intégration CMI) :
  paramètres triés par nom (sans tenir compte de la casse), hors HASH et encoding ;
  chaque valeur échappe « \\ » et « | » ; valeurs jointes par « | » puis « |clé_magasin » ;
  SHA-512 puis base64 du condensé binaire.
"""
import base64
import hashlib
import hmac
import time

from . import config

EXCLUS = {"hash", "encoding"}


def _escape(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace("|", "\\|")


def compute_hash(params: dict, store_key: str) -> str:
    keys = sorted((k for k in params if k.lower() not in EXCLUS), key=str.lower)
    plain = "|".join(_escape(params[k]) for k in keys) + "|" + _escape(store_key)
    return base64.b64encode(hashlib.sha512(plain.encode("utf-8")).digest()).decode()


def store_key() -> str:
    return config.DEMO_STORE_KEY if config.PAYMENT_DEMO else config.CMI_STORE_KEY


def verify(params: dict) -> bool:
    recu = params.get("HASH") or params.get("hash") or ""
    return bool(recu) and hmac.compare_digest(compute_hash(params, store_key()), recu)


def build_form(s: dict) -> dict:
    """Champs du formulaire POST envoyé au CMI pour une souscription."""
    base = config.SITE_URL
    lang = {"fr": "fr", "ar": "ar", "da": "ar"}.get(s.get("lang") or "fr", "fr")
    souscripteur = next((a for a in s["assures"] if a["lien"] == "Souscripteur"), s["assures"][0])
    params = {
        "clientid": config.CMI_CLIENT_ID or "DEMO",
        "amount": f"{s['prime_ttc']:.2f}",
        "currency": "504",  # dirham marocain
        "oid": s["ref"],
        "okUrl": f"{base}/paiement/retour",
        "failUrl": f"{base}/paiement/retour",
        "callbackUrl": f"{base}/paiement/cmi/callback",
        "shopurl": f"{base}/",
        "TranType": "PreAuth",
        "storetype": "3D_PAY_HOSTING",
        "hashAlgorithm": "ver3",
        "lang": lang,
        "refreshtime": "5",
        "rnd": str(time.time_ns()),
        "encoding": "UTF-8",
        "BillToName": f"{souscripteur.get('prenom', '')} {souscripteur.get('nom', '')}".strip()[:60],
        "email": s.get("email") or "",
        "tel": s["telephone"],
        "AutoRedirect": "true",
    }
    params["HASH"] = compute_hash(params, store_key())
    action = f"{base}/paiement/demo" if config.PAYMENT_DEMO else config.CMI_GATEWAY_URL
    return {"action": action, "fields": params, "demo": config.PAYMENT_DEMO}


def is_approved(params: dict) -> bool:
    return params.get("ProcReturnCode") == "00" and (params.get("Response") or "").lower() == "approved"
