"""Envois après paiement : WhatsApp (API Cloud de Meta), e-mail (SMTP), fiche vers Digitalia.

Chaque canal est facultatif : s'il n'est pas configuré, l'envoi est simplement
journalisé et le cabinet peut envoyer le message en un clic depuis l'espace admin.
"""
import hashlib
import hmac
import json
import logging
import smtplib
from email.message import EmailMessage

import httpx

from . import config, db, pieces

log = logging.getLogger("digitalia.notif")


def tel_international(tel: str) -> str:
    d = "".join(ch for ch in tel if ch.isdigit())
    if d.startswith("00"):
        d = d[2:]
    if d.startswith("0") and len(d) == 10:
        d = "212" + d[1:]
    return d


def lien_suivi(s: dict) -> str:
    return f"{config.SITE_URL}/suivi/{s['ref']}?t={s['token']}"


def message_client(s: dict) -> str:
    return (
        f"Bonjour, votre paiement de {s['prime_ttc']:.2f} DH est bien reçu (réf. {s['ref']}).\n"
        f"Formule : {s['produit']}, du {s['date_effet']} au {s['date_echeance']}.\n"
        f"Suivez votre contrat et téléchargez vos documents ici : {lien_suivi(s)}\n"
        "Digitalia by Assurances Elkhaddar"
    )


def envoyer_whatsapp(s: dict, texte: str) -> bool:
    if not (config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_ID):
        db.log(s["ref"], "whatsapp_non_configure")
        return False
    to = tel_international(s["telephone"])
    if config.WHATSAPP_TEMPLATE:
        # Hors fenêtre de 24 h, Meta impose un modèle approuvé.
        payload = {
            "messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {
                "name": config.WHATSAPP_TEMPLATE, "language": {"code": "fr"},
                "components": [{"type": "body", "parameters": [
                    {"type": "text", "text": s["ref"]},
                    {"type": "text", "text": f"{s['prime_ttc']:.2f} DH"},
                    {"type": "text", "text": lien_suivi(s)},
                ]}],
            },
        }
    else:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": texte}}
    try:
        r = httpx.post(
            f"https://graph.facebook.com/v21.0/{config.WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}, json=payload, timeout=15,
        )
        ok = r.status_code < 300
        db.log(s["ref"], "whatsapp_envoye" if ok else "whatsapp_erreur", {"status": r.status_code})
        return ok
    except httpx.HTTPError as e:
        db.log(s["ref"], "whatsapp_erreur", {"erreur": str(e)})
        return False


def envoyer_email(to: str, sujet: str, texte: str, pieces: list[tuple[str, bytes]] = (), ref: str | None = None) -> bool:
    if not (config.SMTP_HOST and to):
        return False
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = config.SMTP_FROM, to, sujet
    m.set_content(texte)
    for nom, data in pieces:
        m.add_attachment(data, maintype="application", subtype="pdf", filename=nom)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as srv:
            srv.starttls()
            if config.SMTP_USER:
                srv.login(config.SMTP_USER, config.SMTP_PASSWORD)
            srv.send_message(m)
        db.log(ref, "email_envoye", {"to": to})
        return True
    except (smtplib.SMTPException, OSError) as e:
        db.log(ref, "email_erreur", {"erreur": str(e)})
        return False


def fiche_digitalia(s: dict) -> dict:
    return {
        "reference": s["ref"], "statut": s["statut"], "canal": "site_web",
        "numero_police": s.get("numero_police"), "date_souscription": s.get("cree_le"),
        "date_emission": s.get("emise_le"), "mis_a_jour_le": s.get("maj_le") or s.get("cree_le"), "version": s.get("seq"), "branche": "Assistance voyage",
        "compagnie": config.COMPAGNIE, "produit": s["produit"],
        "date_effet": s["date_effet"], "date_echeance": s["date_echeance"], "prime_ttc": s["prime_ttc"],
        "encaissement": {"mode": "carte_bancaire", "montant": s["prime_ttc"], "statut": "accepte",
                         "transaction": s.get("transaction_id"), "autorisation": s.get("auth_code"),
                         "date": s.get("payee_le")},
        "souscripteur": {"telephone_whatsapp": s["telephone"], "email": s.get("email")},
        "duree_ans": s.get("duree_ans") or 1,
        "produit_compagnie": "INJAD MONDE",
        "vehicule": (s.get("options") or {}).get("vehicule"),
        "vehicule2": (s.get("options") or {}).get("vehicule2"),
        "prime_70_ans": bool((s.get("options") or {}).get("senior")),
        "assures": s["assures"],
        "consentements": s["consentements"],
        "documents": {
            "recu": f"/api/digitalia/souscriptions/{s['ref']}/recu.pdf" if s["statut"] in ("payee", "emise", "annulee") else None,
            "attestation": f"/api/digitalia/souscriptions/{s['ref']}/attestation.pdf" if s.get("attestation_fichier") else None,
            # Copies CIN / passeport : présentes jusqu'à l'accusé de réception de Digitalia
            "pieces": [{**p, "url": f"/api/digitalia/souscriptions/{s['ref']}/pieces/{p['nom']}"}
                       for p in pieces.presentes(s)] if s["statut"] in ("payee", "emise", "annulee") else [],
        },
    }


def envoyer_digitalia(s: dict) -> bool:
    if not config.DIGITALIA_WEBHOOK_URL:
        return False
    body = json.dumps(fiche_digitalia(s), ensure_ascii=False).encode()
    sig = hmac.new(config.SECRET_KEY.encode(), body, hashlib.sha256).hexdigest()
    try:
        r = httpx.post(config.DIGITALIA_WEBHOOK_URL, content=body, timeout=15,
                       headers={"Content-Type": "application/json", "X-Digitalia-Signature": sig})
        ok = r.status_code < 300
    except httpx.HTTPError:
        ok = False
    # Modification technique : la fiche ne doit pas réapparaître dans la reprise par Digitalia
    db.update_souscription(s["ref"], _signaler=False, webhook_statut="ok" if ok else "erreur")
    db.log(s["ref"], "digitalia_ok" if ok else "digitalia_erreur")
    return ok


def apres_paiement(ref: str) -> None:
    """Tâche de fond lancée une seule fois, quand le paiement est confirmé."""
    from . import documents
    s = db.get_souscription(ref)
    if not s:
        return
    envoyer_whatsapp(s, message_client(s))
    if s.get("email"):
        envoyer_email(s["email"], f"Votre assurance voyage - reçu {ref}", message_client(s),
                      [(f"recu-{ref}.pdf", documents.recu_pdf(s))], ref)
    if config.NOTIFY_EMAIL:
        envoyer_email(config.NOTIFY_EMAIL, f"[Digitalia] Nouveau paiement {ref} - à émettre",
                      json.dumps(fiche_digitalia(s), ensure_ascii=False, indent=2), ref=ref)
    envoyer_digitalia(s)


def apres_emission(ref: str) -> None:
    s = db.get_souscription(ref)
    if not s:
        return
    texte = (f"Bonne nouvelle : votre contrat n° {s['numero_police']} est émis (réf. {ref}).\n"
             f"Téléchargez votre attestation pour le visa : {lien_suivi(s)}")
    envoyer_whatsapp(s, texte)
    if s.get("email"):
        envoyer_email(s["email"], f"Votre attestation d'assurance voyage - {s['numero_police']}", texte, ref=ref)
    envoyer_digitalia(s)
