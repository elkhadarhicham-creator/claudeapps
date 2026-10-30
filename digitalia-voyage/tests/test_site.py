import re
import time
from datetime import date, timedelta

import faux_portail
import pytest
from fastapi.testclient import TestClient

from app import cmi, db, main

c = TestClient(main.app)
AUJ = main.aujourdhui()


def souscription(**over):
    corps = {
        "offre": "FAM_MONDE_AN", "date_effet": AUJ.isoformat(), "telephone": "06 12 34 56 78", "email": "",
        "lang": "fr",
        "assures": [
            {"lien": "Souscripteur", "nom": "ALAMI", "prenom": "SARA", "naissance": "1990-01-01", "cin": "AB123456",
             "passeport": "", "exp_passeport": "", "adresse": "Rabat"},
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
    attendu = date(AUJ.year + 1, AUJ.month, min(AUJ.day, 28 if AUJ.month == 2 else AUJ.day)) - timedelta(days=1)
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
    s = c.get(f"/api/suivi/{ref}?t={tok}").json()
    assert s["statut"] == "emise" and s["attestation"]


def test_passeport_facultatif():
    base = souscription().json()  # référence : la souscription type passe
    assert base["ref"]
    sans_piece = [
        {"lien": "Souscripteur", "nom": "ALAMI", "prenom": "SARA", "naissance": "1990-01-01", "cin": "AB123456",
         "passeport": "", "exp_passeport": "", "adresse": ""},
        {"lien": "Enfant", "nom": "ALAMI", "prenom": "ADAM", "naissance": "2015-05-05", "cin": "", "passeport": "",
         "exp_passeport": "", "adresse": ""},
    ]
    assert souscription(assures=sans_piece).status_code == 200  # enfant sans CIN ni passeport
    sans_piece[0]["cin"] = ""
    r = souscription(assures=sans_piece)
    assert r.status_code == 422 and "Souscripteur" in r.json()["detail"]["message"]
