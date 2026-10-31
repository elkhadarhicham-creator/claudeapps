"""Digitalia Assurance Voyage - serveur web (FastAPI)."""
import html
import threading
from contextlib import asynccontextmanager
import logging
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import cmi, config, db, documents, mai, notifications, ocr, pieces, securite
from .offres import (AGE_MAX_ENFANT, AGE_MAX_ENFANT_ETUDIANT, AGE_SENIOR, LIENS, MAX_ENFANTS, OFFRES, VEHICULE2,
                     age_a, libelle_duree, tarif)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("digitalia")

STATIC = config.BASE_DIR / "static"
limite_ocr = securite.RateLimiter(30, 3600)
limite_form = securite.RateLimiter(20, 3600)
limite_login = securite.RateLimiter(8, 900)

CMI_HOST = re.match(r"https?://[^/]+", config.CMI_GATEWAY_URL).group(0)


def demarrage():
    db.conn()
    # Minimisation des données (loi 09-08) : les souscriptions jamais payées sont supprimées après 30 jours.
    limite = (datetime.now(config.TZ) - timedelta(days=30)).isoformat()
    with db.tx() as c:
        c.execute("DELETE FROM souscriptions WHERE statut IN ('attente_paiement','echec_paiement') AND cree_le < ?", (limite,))
    pieces.purger_tmp()
    pieces.purger_impayees(db)
    log.info("Démarrage - paiement %s, lecture IA %s",
             "DÉMONSTRATION" if config.PAYMENT_DEMO else "CMI réel", "active" if ocr.disponible() else "désactivée")


@asynccontextmanager
async def cycle_de_vie(_app):
    demarrage()
    yield


app = FastAPI(title="Digitalia Assurance Voyage", docs_url=None, redoc_url=None, openapi_url=None, lifespan=cycle_de_vie)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    r.headers["Permissions-Policy"] = "camera=(self), geolocation=()"
    r.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        f"script-src 'self'; connect-src 'self'; form-action 'self' {CMI_HOST}; frame-ancestors 'none'; base-uri 'none'"
    )
    if config.SITE_URL.startswith("https://"):
        r.headers["Strict-Transport-Security"] = "max-age=31536000"
    return r


def ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?")


def aujourdhui() -> date:
    return datetime.now(config.TZ).date()


def ajouter_mois(d: date, mois: int) -> date:
    m = d.month - 1 + mois
    y, m = d.year + m // 12, m % 12 + 1
    jours = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(y, m, min(d.day, jours[m - 1]))


def tel_valide(t: str) -> str:
    d = re.sub(r"\D", "", t)
    if not 9 <= len(d) <= 13:
        raise ValueError("telephone")
    return t.strip()


# ─────────────────────────── Pages ───────────────────────────

@app.get("/", include_in_schema=False)
def accueil():
    return FileResponse(STATIC / "index.html")


@app.get("/suivi/{ref}", include_in_schema=False)
def page_suivi(ref: str):
    return FileResponse(STATIC / "suivi.html")


