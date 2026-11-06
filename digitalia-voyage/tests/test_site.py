import re
import time
from datetime import date, timedelta

import faux_portail
import pytest
from fastapi.testclient import TestClient

from app import cmi, db, main, notifications

c = TestClient(main.app)
AUJ = main.aujourdhui()


COMPLEMENT = {"civilite": "Mme", "lieu_naissance": "RABAT", "situation_familiale": "Marié(e)", "ville": "RABAT",
              "code_postal": "10080", "profession": "Enseignante", "mutuelle": "CNOPS", "circonstances": "Aucune", "assistance_existante": "SANS"}


def souscription(**over):
    corps = {
        "offre": "FAM_MONDE_AN", "date_effet": (AUJ + timedelta(days=1)).isoformat(), "telephone": "06 12 34 56 78", "email": "sara@example.ma",
        "lang": "fr",
        "assures": [
            {"lien": "Souscripteur", "nom": "ALAMI", "prenom": "SARA", "naissance": "1990-01-01", "cin": "AB123456",
             "passeport": "", "exp_passeport": "", "adresse": "12 rue Fès, Agdal", **COMPLEMENT},
            {"lien": "Enfant", "nom": "ALAMI", "prenom": "ADAM", "naissance": "2015-05-05", "cin": "",
             "passeport": "XY998877", "exp_passeport": (AUJ + timedelta(days=900)).isoformat(), "adresse": ""},
        ],
        "consentements": {"conditions_generales": True, "exactitude": True, "loi_09_08": True},
    }
    corps.update(over)
    return c.post("/api/souscriptions", json=corps, headers={"x-forwarded-for": f"10.0.0.{time.time_ns() % 250}"})


def payer(r, decision="ok"):
    p = r.json()["paiement"]
    assert p["demo"] and p["action"].endswith("/paiement/demo")
    page = c.post("/paiement/demo", data=p["fields"])
    assert "3-D Secure" in page.text
    retour = c.post("/paiement/demo/decision", data={**p["fields"], "decision": decision})
    assert retour.status_code == 200
    ref = r.json()["ref"]
    for _ in range(50):  # l'envoi après paiement tourne en tâche de fond
        if db.get_souscription(ref)["statut"] != "attente_paiement":
            break
        time.sleep(0.05)
    champs = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', retour.text))
    return c.post("/paiement/retour", data=champs, follow_redirects=False)


def test_pages_publiques():
    assert "190 DH" in c.get("/").text
    assert c.get("/api/config").json()["paiement_demo"] is True
    assert "Content-Security-Policy" in c.get("/").headers


def test_hash_cmi_aller_retour():
    p = {"clientid": "X", "amount": "190.00", "oid": "A|B\\C", "rnd": "1"}
    p["HASH"] = cmi.compute_hash(p, cmi.store_key())
    assert cmi.verify(p)
    p["amount"] = "1.00"
    assert not cmi.verify(p)


def test_parcours_complet_paiement_suivi_documents():
    r = souscription()
    assert r.status_code == 200, r.text
    ref, tok = r.json()["ref"], r.json()["token"]
    # échéance = effet + 12 mois - 1 jour
    eff = AUJ + timedelta(days=1)
    attendu = date(eff.year + 1, eff.month, min(eff.day, 28 if eff.month == 2 else eff.day)) - timedelta(days=1)
    assert r.json()["date_echeance"] == attendu.isoformat()
    assert c.get(f"/api/suivi/{ref}?t={tok}").json()["statut"] == "attente_paiement"
    redir = payer(r)
    assert redir.status_code == 303 and redir.headers["location"] == f"/suivi/{ref}?t={tok}"
    s = c.get(f"/api/suivi/{ref}?t={tok}").json()
    assert s["statut"] == "payee" and s["recu"]
    pdf = c.get(f"/documents/{ref}/recu.pdf?t={tok}")
    assert pdf.content.startswith(b"%PDF")
    assert c.get(f"/documents/{ref}/recu.pdf?t=mauvais").status_code == 404
    # vérification publique par QR code
    from app import securite
    v = c.get(f"/verifier/{ref}?c={securite.code_verification(ref)}")
    assert "authentique" in v.text and "SARA" not in v.text  # prénoms masqués
    assert "non reconnu" in c.get(f"/verifier/{ref}?c=FAUX").text


