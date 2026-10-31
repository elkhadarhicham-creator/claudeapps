"""Reçu de paiement et accusé de souscription (PDF), avec QR code de vérification.

L'attestation d'assurance officielle reste celle émise par la compagnie :
le cabinet la dépose dans l'espace admin et le client la télécharge ensuite.
"""
import io
from datetime import date

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from . import config, securite

PRUNE = colors.HexColor("#3f1c37")
OR = colors.HexColor("#e0a93a")
GRIS = colors.HexColor("#6b6880")


def _fr(d: str | None) -> str:
    if not d:
        return "—"
    try:
        return date.fromisoformat(d[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return d


def url_verification(ref: str) -> str:
    return f"{config.SITE_URL}/verifier/{ref}?c={securite.code_verification(ref)}"


def recu_pdf(s: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    c.setTitle(f"Reçu {s['ref']}")
    c.setAuthor("Digitalia by Assurances Elkhaddar")

    # Bandeau
    c.setFillColor(PRUNE)
    c.rect(0, H - 34 * mm, W, 34 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(18 * mm, H - 18 * mm, "Digital")
    c.setFillColor(OR)
    c.drawString(18 * mm + c.stringWidth("Digital", "Helvetica-Bold", 22), H - 18 * mm, "ia")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, H - 25 * mm, "by Assurances Elkhaddar · Rabat et Salé")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(W - 18 * mm, H - 18 * mm, "REÇU DE PAIEMENT")
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 18 * mm, H - 25 * mm, "et accusé de souscription")

    y = H - 50 * mm
    c.setFillColor(colors.black)

    def ligne(label, valeur, bold=False):
        nonlocal y
        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        c.drawString(18 * mm, y, label)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        c.drawString(68 * mm, y, str(valeur))
        y -= 6.5 * mm

    ligne("Référence", s["ref"], True)
    ligne("Formule", s["produit"])
    ligne("Compagnie", config.COMPAGNIE)
    ligne("Période de garantie", f"du {_fr(s['date_effet'])} au {_fr(s['date_echeance'])} inclus")
    vehicule = (s.get("options") or {}).get("assistance_auto")
    if vehicule:
        ligne("Assistance auto", " ".join(x for x in (vehicule.get("immatriculation"), vehicule.get("marque"),
                                                       vehicule.get("modele")) if x))
    ligne("Prime TTC payée", f"{s['prime_ttc']:.2f} DH".replace(".", ","), True)
    ligne("Paiement", f"Carte bancaire · transaction {s.get('transaction_id') or '—'}")
    ligne("Payé le", _fr(s.get("payee_le")))
    if s.get("numero_police"):
        ligne("N° de contrat", s["numero_police"], True)

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUNE)
    c.drawString(18 * mm, y, "Assurés")
    y -= 7 * mm
    for a in s["assures"]:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.black)
        c.drawString(18 * mm, y, f"{a.get('nom', '')} {a.get('prenom', '')}")
        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        piece = " · ".join(x for x in [
            f"CIN {a['cin']}" if a.get("cin") else "",
            f"Passeport {a['passeport']}" if a.get("passeport") else "",
        ] if x)
        c.drawString(78 * mm, y, f"{a['lien']} · né(e) le {_fr(a.get('naissance'))} · {piece}")
        y -= 6 * mm

    # QR code de vérification
    url = url_verification(s["ref"])
    img = qrcode.make(url, box_size=6, border=1)
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    qy = 52 * mm
    c.drawImage(ImageReader(b), W - 52 * mm, qy, 34 * mm, 34 * mm)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS)
    c.drawRightString(W - 18 * mm, qy - 4 * mm, f"Code de vérification : {securite.code_verification(s['ref'])}")

    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.black)
    texte = c.beginText(18 * mm, qy + 28 * mm)
    texte.setLeading(11)
    for t in [
        "Ce reçu confirme le paiement et l'enregistrement de votre souscription.",
        "L'attestation d'assurance officielle est émise par la compagnie après",
        "contrôle par le cabinet ; elle vous est envoyée sur WhatsApp et reste",
        "téléchargeable depuis votre lien de suivi.",
        "",
        "Scannez le QR code pour vérifier l'authenticité de ce document.",
    ]:
        texte.textLine(t)
    c.drawText(texte)

    # Pied de page légal
    c.setStrokeColor(colors.HexColor("#e6e2ea"))
    c.line(18 * mm, 36 * mm, W - 18 * mm, 36 * mm)
    c.setFont("Helvetica", 7.2)
    c.setFillColor(GRIS)
    for i, t in enumerate([
        "Intermédiaires d'assurances régis par la loi n° 17-99 portant Code des assurances, sous le contrôle de l'ACAPS.",
        "Assurances Elkhaddar & Co (Rabat) · Elkhaddar Conseil en Assurances SARL AU (Salé) · Code ACAPS C4473",
        "WhatsApp 07 08 29 50 52 · Téléphone 05 37 69 36 25 · Données traitées conformément à la loi 09-08.",
    ]):
        c.drawString(18 * mm, 30 * mm - i * 4.2 * mm, t)
    c.showPage()
    c.save()
    return buf.getvalue()