@app.get("/admin", include_in_schema=False)
def page_admin():
    return FileResponse(STATIC / "admin.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(STATIC / "sw.js", media_type="text/javascript")


@app.get("/sante", include_in_schema=False)
def sante():
    return {"ok": True}


# ─────────────────────────── API publique ───────────────────────────

@app.get("/api/config")
def api_config():
    return {
        "ocr": ocr.disponible(),
        "paiement_demo": config.PAYMENT_DEMO,
        "whatsapp": config.WHATSAPP_CABINET,
        "aujourdhui": aujourdhui().isoformat(),
        "offres": list(OFFRES.values()),
        "vehicule2": VEHICULE2,
        "age_max_enfant": AGE_MAX_ENFANT,
        "age_max_enfant_etudiant": AGE_MAX_ENFANT_ETUDIANT,
        "age_senior": AGE_SENIOR,
    }


@app.post("/api/ocr")
async def api_ocr(request: Request, fichier: UploadFile = File(...)):
    """Garde la copie de la pièce (pour le dossier client dans Digitalia) et la lit avec Claude si possible."""
    if not limite_ocr.ok(ip(request)):
        return JSONResponse({"ok": False, "code": "trop"}, status_code=429)
    data = await fichier.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        return JSONResponse({"ok": False, "code": "taille"}, status_code=413)
    media = fichier.content_type or ""
    if media == "image/jpg":
        media = "image/jpeg"
    nom = (fichier.filename or "").lower()
    if media in ("", "application/octet-stream"):  # certains téléphones n'envoient pas le type
        media = "application/pdf" if nom.endswith(".pdf") else "image/png" if nom.endswith(".png") else "image/jpeg"
    if data[:4] == b"%PDF":
        media = "application/pdf"
    if media not in pieces.EXT or not data:
        return JSONResponse({"ok": False, "code": "format"}, status_code=422)
    pid = pieces.deposer(data, media)
    if not ocr.disponible():
        return {"ok": False, "code": "indisponible", "piece_id": pid}
    try:
        res = ocr.lire_piece(data, media)
    except ocr.OCRErreur as e:
        return {"ok": False, "code": str(e), "piece_id": pid}
    except ocr.OCRIndisponible:
        return {"ok": False, "code": "indisponible", "piece_id": pid}
    if not res.get("lisible"):
        return {"ok": False, "code": "illisible", "piece_id": pid}
    return {"ok": True, "data": res, "piece_id": pid}


CIN_RE = re.compile(r"[A-Z]{1,2}[0-9]{1,6}[A-Z]?")  # règle du portail MAI


class Assure(BaseModel):
    lien: Literal[LIENS]
    nom: str = Field(min_length=1, max_length=60)
    prenom: str = Field(min_length=1, max_length=60)
    naissance: date
    cin: str = Field("", max_length=20)
    passeport: str = Field("", max_length=20)
    exp_passeport: date | None = None
    adresse: str = Field("", max_length=200)
    etudiant: bool = False  # enfant de 21 à 25 ans poursuivant ses études au Maroc
    # Informations du souscripteur demandées par le portail MAI
    civilite: Literal["", "M.", "Mme"] = ""
    lieu_naissance: str = Field("", max_length=80)
    situation_familiale: Literal["", "Célibataire", "Marié(e)", "Divorcé(e)", "Veuf(ve)"] = ""
    ville: str = Field("", max_length=80)
    code_postal: str = Field("", max_length=10)
    profession: str = Field("", max_length=80)
    mutuelle: str = Field("", max_length=80)       # assurance couvrant le même risque (AMO, CNOPS, mutuelle…)
    circonstances: str = Field("", max_length=300)  # circonstances susceptibles d'aggraver le risque
    pieces: list[str] = Field(default_factory=list, max_length=pieces.MAX_PAR_ASSURE)  # copies CIN / passeport
    # Assistance déjà souscrite couvrant le même risque (liste du portail MAI)
    assistance_existante: Literal["", "SANS", "SAHAM ASSISTANCE", "AXA ASSISTANCE", "WAFA IMA ASSISTANCE", "RMA ASSISTANCE"] = ""

    @field_validator("cin")
    @classmethod
    def format_cin(cls, v: str) -> str:
        v = v.replace(" ", "").upper()
        if v and not CIN_RE.fullmatch(v):
            raise ValueError("CIN : 1 ou 2 lettres puis des chiffres (ex. AB123456)")
        return v

    @field_validator("pieces")
    @classmethod
    def ids_pieces(cls, v: list[str]) -> list[str]:
        return [p for p in v if pieces.ID_RE.match(p)]

    @field_validator("nom", "prenom", "cin", "passeport", "adresse", "lieu_naissance", "ville", "code_postal",
                     "profession", "mutuelle", "circonstances")
    @classmethod
    def nettoie(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("exp_passeport", mode="before")
    @classmethod
    def vide_none(cls, v):
        return v or None


class Consentements(BaseModel):
    conditions_generales: bool
    exactitude: bool
    loi_09_08: bool


class Vehicule(BaseModel):
    immatriculation: str = Field(min_length=3, max_length=20)
    marque: str = Field("", max_length=40)
    modele: str = Field("", max_length=40)

    @field_validator("immatriculation", "marque", "modele")
    @classmethod
    def nettoie(cls, v: str) -> str:
        return " ".join(v.split()).upper()


class SouscriptionIn(BaseModel):
    offre: str
    duree_ans: int = Field(1, ge=1, le=5)
    vehicule: Vehicule | None = None    # véhicule inclus dans le forfait (facultatif)
    vehicule2: Vehicule | None = None   # deuxième véhicule : surprime
    date_effet: date
    telephone: str = Field(max_length=20)
    email: str = Field("", max_length=120)
    lang: Literal["fr", "ar", "da"] = "fr"
    assures: list[Assure] = Field(min_length=1, max_length=10)
    consentements: Consentements


def erreur(code: str, message: str, status: int = 422):
    raise HTTPException(status, {"code": code, "message": message})


@app.post("/api/souscriptions")
def creer_souscription(body: SouscriptionIn, request: Request):
    if not limite_form.ok(ip(request)):
        erreur("trop", "Trop de tentatives, réessayez plus tard.", 429)
    o = OFFRES.get(body.offre)
    if not o or not o.get("en_ligne"):
        erreur("offre", "Cette formule se souscrit sur devis.")
    auj = aujourdhui()
    # Injad Monde : prise d'effet le lendemain à midi de la date de paiement
    if body.date_effet <= auj:
        erreur("date_effet", "Le contrat prend effet au plus tôt demain (le lendemain du paiement, à midi).")
    if body.date_effet > auj + timedelta(days=180):
        erreur("date_effet", "La date d'effet doit être dans les 6 prochains mois.")
    try:
        tel_valide(body.telephone)
    except ValueError:
        erreur("telephone", "Numéro WhatsApp invalide.")
    if not body.email:
        erreur("email", "Adresse e-mail obligatoire : le contrat y est envoyé.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", body.email):
        erreur("email", "Adresse e-mail invalide.")
    c = body.consentements
    if not (c.conditions_generales and c.exactitude and c.loi_09_08):
        erreur("consentements", "Les trois consentements sont obligatoires.")
    liens = [a.lien for a in body.assures]
    if liens.count("Souscripteur") != 1 or liens[0] != "Souscripteur":
        erreur("assures", "Le premier assuré doit être le souscripteur, et lui seul.")
    if liens.count("Conjoint(e)") > 1:
        erreur("assures", "Un seul conjoint par contrat famille.")
    if liens.count("Enfant") > MAX_ENFANTS:
        erreur("assures", f"{MAX_ENFANTS} enfants au maximum.")
    for i, a in enumerate(body.assures, 1):
        if a.lien == "Souscripteur" and not (a.cin or a.passeport):
            erreur("assures", "Souscripteur : numéro de CIN ou de passeport requis.")
        if a.lien == "Souscripteur":
            manque = [lib for lib, v in (("civilité", a.civilite), ("lieu de naissance", a.lieu_naissance),
                                         ("situation familiale", a.situation_familiale), ("adresse", a.adresse),
                                         ("ville", a.ville), ("code postal", a.code_postal), ("profession", a.profession),
                                         ("assurance maladie / mutuelle", a.mutuelle),
                                         ("autre assistance déjà souscrite", a.assistance_existante),
                                         ("circonstances aggravant le risque", a.circonstances)) if not v]
            if manque:
                erreur("assures", "Souscripteur : " + ", ".join(manque) + " à compléter.")
        if a.naissance > auj:
            erreur("assures", f"Assuré {i} : date de naissance dans le futur.")
        age = age_a(a.naissance, body.date_effet)
        if a.lien == "Enfant" and age >= AGE_MAX_ENFANT:
            if age > AGE_MAX_ENFANT_ETUDIANT:
                erreur("age", f"Assuré {i} : un enfant doit avoir moins de {AGE_MAX_ENFANT} ans, ou au plus "
                              f"{AGE_MAX_ENFANT_ETUDIANT} ans s'il est étudiant au Maroc. Formule individuelle sur devis.")
            if not a.etudiant:
                erreur("age", f"Assuré {i} : de {AGE_MAX_ENFANT} à {AGE_MAX_ENFANT_ETUDIANT} ans, un enfant n'est couvert "
                              "que s'il poursuit ses études au Maroc : cochez « Étudiant(e) au Maroc ».")
        if a.exp_passeport and a.exp_passeport < body.date_effet:
            erreur("assures", f"Assuré {i} : passeport expiré à la date d'effet.")

    if body.duree_ans not in o.get("durees_ans", [1]):
        erreur("duree", "Durée non proposée pour cette formule.")
    if body.vehicule2 and not body.vehicule:
        erreur("vehicule", "Indiquez d'abord le véhicule inclus avant d'ajouter un deuxième véhicule.")
    senior = any(age_a(a.naissance, body.date_effet) >= AGE_SENIOR for a in body.assures)
    if senior and not o.get("prix_70"):
        erreur("age", f"Un assuré a {AGE_SENIOR} ans ou plus : le tarif se fait sur devis. "
                      "Contactez-nous sur WhatsApp au 07 08 29 50 52.")
    echeance = ajouter_mois(body.date_effet, 12 * body.duree_ans) - timedelta(days=1)
    prime = tarif(o, body.duree_ans, senior, bool(body.vehicule2))
    produit = (f"{o['nom']} · {libelle_duree(body.duree_ans)}" + (" · + 70 ans" if senior else "")
               + (f" + {VEHICULE2['nom']}" if body.vehicule2 else ""))
    ref = f"DGV-{auj:%y%m}-{secrets.token_hex(3).upper()}"
    s = {
        "ref": ref, "token": securite.new_token(), "offre": o["code"], "produit": produit,
        "duree_ans": body.duree_ans,
        "options": {"vehicule": body.vehicule.model_dump() if body.vehicule else None,
                    "vehicule2": body.vehicule2.model_dump() if body.vehicule2 else None, "senior": senior},
        "date_effet": body.date_effet.isoformat(), "date_echeance": echeance.isoformat(),
        "prime_ttc": prime, "telephone": body.telephone.strip(), "email": body.email.strip() or None,
        "lang": body.lang,
        "assures": [a.model_dump(mode="json") for a in body.assures],
        "consentements": {**c.model_dump(), "horodatage": db.now(), "ip": ip(request)},
        "statut": "attente_paiement", "ip": ip(request), "cree_le": db.now(),
    }
    pieces.rattacher(ref, s["assures"])
    db.insert_souscription(s)
    db.log(ref, "creee", {"prime": prime, "duree_ans": body.duree_ans, "senior": senior, "vehicule2": bool(body.vehicule2),
                          "assures": len(body.assures)})
    return {"ref": ref, "token": s["token"], "prime_ttc": prime, "date_echeance": s["date_echeance"],
            "paiement": cmi.build_form(db.get_souscription(ref))}


def souscription_client(ref: str, t: str) -> dict:
    s = db.get_souscription(ref)
    if not s or not t or not secrets.compare_digest(s["token"], t):
        raise HTTPException(404, {"code": "introuvable", "message": "Souscription introuvable."})
    return s


@app.post("/api/souscriptions/{ref}/paiement")
def relancer_paiement(ref: str, t: str):
    s = souscription_client(ref, t)
    if s["statut"] not in ("attente_paiement", "echec_paiement"):
        erreur("statut", "Cette souscription est déjà payée.", 409)
    db.update_souscription(ref, statut="attente_paiement")
    return cmi.build_form(db.get_souscription(ref))


@app.get("/api/suivi/{ref}")
def api_suivi(ref: str, t: str):
    s = souscription_client(ref, t)
    return {
        "ref": s["ref"], "statut": s["statut"], "produit": s["produit"],
        "date_effet": s["date_effet"], "date_echeance": s["date_echeance"], "prime_ttc": s["prime_ttc"],
        "assures": [{"lien": a["lien"], "nom": a["nom"], "prenom": a["prenom"]} for a in s["assures"]],
        "numero_police": s.get("numero_police"),
        "vehicule": (s.get("options") or {}).get("vehicule"),
        "vehicule2": (s.get("options") or {}).get("vehicule2"),
        "recu": s["statut"] in ("payee", "emise"),
        "attestation": bool(s.get("attestation_fichier")),
        "payee_le": s.get("payee_le"),
    }


@app.get("/documents/{ref}/recu.pdf")
def doc_recu(ref: str, t: str):
    s = souscription_client(ref, t)
    if s["statut"] not in ("payee", "emise"):
        raise HTTPException(404)
    return Response(documents.recu_pdf(s), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="recu-{ref}.pdf"'})


@app.get("/documents/{ref}/attestation.pdf")
def doc_attestation(ref: str, t: str):
    s = souscription_client(ref, t)
    if not s.get("attestation_fichier"):
        raise HTTPException(404)
    return FileResponse(config.DATA_DIR / "attestations" / s["attestation_fichier"], media_type="application/pdf",
                        filename=f"attestation-{ref}.pdf")


class DevisIn(BaseModel):
    offre: str
    nom: str = Field("", max_length=80)
    telephone: str = Field(max_length=20)
    date_depart: date | None = None
    message: str = Field("", max_length=600)


@app.post("/api/devis")
def demander_devis(body: DevisIn, request: Request):
    if not limite_form.ok(ip(request)):
        erreur("trop", "Trop de tentatives, réessayez plus tard.", 429)
    if body.offre not in OFFRES:
        erreur("offre", "Formule inconnue.")
    try:
        tel_valide(body.telephone)
    except ValueError:
        erreur("telephone", "Numéro WhatsApp invalide.")
    i = db.insert_devis(body.model_dump(mode="json"))
    return {"ok": True, "id": i}


def _masque(a: dict) -> str:
    return f"{a.get('nom', '')} {(a.get('prenom') or ' ')[0]}.".strip()


@app.get("/verifier/{ref}", response_class=HTMLResponse)
def verifier(ref: str, c: str = ""):
    s = db.get_souscription(ref)
    valide = bool(s and c and secrets.compare_digest(securite.code_verification(ref), c.upper())
                  and s["statut"] in ("payee", "emise"))
    if valide:
        etat = (f"Contrat émis · n° {html.escape(s['numero_police'])}" if s["statut"] == "emise"
                else "Paiement reçu · contrat en cours d'émission par la compagnie")
        assures = "".join(f"<li>{html.escape(_masque(a))} · {html.escape(a['lien'])}</li>" for a in s["assures"])
        corps = f"""<div class="ok">✓ Document authentique</div>
        <dl><dt>Référence</dt><dd>{html.escape(ref)}</dd><dt>Formule</dt><dd>{html.escape(s['produit'])}</dd>
        <dt>Compagnie</dt><dd>{html.escape(config.COMPAGNIE)}</dd>
        <dt>Période</dt><dd>du {documents._fr(s['date_effet'])} au {documents._fr(s['date_echeance'])}</dd>
        <dt>État</dt><dd>{etat}</dd></dl><h2>Assurés</h2><ul>{assures}</ul>"""
    else:
        corps = '<div class="ko">✗ Document non reconnu</div><p>Ce code ne correspond à aucune souscription payée. Contactez le cabinet pour vérification.</p>'
    return _page("Vérification d'un document", corps)


def _page(titre: str, corps: str, scripts: str = "") -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titre)} · Digitalia</title>
<link rel="stylesheet" href="/static/mini.css"></head><body><header><b>Digital<span>ia</span></b>
<small>by Assurances Elkhaddar</small></header><main><h1>{html.escape(titre)}</h1>{corps}</main>{scripts}</body></html>""")


# ─────────────────────────── Paiement ───────────────────────────

def traiter_callback(params: dict, taches: BackgroundTasks | None) -> str:
    """Rappel serveur à serveur du CMI. Réponses attendues par le CMI : ACTION=POSTAUTH / APPROVED / FAILURE."""
    if not cmi.verify(params):
        db.log(params.get("oid"), "callback_hash_invalide")
        return "FAILURE"
    ref = params.get("oid", "")
    s = db.get_souscription(ref)
    if not s:
        return "FAILURE"
    if params.get("amount") and abs(float(params["amount"].replace(",", ".")) - s["prime_ttc"]) > 0.001:
        db.log(ref, "callback_montant_incoherent", {"recu": params.get("amount")})
        return "FAILURE"
    if cmi.is_approved(params):
        if s["statut"] == "attente_paiement" or s["statut"] == "echec_paiement":
            db.update_souscription(
                ref, statut="payee", payee_le=db.now(), transaction_id=params.get("TransId"),
                auth_code=params.get("AuthCode"),
                paiement_detail={k: params.get(k) for k in ("TransId", "AuthCode", "ProcReturnCode", "Response",
                                                             "maskedCreditCard", "EXTRA.TRXDATE") if params.get(k)},
            )
            db.log(ref, "payee", {"transaction": params.get("TransId")})
            def suite():
                notifications.apres_paiement(ref)
                if mai.MODE == "auto" and mai.configure():
                    mai.emettre(ref)
            if taches is not None:
                taches.add_task(suite)
            else:
                threading.Thread(target=suite, daemon=True).start()
        return "ACTION=POSTAUTH"
    if s["statut"] == "attente_paiement":
        db.update_souscription(ref, statut="echec_paiement")
    db.log(ref, "paiement_refuse", {"code": params.get("ProcReturnCode"), "message": params.get("ErrMsg")})
    return "APPROVED"


@app.post("/paiement/cmi/callback", response_class=PlainTextResponse)
async def cmi_callback(request: Request, taches: BackgroundTasks):
    params = {k: str(v) for k, v in (await request.form()).items()}
    return traiter_callback(params, taches)


@app.api_route("/paiement/retour", methods=["GET", "POST"])
async def paiement_retour(request: Request):
    """Le navigateur du client revient de la page bancaire (okUrl / failUrl)."""
    params = {k: str(v) for k, v in (await request.form()).items()} if request.method == "POST" else {}
    s = db.get_souscription(params.get("oid", "")) if params else None
    if s and cmi.verify(params):
        return RedirectResponse(f"/suivi/{s['ref']}?t={s['token']}", status_code=303)
    return _page("Retour du paiement", "<p>Nous n'avons pas pu identifier votre paiement. "
                 "Si votre carte a été débitée, contactez-nous sur WhatsApp au 07 08 29 50 52 : votre contrat sera vérifié.</p>")


def _hidden(params: dict) -> str:
    return "".join(f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(v)}">' for k, v in params.items())


@app.post("/paiement/demo", response_class=HTMLResponse)
async def passerelle_demo(request: Request):
    """Imitation de la page 3-D Secure du CMI, active tant que le contrat commerçant n'est pas signé."""
    if not config.PAYMENT_DEMO:
        raise HTTPException(404)
    params = {k: str(v) for k, v in (await request.form()).items()}
    if not cmi.verify(params):
        return _page("Paiement", "<p>Requête de paiement invalide.</p>")
    montant = html.escape(params.get("amount", "")).replace(".", ",")
    corps = f"""<div class="demo">Mode démonstration : aucune carte n'est débitée. Après signature du contrat commerçant,
    cette étape se fera sur la page sécurisée du CMI.</div>
    <div class="bank"><p>Marchand : <b>Digitalia · Assurances Elkhaddar</b><br>Commande : <b>{html.escape(params.get('oid', ''))}</b></p>
    <p class="amt">{montant} MAD</p>
    <label>Numéro de carte<input inputmode="numeric" placeholder="4000 0000 0000 0002" autocomplete="off"></label>
    <div class="row"><label>Expiration<input placeholder="MM/AA" autocomplete="off"></label><label>CVV<input placeholder="123" autocomplete="off"></label></div>
    <form method="post" action="/paiement/demo/decision">{_hidden(params)}
      <button name="decision" value="ok" class="btn">Valider le paiement (simulation)</button>
      <button name="decision" value="ko" class="btn line">Simuler un refus</button></form></div>"""
    return _page("Paiement sécurisé 3-D Secure", corps)


@app.post("/paiement/demo/decision", response_class=HTMLResponse)
async def passerelle_demo_decision(request: Request):
    if not config.PAYMENT_DEMO:
        raise HTTPException(404)
    form = {k: str(v) for k, v in (await request.form()).items()}
    decision = form.pop("decision", "ko")
    if not cmi.verify(form):
        return _page("Paiement", "<p>Requête de paiement invalide.</p>")
    retour = {k: v for k, v in form.items() if k not in ("HASH", "encoding")}
    ok = decision == "ok"
    retour.update({
        "ProcReturnCode": "00" if ok else "05", "Response": "Approved" if ok else "Declined",
        "TransId": f"DEMO{secrets.token_hex(5).upper()}", "AuthCode": f"{secrets.randbelow(10**6):06d}" if ok else "",
        "maskedCreditCard": "4000 00** **** 0002", "ErrMsg": "" if ok else "Transaction refusée (simulation)",
    })
    retour["HASH"] = cmi.compute_hash(retour, cmi.store_key())
    traiter_callback(dict(retour), None)  # même chemin que le vrai rappel serveur du CMI
    cible = retour["okUrl"] if ok else retour["failUrl"]
    corps = f"""<p>Retour vers le site…</p><form id="auto" method="post" action="{html.escape(cible)}">{_hidden(retour)}
    <button class="btn">Continuer</button></form>"""
    return _page("Paiement", corps, '<script src="/static/autosubmit.js"></script>')


# ─────────────────────────── Administration ───────────────────────────

def admin(request: Request):
    if not securite.admin_session_valide(request.cookies.get("dg_admin")):
        raise HTTPException(401, {"code": "auth", "message": "Connexion requise."})


class LoginIn(BaseModel):
    mot_de_passe: str = Field(max_length=200)


@app.post("/api/admin/login")
def admin_login(body: LoginIn, request: Request):
    if not limite_login.ok(ip(request)):
        erreur("trop", "Trop de tentatives, patientez 15 minutes.", 429)
    if not config.ADMIN_PASSWORD:
        erreur("config", "ADMIN_PASSWORD n'est pas défini sur le serveur.", 503)
    if not securite.mot_de_passe_ok(body.mot_de_passe):
        erreur("auth", "Mot de passe incorrect.", 401)
    r = JSONResponse({"ok": True})
    r.set_cookie("dg_admin", securite.admin_session(), max_age=securite.SESSION_TTL, httponly=True,
                 samesite="strict", secure=config.SITE_URL.startswith("https://"), path="/")
    return r


@app.post("/api/admin/logout")
def admin_logout():
    r = JSONResponse({"ok": True})
    r.delete_cookie("dg_admin", path="/")
    return r


@app.get("/api/admin/tableau", dependencies=[Depends(admin)])
def admin_tableau(statut: str | None = None, q: str | None = None):
    lignes = []
    for s in db.list_souscriptions(statut or None, q or None):
        sous = s["assures"][0] if s["assures"] else {}
        lignes.append({k: s.get(k) for k in ("ref", "statut", "produit", "date_effet", "date_echeance", "prime_ttc",
                                             "telephone", "numero_police", "cree_le", "payee_le", "webhook_statut",
                                             "digitalia_importe_le")}
                      | {"souscripteur": f"{sous.get('nom', '')} {sous.get('prenom', '')}", "nb_assures": len(s["assures"])})
    return {"stats": db.stats(), "souscriptions": lignes, "demo": config.PAYMENT_DEMO, "mai": mai.etat()}


@app.get("/api/admin/souscriptions/{ref}", dependencies=[Depends(admin)])
def admin_detail(ref: str):
    s = db.get_souscription(ref)
    if not s:
        raise HTTPException(404)
    s.pop("token", None)
    s["journal"] = db.journal(ref)
    s["mai"] = mai.etat()
    s["mai_capture"] = (mai.DOSSIER / f"{ref}-erreur.png").exists()
    s["pieces_presentes"] = pieces.presentes(s)
    s["fiche_digitalia"] = notifications.fiche_digitalia(s)
    full = db.get_souscription(ref)
    s["lien_suivi"] = notifications.lien_suivi(full)
    s["whatsapp_lien"] = ("https://wa.me/" + notifications.tel_international(s["telephone"]) + "?text="
                          + __import__("urllib.parse").parse.quote(notifications.message_client(full)))
    return s


@app.post("/api/admin/souscriptions/{ref}/emettre", dependencies=[Depends(admin)])
async def admin_emettre(ref: str, taches: BackgroundTasks, numero_police: str = Form(..., max_length=40),
                        attestation: UploadFile | None = File(None)):
    s = db.get_souscription(ref)
    if not s:
        raise HTTPException(404)
    if s["statut"] not in ("payee", "emise"):
        erreur("statut", "Le paiement n'est pas confirmé.", 409)
    champs = {"numero_police": numero_police.strip(), "statut": "emise", "emise_le": db.now()}
    if attestation is not None and attestation.filename:
        data = await attestation.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024 or not data.startswith(b"%PDF"):
            erreur("fichier", "L'attestation doit être un PDF de moins de 10 Mo.")
        nom = f"{ref}.pdf"
        (config.DATA_DIR / "attestations" / nom).write_bytes(data)
        champs["attestation_fichier"] = nom
    premiere = s["statut"] == "payee"
    db.update_souscription(ref, **champs)
    db.log(ref, "emise", {"police": champs["numero_police"]})
    if premiere:
        taches.add_task(notifications.apres_emission, ref)
    return {"ok": True}


@app.post("/api/admin/souscriptions/{ref}/mai", dependencies=[Depends(admin)])
def admin_emettre_mai(ref: str):
    """Le conseiller a contrôlé la souscription : le robot la saisit sur portail.mai.ma."""
    r = mai.emettre(ref)
    if not r["ok"]:
        erreur("mai", r["erreur"], 502)
    return r


@app.get("/api/admin/souscriptions/{ref}/mai-capture.png", dependencies=[Depends(admin)])
def admin_capture_mai(ref: str):
    f = mai.DOSSIER / f"{re.sub(r'[^A-Z0-9-]', '', ref)}-erreur.png"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="image/png")