def test_paiement_refuse_puis_relance():
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    payer(r, "ko")
    assert db.get_souscription(ref)["statut"] == "echec_paiement"
    assert c.post(f"/api/souscriptions/{ref}/paiement?t={tok}").status_code == 200


def test_callback_falsifie_rejete():
    r = souscription()
    f = dict(r.json()["paiement"]["fields"], ProcReturnCode="00", Response="Approved")
    assert c.post("/paiement/cmi/callback", data=f).text == "FAILURE"  # hash plus valable
    f["HASH"] = cmi.compute_hash(f, cmi.store_key())
    f["amount"] = "1.00"
    f["HASH"] = cmi.compute_hash(f, cmi.store_key())
    assert c.post("/paiement/cmi/callback", data=f).text == "FAILURE"  # montant incohérent
    assert db.get_souscription(r.json()["ref"])["statut"] == "attente_paiement"


@pytest.mark.parametrize("over,code", [
    ({"date_effet": (AUJ - timedelta(days=1)).isoformat()}, "date_effet"),
    ({"offre": "OMRA"}, "offre"),
    ({"consentements": {"conditions_generales": True, "exactitude": False, "loi_09_08": True}}, "consentements"),
    ({"telephone": "12"}, "telephone"),
])
def test_validations_serveur(over, code):
    r = souscription(**over)
    assert r.status_code == 422 and r.json()["detail"]["code"] == code


def test_devis():
    assert c.post("/api/devis", json={"offre": "OMRA", "nom": "B", "telephone": "0611223344"}).json()["ok"]


def connexion_admin():
    assert c.post("/api/admin/login", json={"mot_de_passe": "faux"}).status_code == 401
    assert c.post("/api/admin/login", json={"mot_de_passe": "motdepasse-test"}).status_code == 200


