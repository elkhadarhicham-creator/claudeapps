"""Passerelle de paiement YouCan Pay (https://docs.youcan.shop/youcan-pay/).

Parcours :
  1. le serveur crée un jeton de paiement (« tokenize ») avec le montant en centimes et la référence ;
  2. la page /paiement/youcanpay affiche le formulaire de carte de YouCan Pay (yp.js) : le site ne voit
     jamais le numéro de carte, et la 3-D Secure est gérée par YouCan Pay ;
  3. le navigateur annonce le résultat ; le serveur le vérifie auprès de YouCan Pay avant de valider ;
  4. YouCan Pay envoie aussi un webhook signé (transaction.paid) : il valide le paiement même si le
     client a fermé la page.

Les clés « sandbox » (pri_sandbox_…, pub_sandbox_…) activent le mode test : aucune carte n'est débitée.
"""
import hashlib
import hmac
import logging

import httpx

from . import config

log = logging.getLogger("digitalia.youcanpay")

HOTE = "https://youcanpay.com"


class ErreurYouCanPay(Exception):
    pass


def configure() -> bool:
    return bool(config.YCP_PRIVATE_KEY and config.YCP_PUBLIC_KEY)


def sandbox() -> bool:
    return config.YCP_PRIVATE_KEY.startswith("pri_sandbox_")


def centimes(montant_dh: float) -> int:
    return int(round(montant_dh * 100))


def tokenize(s: dict) -> str:
    """Crée le jeton de paiement de la souscription et renvoie son identifiant."""
    base = config.SITE_URL
    sous = next((a for a in s["assures"] if a["lien"] == "Souscripteur"), s["assures"][0])
    donnees = {
        "pri_key": config.YCP_PRIVATE_KEY,
        "order_id": s["ref"],
        "amount": str(centimes(s["prime_ttc"])),
        "currency": "MAD",
        "success_url": f"{base}/suivi/{s['ref']}?t={s['token']}",
        "error_url": f"{base}/suivi/{s['ref']}?t={s['token']}",
        "metadata[ref]": s["ref"],
        "metadata[produit]": s["produit"][:120],
        "customer[name]": f"{sous.get('prenom', '')} {sous.get('nom', '')}".strip()[:80],
        "customer[phone]": s["telephone"],
    }
    if s.get("email"):
        donnees["customer[email]"] = s["email"]
    url = f"{HOTE}/sandbox/api/tokenize" if sandbox() else f"{HOTE}/api/tokenize"
    try:
        r = httpx.post(url, data=donnees, headers={"Accept": "application/json"}, timeout=20)
    except httpx.HTTPError as e:
        raise ErreurYouCanPay(f"YouCan Pay injoignable : {e}") from e
    if r.status_code >= 300:
        raise ErreurYouCanPay(f"Jeton refusé par YouCan Pay ({r.status_code}) : {r.text[:300]}")
    jeton = r.json().get("token")
    if isinstance(jeton, dict):  # la documentation montre les deux formes
        jeton = jeton.get("id")
    if not jeton:
        raise ErreurYouCanPay(f"Réponse YouCan Pay sans jeton : {r.text[:300]}")
    return str(jeton)


def transaction(transaction_id: str) -> dict:
    """Lit une transaction (API v2, clés réelles uniquement)."""
    try:
        r = httpx.get(f"{HOTE}/api/v2/transactions/{transaction_id}", auth=(config.YCP_PRIVATE_KEY, ""),
                      headers={"Accept": "application/json"}, timeout=20)
    except httpx.HTTPError as e:
        raise ErreurYouCanPay(f"YouCan Pay injoignable : {e}") from e
    if r.status_code != 200:
        raise ErreurYouCanPay(f"Transaction illisible ({r.status_code}) : {r.text[:300]}")
    return r.json()


def transaction_payee(t: dict, ref: str, montant_dh: float) -> bool:
    """La transaction lue via l'API correspond-elle bien à la souscription, payée et au bon montant ?"""
    try:
        montant = float((t.get("amount") or {}).get("amount"))
    except (TypeError, ValueError):
        return False
    return (t.get("status") == "paid" and str(t.get("order_id")) == ref
            and (t.get("amount") or {}).get("currency") == "MAD" and abs(montant - montant_dh) < 0.005)


def signature_valide(corps: bytes, signature: str) -> bool:
    """En-tête X-YOUCANPAY-SIGNATURE : HMAC-SHA256 (hexadécimal) du corps brut, clé = clé privée."""
    if not signature or not config.YCP_PRIVATE_KEY:
        return False
    attendu = hmac.new(config.YCP_PRIVATE_KEY.encode(), corps, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, signature.strip().lower())