@app.get("/api/admin/souscriptions/{ref}/pieces/{nom}", dependencies=[Depends(admin)])
def admin_piece(ref: str, nom: str):
    p = pieces.chemin(ref, nom)
    if not p:
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "no-store"})


@app.post("/api/admin/souscriptions/{ref}/annuler", dependencies=[Depends(admin)])
def admin_annuler(ref: str):
    s = db.get_souscription(ref)
    if not s:
        raise HTTPException(404)
    db.update_souscription(ref, statut="annulee")
    db.log(ref, "annulee")
    return {"ok": True}


@app.post("/api/admin/souscriptions/{ref}/digitalia", dependencies=[Depends(admin)])
def admin_renvoyer_digitalia(ref: str):
    s = db.get_souscription(ref)
    if not s:
        raise HTTPException(404)
    if not config.DIGITALIA_WEBHOOK_URL:
        erreur("config", "DIGITALIA_WEBHOOK_URL n'est pas configuré.", 503)
    return {"ok": notifications.envoyer_digitalia(s)}


@app.post("/api/admin/digitalia/synchroniser", dependencies=[Depends(admin)])
def admin_synchroniser_tout():
    """Renvoie vers Digitalia toutes les souscriptions payées pas encore confirmées par Digitalia."""
    if not config.DIGITALIA_WEBHOOK_URL:
        erreur("config", "DIGITALIA_WEBHOOK_URL n'est pas configuré.", 503)
    ok = ko = 0
    for s in db.souscriptions_depuis(None, True, 5000):
        if notifications.envoyer_digitalia(s):
            ok += 1
        else:
            ko += 1
    return {"envoyees": ok, "erreurs": ko}