def test_admin_emission_manuelle_et_export():
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    payer(r)
    c.cookies.clear()
    assert c.get("/api/admin/tableau").status_code == 401
    connexion_admin()
    t = c.get("/api/admin/tableau?statut=payee").json()
    assert any(x["ref"] == ref for x in t["souscriptions"]) and t["stats"]["a_emettre"] >= 1
    d = c.get(f"/api/admin/souscriptions/{ref}").json()
    assert "token" not in d and d["assures"][0]["cin"] == "AB123456"
    e = c.post(f"/api/admin/souscriptions/{ref}/emettre", data={"numero_police": "POL-1"},
               files={"attestation": ("a.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert e.status_code == 200, e.text
    s = c.get(f"/api/suivi/{ref}?t={tok}").json()
    assert s["statut"] == "emise" and s["attestation"] and s["numero_police"] == "POL-1"
    assert c.get(f"/documents/{ref}/attestation.pdf?t={tok}").content.startswith(b"%PDF")
    assert ref in c.get("/api/admin/export.csv").text


def test_reprise_par_digitalia():
    refs = []
    for _ in range(3):
        r = souscription()
        payer(r)
        refs.append(r.json()["ref"])
    assert c.get("/api/digitalia/souscriptions").status_code == 401
    h = {"x-api-key": "cle-digitalia-test"}
    vus, curseur = [], None
    while True:  # pagination par curseur, 1 fiche par page
        p = c.get("/api/digitalia/souscriptions", params={"limite": 1, **({"depuis": curseur} if curseur else {})}, headers=h).json()
        vus += [f["reference"] for f in p["souscriptions"]]
        curseur = p["curseur"]
        if not p["suite"]:
            break
    assert set(refs) <= set(vus) and len(vus) == len(set(vus))
    fiche = c.get("/api/digitalia/souscriptions", headers=h).json()["souscriptions"][0]
    assert fiche["encaissement"]["mode"] == "carte_bancaire" and fiche["assures"]
    assert c.post("/api/digitalia/accuse", json={"references": refs}, headers=h).json()["confirmees"] == 3
    restants = c.get("/api/digitalia/souscriptions", params={"non_importees": True, "limite": 1000}, headers=h).json()
    assert not set(refs) & {f["reference"] for f in restants["souscriptions"]}


def test_robot_portail_mai():
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    payer(r)
    connexion_admin()
    res = c.post(f"/api/admin/souscriptions/{ref}/mai")
    assert res.status_code == 200, res.text
    assert res.json()["numero_police"] == "MAI-2026-000123"
    saisie = faux_portail.SAISIES[-1]
    assert saisie["nom"] == ["ALAMI"] and saisie["cin"] == ["AB123456"] and saisie["produit"] == ["fam"]
    assert saisie["b1Prenom"] == ["ADAM"] and saisie["b1Passeport"] == ["XY998877"]
    assert saisie["tarif"] == ["promo"]  # le tarif dont la prime affichée vaut 190 DH
    s = c.get(f"/api/suivi/{ref}?t={tok}").json()
    assert s["statut"] == "emise" and s["attestation"]


def test_passeport_facultatif():
    base = souscription().json()  # référence : la souscription type passe
    assert base["ref"]
    sans_piece = [
        {"lien": "Souscripteur", "nom": "ALAMI", "prenom": "SARA", "naissance": "1990-01-01", "cin": "AB123456",
         "passeport": "", "exp_passeport": "", "adresse": "12 rue Fès", **COMPLEMENT},
        {"lien": "Enfant", "nom": "ALAMI", "prenom": "ADAM", "naissance": "2015-05-05", "cin": "", "passeport": "",
         "exp_passeport": "", "adresse": ""},
    ]
    assert souscription(assures=sans_piece).status_code == 200  # enfant sans CIN ni passeport
    sans_piece[0]["cin"] = ""
    r = souscription(assures=sans_piece)
    assert r.status_code == 422 and "Souscripteur" in r.json()["detail"]["message"]


def test_lecture_pdf_et_photo(monkeypatch):
    """Le serveur accepte JPG, PNG et PDF ; un PDF part en bloc « document »."""
    from app import config, ocr
    envoye = []

    class Faux:
        class beta:
            class messages:
                @staticmethod
                def create(**kw):
                    envoye.append(kw["messages"][0]["content"][0])

                    class R:
                        stop_reason = "end_turn"
                        content = [type("T", (), {"type": "text", "text": '{"lisible":true,"type":"CIN","nom":"X","prenom":"Y",'
                                                  '"naissance":"1984-08-17","sexe":"M","cin":"A1","passeport":"",'
                                                  '"exp_passeport":"","adresse":""}'})()]
                    return R()
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(ocr, "_client", Faux())
    pdf = c.post("/api/ocr", files={"fichier": ("cin.pdf", b"%PDF-1.4 cin", "application/octet-stream")})
    assert pdf.json()["ok"] and envoye[-1]["type"] == "document"
    jpg = c.post("/api/ocr", files={"fichier": ("cin.jpg", b"\xff\xd8\xff photo", "image/jpeg")})
    assert jpg.json()["data"]["naissance"] == "1984-08-17" and envoye[-1]["type"] == "image"
    autre = c.post("/api/ocr", files={"fichier": ("cin.txt", b"texte", "text/plain")})
    assert autre.status_code == 422


def test_regles_injad_monde_famille_et_ages():
    eff = AUJ + timedelta(days=1)
    adulte = {"lien": "Souscripteur", "nom": "A", "prenom": "B", "naissance": f"{eff.year - 40}-01-01", "cin": "X1",
              "passeport": "", "exp_passeport": "", "adresse": "12 rue Fès", **COMPLEMENT}
    enfant = {"lien": "Enfant", "nom": "A", "prenom": "C", "naissance": f"{eff.year - 23}-01-01", "cin": "",
              "passeport": "", "exp_passeport": "", "adresse": ""}
    # 21-25 ans : couvert seulement s'il est étudiant au Maroc
    r = souscription(assures=[adulte, enfant])
    assert r.status_code == 422 and "étudiant" in r.json()["detail"]["message"].lower()
    assert souscription(assures=[adulte, dict(enfant, etudiant=True)]).json()["prime_ttc"] == 190.0
    # plus de 25 ans : refusé même étudiant
    r = souscription(assures=[adulte, dict(enfant, naissance=f"{eff.year - 27}-01-01", etudiant=True)])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "age"
    # un assuré de 70 ans ou plus : sur devis tant que le prix « + 70 ans » n'est pas fixé
    vieux = dict(adulte, naissance=f"{eff.year - 72}-01-01")
    r = souscription(assures=[vieux])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "age"
    # prise d'effet au plus tôt le lendemain
    assert souscription(date_effet=AUJ.isoformat()).json()["detail"]["code"] == "date_effet"

def test_duree_pluriannuelle_et_vehicules():
    from app.offres import VEHICULE2
    r = souscription(duree_ans=3)
    assert r.status_code == 200 and r.json()["prime_ttc"] == 3 * 190
    eff = AUJ + timedelta(days=1)
    attendu = date(eff.year + 3, eff.month, min(eff.day, 28 if eff.month == 2 else eff.day)) - timedelta(days=1)
    assert r.json()["date_echeance"] == attendu.isoformat()
    assert r.json()["paiement"]["fields"]["amount"] == "570.00"
    s = db.get_souscription(r.json()["ref"])
    assert s["duree_ans"] == 3 and "3 ans" in s["produit"]
    v1 = {"immatriculation": "12345-a-6", "marque": "dacia", "modele": "logan"}
    v2 = {"immatriculation": "6789-b-1", "marque": "renault", "modele": "clio"}
    # véhicule inclus sans surcoût
    assert souscription(vehicule=v1).json()["prime_ttc"] == 190.0
    # 2e véhicule : surprime par année, et il faut le premier
    assert souscription(vehicule2=v2).json()["detail"]["code"] == "vehicule"
    r = souscription(duree_ans=2, vehicule=v1, vehicule2=v2)
    assert r.json()["prime_ttc"] == 2 * 190 + 2 * VEHICULE2["prix_an"]
    s = db.get_souscription(r.json()["ref"])
    assert s["options"]["vehicule"]["immatriculation"] == "12345-A-6" and "2e véhicule" in s["produit"]
    assert souscription(duree_ans=5).json()["prime_ttc"] == 5 * 190
    assert souscription(duree_ans=6).status_code == 422


def test_champs_portail_mai_obligatoires_pour_le_souscripteur():
    assert souscription(email="").json()["detail"]["code"] == "email"
    for champ in ("lieu_naissance", "code_postal", "profession", "mutuelle", "circonstances", "assistance_existante"):
        r = c.post("/api/souscriptions", json={
            "offre": "FAM_MONDE_AN", "date_effet": (AUJ + timedelta(days=1)).isoformat(), "telephone": "0612345678",
            "email": "a@b.ma", "assures": [{"lien": "Souscripteur", "nom": "A", "prenom": "B", "naissance": "1990-01-01",
                                             "cin": "X1", "adresse": "rue", **{**COMPLEMENT, champ: ""}}],
            "consentements": {"conditions_generales": True, "exactitude": True, "loi_09_08": True}},
            headers={"x-forwarded-for": f"10.1.0.{time.time_ns() % 250}"})
        assert r.status_code == 422 and "à compléter" in r.json()["detail"]["message"], champ
    # les champs passent jusqu'à Digitalia et au robot MAI
    ref = souscription().json()["ref"]
    from app import db, mai
    v = mai.variables(db.get_souscription(ref))
    assert v["souscripteur.code_postal"] == "10080" and v["souscripteur.civilite"] == "Mme"
    assert v["telephone_mai"] == "0612345678" and v["duree_mai"] == "1 An"
    bad = {"lien": "Souscripteur", "nom": "A", "prenom": "B", "naissance": "1990-01-01", "cin": "123ABC", "adresse": "r", **COMPLEMENT}
    assert souscription(assures=[bad]).status_code == 422


def test_copie_cin_envoyee_a_digitalia_puis_effacee(monkeypatch):
    from app import ocr, pieces
    monkeypatch.setattr(ocr, "disponible", lambda: False)  # même sans lecture IA, la copie est gardée
    jpg = b"\xff\xd8\xff\xe0" + b"0" * 200
    r = c.post("/api/ocr", files={"fichier": ("cin.jpg", jpg, "image/jpeg")}, headers={"x-forwarded-for": "10.9.9.9"}).json()
    assert r["code"] == "indisponible" and pieces.ID_RE.match(r["piece_id"])
    assures = [{"lien": "Souscripteur", "nom": "ALAMI", "prenom": "SARA", "naissance": "1990-01-01", "cin": "AB123456",
                "adresse": "12 rue Fès", "pieces": [r["piece_id"], "inexistante-0000000000000000"], **COMPLEMENT}]
    s = souscription(assures=assures)
    ref = s.json()["ref"]
    h = {"x-api-key": "cle-digitalia-test"}
    assert c.get(f"/api/digitalia/souscriptions/{ref}/pieces/{ref}-1-souscripteur-1.jpg", headers=h).status_code == 404  # pas payée
    payer(s)
    fiche = notifications.fiche_digitalia(db.get_souscription(ref))
    (p,) = fiche["documents"]["pieces"]
    assert c.get(p["url"]).status_code == 401
    assert c.get(p["url"], headers=h).content == jpg
    assert c.get(f"/api/digitalia/souscriptions/{ref}/pieces/..%2F..%2Fdigitalia.db", headers=h).status_code == 404
    c.post("/api/digitalia/accuse", json={"references": [ref]}, headers=h)
    assert c.get(p["url"], headers=h).status_code == 404  # effacée du site après réception par Digitalia
    assert not notifications.fiche_digitalia(db.get_souscription(ref))["documents"]["pieces"]


def test_lecture_des_montants_du_portail():
    from app import mai
    assert mai.montant("190,00") == 190 and mai.montant("1 080,00 DH") == 1080 and mai.montant("674.33") == 674.33
    assert mai.montant("1.080,50") == 1080.5 and mai.montant("Prime : 350,00dh") == 350 and mai.montant("") is None
    s = {"prime_ttc": 580.0, "duree_ans": 2, "options": {"vehicule2": {"immatriculation": "1-A-2"}}}
    assert mai.prime_annuelle(s) == 190


def test_robot_mai_refuse_si_aucun_tarif_au_prix_paye(monkeypatch):
    from app import mai
    monkeypatch.setattr(mai, "prime_annuelle", lambda s: 175.0)  # ex. promotion pas encore ouverte sur le portail
    r = souscription()
    ref = r.json()["ref"]
    payer(r)
    connexion_admin()
    res = c.post(f"/api/admin/souscriptions/{ref}/mai")
    assert res.status_code == 502 and "Aucun tarif du portail à 175.00 DH" in res.text
    assert db.get_souscription(ref)["statut"] == "payee"  # rien d'émis : reste « à émettre »


def test_devis_automobile():
    assert c.get("/auto").status_code == 200 and "Devis assurance automobile" in c.get("/auto").text
    corps = {"type_vehicule": "Voiture de tourisme", "marque": "Dacia", "modele": "Logan", "immatriculation": "12345-A-6",
             "mise_en_circulation": "2019-03-15", "puissance_fiscale": 6, "carburant": "Diesel", "valeur": 90000,
             "usage": "Personnel", "nom": "ALAMI Karim", "naissance": "1985-05-05", "date_permis": "2005-06-01",
             "ville": "Rabat", "assureur_actuel": "Wafa", "echeance_actuelle": "", "sinistres_3_ans": "0",
             "formule": "Tous risques", "options": ["Assistance dépannage"], "telephone": "0612345678", "email": "",
             "message": ""}
    def h():
        return {"x-forwarded-for": f"10.7.{time.time_ns() % 250}.{time.time_ns() % 199}"}
    r = c.post("/api/devis/auto", json=corps, headers=h())
    assert r.status_code == 200, r.text
    assert c.post("/api/devis/auto", json={**corps, "date_permis": "1990-01-01"}, headers=h()).status_code == 422  # permis à 4 ans
    assert c.post("/api/devis/auto", json={**corps, "formule": "Inconnue"}, headers=h()).status_code == 422
    if c.get("/api/admin/devis").status_code != 200:  # session cabinet déjà ouverte par les tests précédents
        connexion_admin()
    d = next(x for x in c.get("/api/admin/devis").json()["devis"] if x["id"] == r.json()["id"])
    assert d["offre"] == "AUTO" and d["details"]["marque"] == "Dacia" and "Tous risques" in d["message"]


@pytest.fixture
def ycp(monkeypatch):
    """YouCan Pay activé avec des clés réelles factices ; les appels réseau sont simulés."""
    from app import config, youcanpay
    monkeypatch.setattr(config, "PAYMENT_PROVIDER", "youcanpay")
    monkeypatch.setattr(config, "YCP_PRIVATE_KEY", "pri_test_cle_privee")
    monkeypatch.setattr(config, "YCP_PUBLIC_KEY", "pub_test_cle_publique")
    appels = []

    class Rep:
        def __init__(self, code, data):
            self.status_code, self._d, self.text = code, data, str(data)

        def json(self):
            return self._d

    def post(url, data=None, **kw):
        appels.append((url, data))
        return Rep(200, {"transaction_id": "tx-1", "token": {"id": "tok_123"}})
    monkeypatch.setattr(youcanpay.httpx, "post", post)
    return appels


def _signe(corps: bytes, cle="pri_test_cle_privee"):
    import hashlib
    import hmac
    return hmac.new(cle.encode(), corps, hashlib.sha256).hexdigest()


def test_youcanpay_page_jeton_et_webhook(ycp, monkeypatch):
    import json as _json
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    assert r.json()["paiement"] == {"action": "/paiement/youcanpay", "fields": {"ref": ref, "t": tok}, "demo": False}
    assert c.post("/paiement/youcanpay", data={"ref": ref, "t": "faux"}).status_code == 404
    page = c.post("/paiement/youcanpay", data={"ref": ref, "t": tok})
    assert page.status_code == 200 and 'data-jeton="tok_123"' in page.text and "https://youcanpay.com/yp.js" in page.text
    assert "https://youcanpay.com" in page.headers["content-security-policy"]
    url, data = ycp[-1]
    assert url == "https://youcanpay.com/api/tokenize" and data["order_id"] == ref and data["amount"] == "19000"
    assert data["currency"] == "MAD" and data["pri_key"] == "pri_test_cle_privee"

    def evt(montant, nom="transaction.paid", sandbox=False):
        return _json.dumps({"id": "e1", "event_name": nom, "sandbox": sandbox, "payload": {
            "transaction": {"id": "tr-9", "amount": montant, "status": 1, "currency": "MAD", "order_id": ref},
            "payment_method": {"card": {"brand": "VISA", "last_digits": "4242", "country_code": "MA"}}}}).encode()
    corps = evt("19000")
    assert c.post("/paiement/youcanpay/webhook", content=corps, headers={"x-youcanpay-signature": "00"}).status_code == 403
    mauvais = evt("100")
    assert c.post("/paiement/youcanpay/webhook", content=mauvais, headers={"x-youcanpay-signature": _signe(mauvais)}).text == "montant"
    assert db.get_souscription(ref)["statut"] == "attente_paiement"
    test = evt("19000", sandbox=True)  # événement de test alors que les clés sont réelles : ignoré
    assert c.post("/paiement/youcanpay/webhook", content=test, headers={"x-youcanpay-signature": _signe(test)}).text == "ignore"
    rep = c.post("/paiement/youcanpay/webhook", content=corps, headers={"x-youcanpay-signature": _signe(corps)})
    assert rep.status_code == 200 and rep.text == "ok"
    s = db.get_souscription(ref)
    assert s["statut"] == "payee" and s["transaction_id"] == "tr-9" and s["paiement_detail"]["carte"] == "VISA **** 4242"
    c.post("/paiement/youcanpay/webhook", content=corps, headers={"x-youcanpay-signature": _signe(corps)})  # doublon sans effet
    assert sum(1 for e in db.journal(ref) if e["evenement"] == "payee") == 1


def test_youcanpay_confirmation_verifiee(ycp, monkeypatch):
    from app import youcanpay
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    lu = {"id": "tr-5", "status": "paid", "order_id": ref, "amount": {"amount": "100.00", "currency": "MAD"}}
    monkeypatch.setattr(youcanpay, "transaction", lambda tid: lu)
    corps = {"ref": ref, "t": tok, "transaction_id": "tr-5"}
    assert c.post("/api/paiement/youcanpay/confirmer", json=corps).json()["statut"] == "attente_paiement"  # mauvais montant
    lu["amount"]["amount"] = "190.00"
    assert c.post("/api/paiement/youcanpay/confirmer", json=corps).json()["statut"] == "payee"
    assert db.get_souscription(ref)["statut"] == "payee"


def test_youcanpay_mode_test(ycp, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "YCP_PRIVATE_KEY", "pri_sandbox_xyz")
    r = souscription()
    ref, tok = r.json()["ref"], r.json()["token"]
    page = c.post("/paiement/youcanpay", data={"ref": ref, "t": tok})
    assert "Mode test YouCan Pay" in page.text and ycp[-1][0] == "https://youcanpay.com/sandbox/api/tokenize"
    assert c.post("/api/paiement/youcanpay/confirmer", json={"ref": ref, "t": tok, "transaction_id": "tr-s"}).json()["statut"] == "payee"