# ─────────────────────────── Interface Digitalia ───────────────────────────

def cle_digitalia(request: Request):
    cle = request.headers.get("x-api-key", "")
    if not config.DIGITALIA_API_KEY or not secrets.compare_digest(cle, config.DIGITALIA_API_KEY):
        raise HTTPException(401, {"code": "auth", "message": "Clé API invalide."})


@app.get("/api/digitalia/souscriptions", dependencies=[Depends(cle_digitalia)])
def digitalia_souscriptions(depuis: str | None = None, non_importees: bool = False, limite: int = 200):
    """Reprise des souscriptions par Digitalia.

    Sans paramètre : tout l'historique (par pages de `limite`). Pour la page suivante,
    repasser `depuis=<curseur>` reçu dans la réponse. `non_importees=true` ne renvoie que
    ce que Digitalia n'a pas encore confirmé.
    """
    limite = max(1, min(limite, 1000))
    lignes = db.souscriptions_depuis(depuis, non_importees, limite)
    fiches = [notifications.fiche_digitalia(s) for s in lignes]
    curseur = str(lignes[-1]["seq"]) if lignes else (depuis or "0")
    return {"souscriptions": fiches, "curseur": curseur, "suite": len(fiches) == limite}


@app.get("/api/digitalia/souscriptions/{ref}/{doc}.pdf", dependencies=[Depends(cle_digitalia)])
def digitalia_document(ref: str, doc: Literal["recu", "attestation"]):
    """Reçu (généré) ou attestation de la compagnie, pour le dossier client dans Digitalia."""
    s = db.get_souscription(ref)
    if not s or s["statut"] not in ("payee", "emise", "annulee"):
        raise HTTPException(404)
    if doc == "recu":
        return Response(documents.recu_pdf(s), media_type="application/pdf")
    if not s.get("attestation_fichier"):
        raise HTTPException(404)
    return FileResponse(config.DATA_DIR / "attestations" / s["attestation_fichier"], media_type="application/pdf")


@app.get("/api/digitalia/souscriptions/{ref}/pieces/{nom}", dependencies=[Depends(cle_digitalia)])
def digitalia_piece(ref: str, nom: str):
    """Copie de la CIN ou du passeport d'un assuré, pour le dossier client dans Digitalia."""
    s = db.get_souscription(ref)
    p = pieces.chemin(ref, nom) if s and s["statut"] in ("payee", "emise", "annulee") else None
    if not p:
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "no-store"})


class AccuseIn(BaseModel):
    references: list[str] = Field(min_length=1, max_length=1000)


@app.post("/api/digitalia/accuse", dependencies=[Depends(cle_digitalia)])
def digitalia_accuse(body: AccuseIn):
    """Digitalia confirme les souscriptions bien importées."""
    with db.tx() as c:
        n = 0
        for ref in body.references:
            n += c.execute("UPDATE souscriptions SET digitalia_importe_le=? WHERE ref=?", (db.now(), ref)).rowcount
    # Les copies de pièces d'identité sont maintenant dans Digitalia : on les efface du site.
    for ref in body.references:
        s = db.get_souscription(ref)
        if s and s["statut"] in ("payee", "emise", "annulee") and pieces.presentes(s):
            pieces.effacer(ref)
            db.log(ref, "pieces_effacees_apres_digitalia")
    return {"confirmees": n}


@app.get("/api/admin/devis", dependencies=[Depends(admin)])
def admin_devis():
    return {"devis": db.list_devis()}


class DevisStatut(BaseModel):
    statut: Literal["nouveau", "traite", "converti", "perdu"]


@app.post("/api/admin/devis/{i}", dependencies=[Depends(admin)])
def admin_devis_statut(i: int, body: DevisStatut):
    db.update_devis(i, body.statut)
    return {"ok": True}


@app.get("/api/admin/export.csv", dependencies=[Depends(admin)])
def admin_export():
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Référence", "Statut", "Formule", "Date d'effet", "Échéance", "Prime TTC", "Souscripteur", "Téléphone",
                "Nb assurés", "N° police", "Transaction", "Payée le", "Émise le"])
    for s in db.list_souscriptions(limit=100000):
        sous = s["assures"][0] if s["assures"] else {}
        w.writerow([s["ref"], s["statut"], s["produit"], s["date_effet"], s["date_echeance"],
                    f"{s['prime_ttc']:.2f}".replace(".", ","), f"{sous.get('nom', '')} {sous.get('prenom', '')}",
                    s["telephone"], len(s["assures"]), s.get("numero_police") or "", s.get("transaction_id") or "",
                    s.get("payee_le") or "", s.get("emise_le") or ""])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="souscriptions-{aujourdhui()}.csv"'})
