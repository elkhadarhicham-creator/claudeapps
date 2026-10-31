"""Tests de souscription de bout en bout, dans un vrai navigateur, comme un client.

Lance le site sur un port local (base temporaire, paiement CMI en démonstration, faux portail MAI),
puis déroule les parcours avec Chromium. Usage :
    .venv/bin/python tests/e2e_souscription.py [dossier_captures]
Affiche un compte rendu ligne par ligne et s'arrête au premier échec (code de sortie 1).
"""
import json
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import faux_portail  # noqa: E402

CAPTURES = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="e2e-captures-"))
CAPTURES.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix="e2e-digitalia-"))
PORTAIL = faux_portail.demarrer()
sc = json.loads((ROOT / "mai_scenario.exemple.json").read_text(encoding="utf-8"))
sc["connexion"][0]["url"] = PORTAIL + "/"
sc["connexion"][-1]["contient"] = "/accueil"
sc["souscription"][0]["url"] = PORTAIL + "/Souscriptions"
(TMP / "scenario.json").write_text(json.dumps(sc), encoding="utf-8")

with socket.socket() as s_:
    s_.bind(("127.0.0.1", 0))
    PORT = s_.getsockname()[1]
SITE = f"http://127.0.0.1:{PORT}"
import glob  # noqa: E402
_CHROME = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))
os.environ.update({
    "MAI_CHROMIUM_PATH": _CHROME[-1] if _CHROME else "",
    "DATA_DIR": str(TMP), "SITE_URL": SITE, "ADMIN_PASSWORD": "motdepasse-test",
    "DIGITALIA_API_KEY": "cle-digitalia-test", "SECRET_KEY": "secret-e2e",
    "MAI_MODE": "validation", "MAI_LOGIN": "cabinet", "MAI_PASSWORD": "secret", "MAI_SCENARIO": str(TMP / "scenario.json"),
})
for k in ("CMI_CLIENT_ID", "CMI_STORE_KEY", "ANTHROPIC_API_KEY", "DIGITALIA_WEBHOOK_URL", "WHATSAPP_TOKEN", "SMTP_HOST"):
    os.environ.pop(k, None)

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402

srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(100):
    try:
        httpx.get(SITE + "/api/config", timeout=1)
        break
    except httpx.HTTPError:
        time.sleep(0.1)

OK = []


def ok(txt):
    OK.append(txt)
    print("  ✔", txt, flush=True)


def fr(d: date) -> str:
    return d.strftime("%d/%m/%Y")


AUJ = date.today()
EFFET = AUJ + timedelta(days=3)


def image_cin() -> Path:
    """Fausse CIN (image JPEG) pour tester le dépôt de fichier."""
    p = TMP / "cin-test.jpg"
    if not p.exists():
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (860, 540), (220, 232, 225))
        d = ImageDraw.Draw(im)
        d.text((40, 40), "ROYAUME DU MAROC - CARTE NATIONALE D'IDENTITE (TEST)", fill=(0, 0, 0))
        d.text((40, 120), "ALAMI SARA  -  AB123456  -  01/01/1990", fill=(0, 0, 0))
        im.save(p, "JPEG")
    return p


def remplir_assure(page, i, nom, prenom, naissance, cin="", passeport="", etudiant=False):
    c = page.locator("#travList > .trav").nth(i)
    c.locator('[data-k="nom"]').fill(nom)
    c.locator('[data-k="prenom"]').fill(prenom)
    c.locator('[data-k="naissance"]').fill(naissance)
    if cin:
        c.locator('[data-k="cin"]').fill(cin)
    if passeport:
        c.locator('[data-k="passeport"]').fill(passeport)
    if etudiant:
        c.locator('[data-k="etudiant"]').check()
    return c


def infos_contrat(c, situation="Célibataire"):
    c.locator('[data-k="civilite"]').select_option("Mme")
    c.locator('[data-k="lieu_naissance"]').fill("RABAT")
    c.locator('[data-k="profession"]').fill("Enseignante")
    c.locator('[data-k="adresse"]').fill("12 rue de Fès, Agdal")
    c.locator('[data-k="ville"]').fill("RABAT")
    c.locator('[data-k="code_postal"]').fill("10080")
    c.locator('[data-k="mutuelle"]').select_option("CNOPS")
    c.locator('[data-k="assistance_existante"]').select_option("SANS")
    c.locator(".circ-sel").select_option("Aucune")
    if situation:
        c.locator('[data-k="situation_familiale"]').select_option(situation)


def etape1(page, duree=1, voiture=True, v2=False, tel="0612345678", email="sara.alami@example.ma"):
    page.goto(SITE + "/")
    page.locator(f'#dureePick input[value="{duree}"]').check(force=True)
    if voiture:
        page.fill("#vImmat", "12345-A-6")
        page.fill("#vMarque", "Dacia Logan")
    if v2:
        page.locator("#optV2").check(force=True)
        page.fill("#v2Immat", "6789-B-1")
        page.fill("#v2Marque", "Renault Clio")
    page.fill("#effet", fr(EFFET))
    page.locator("#effet").blur()
    page.fill("#tel", tel)
    page.fill("#email", email)
    page.click("#go2")


def payer(page, decision="ok"):
    page.click("#go4")
    page.click("#payBtn")
    page.wait_for_url("**/paiement/demo**")
    page.click(f'button[value="{decision}"]')
    if page.locator("text=Continuer").count():
        page.click("text=Continuer")
    page.wait_for_url("**/suivi/**")


def parcours_famille_complet(nav):
    print("\n1. Famille complète, 2 ans, 2 voitures, CIN jointe, téléphone (français)")
    page = nav.new_page(viewport={"width": 390, "height": 860})
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    etape1(page, duree=2, v2=True)
    expect(page.locator("#p2")).to_be_visible()
    ok("étape 1 : formule, 2 ans, 2 véhicules, date d'effet, WhatsApp, e-mail")
    # Souscripteur : dépôt d'une photo de CIN (sans lecture IA ici : la copie est quand même jointe)
    page.locator("#travList .scan input[type=file]").nth(1).set_input_files(str(image_cin()))
    expect(page.locator("#travList .pj").first).to_contain_text("1 copie jointe")
    ok("CIN jointe en fichier : « 1 copie jointe au dossier »")
    c = remplir_assure(page, 0, "ALAMI", "SARA", "01/01/1990", cin="AB123456")
    infos_contrat(c, situation=None)  # « Marié(e) » doit se mettre seul à l'ajout du conjoint
    page.click("#addConj")
    remplir_assure(page, 1, "ALAMI", "KARIM", "15/06/1987", cin="A654321")
    page.click("#addEnf")
    remplir_assure(page, 2, "ALAMI", "ADAM", "05/05/2015", passeport="XY998877")
    page.click("#addEnf")
    ag = AUJ.year - 23
    remplir_assure(page, 3, "ALAMI", "NOUR", f"01/01/{ag}", cin="AB987654", etudiant=True)
    titres = page.locator(".trav-head b").all_inner_texts()
    assert titres == ["Vous (souscripteur)", "Conjoint(e)", "Enfant 1", "Enfant 2"], titres
    assert page.locator('[data-k="situation_familiale"]').input_value() == "Marié(e)"
    assert page.locator("#addConj").is_hidden()
    ok("étape 2 : souscripteur + conjoint + 2 enfants (dont une étudiante de 23 ans) ; situation « Marié(e) » auto")
    page.screenshot(path=str(CAPTURES / "1-assures.png"), full_page=False)
    page.click("#go3")
    expect(page.locator("#p3")).to_be_visible()
    total = page.locator("#totalTxt").inner_text()
    assert "580,00" in total, total  # (190 + 100) × 2 ans
    recap = page.locator("#recapList").inner_text()
    assert "12345-A-6" in recap and "6789-B-1" in recap and "CNOPS" in recap and "Enseignante" in recap, recap
    ok(f"étape 3 : récapitulatif complet, total {total} = (190 + 100) × 2 ans")
    page.screenshot(path=str(CAPTURES / "2-recap.png"))
    page.click("#go4")
    expect(page.locator("#e3")).to_be_visible()
    ok("consentements obligatoires : paiement bloqué tant que les 3 cases ne sont pas cochées")
    for k in ("c1", "c2", "c3"):
        page.check("#" + k)
    payer(page)
    expect(page.locator("#etat")).to_contain_text("Paiement reçu", timeout=10000)
    ref = page.locator("#ref").inner_text().split()[-1]
    ok(f"paiement par carte (passerelle CMI de démonstration) accepté → suivi {ref} « Paiement reçu »")
    page.screenshot(path=str(CAPTURES / "3-suivi.png"))
    recu = page.locator("#dlRecu").get_attribute("href")
    r = page.request.get(SITE + recu)
    assert r.ok and r.body()[:4] == b"%PDF"
    ok("reçu PDF téléchargé depuis la page de suivi")
    s = db.get_souscription(ref)
    assert s["statut"] == "payee" and s["prime_ttc"] == 580 and s["duree_ans"] == 2
    a0 = s["assures"][0]
    assert a0["code_postal"] == "10080" and a0["mutuelle"] == "CNOPS" and len(a0["pieces"]) == 1
    assert [a["lien"] for a in s["assures"]] == ["Souscripteur", "Conjoint(e)", "Enfant", "Enfant"]
    ok("en base : 580 DH, 2 ans, 4 assurés, infos du contrat, 1 copie de CIN rattachée")
    assert not erreurs, erreurs
    ok("aucune erreur JavaScript")
    page.close()
    return ref


def parcours_refus_puis_relance(nav):
    print("\n2. Paiement refusé puis relancé")
    page = nav.new_page(viewport={"width": 1280, "height": 900})
    etape1(page, voiture=False, tel="0661223344", email="omar@example.ma")
    c = remplir_assure(page, 0, "BENNANI", "OMAR", "10/10/1980", cin="BK112233")
    infos_contrat(c)
    page.click("#go3")
    expect(page.locator("#p3")).to_be_visible(timeout=3000) if not page.locator("#e2").is_visible() else (_ for _ in ()).throw(AssertionError(page.locator("#e2").inner_text()))
    assert "190,00" in page.locator("#totalTxt").inner_text()
    ok("famille sans voiture, 1 an : total 190,00 DH (sur ordinateur)")
    for k in ("c1", "c2", "c3"):
        page.check("#" + k)
    payer(page, "ko")
    expect(page.locator("#retry")).to_be_visible(timeout=10000)
    ok("paiement refusé : le suivi propose « Réessayer le paiement »")
    page.click("#retry")
    page.wait_for_url("**/paiement/demo**")
    page.click('button[value="ok"]')
    if page.locator("text=Continuer").count():
        page.click("text=Continuer")
    page.wait_for_url("**/suivi/**")
    expect(page.locator("#etat")).to_contain_text("Paiement reçu", timeout=10000)
    ok("nouvel essai accepté → « Paiement reçu »")
    page.close()


def controles(nav):
    print("\n3. Contrôles du formulaire")
    page = nav.new_page(viewport={"width": 390, "height": 860})
    page.goto(SITE + "/")
    page.fill("#tel", "0612345678")
    page.click("#go2")
    expect(page.locator("#e1")).to_contain_text("e-mail")
    ok("e-mail manquant : refusé")
    page.fill("#email", "x@example.ma")
    page.click("#go2")
    c = remplir_assure(page, 0, "TEST", "ESSAI", "01/01/1985", cin="123ABC")
    infos_contrat(c)
    page.click("#go3")
    expect(page.locator("#e2")).to_contain_text("CIN")
    ok("CIN au mauvais format (123ABC) : refusée")
    c.locator('[data-k="cin"]').fill("AB123456")
    c.locator('[data-k="profession"]').fill("")
    page.click("#go3")
    expect(page.locator("#e2")).to_contain_text("informations pour le contrat")
    ok("profession manquante : refusée")
    c.locator('[data-k="profession"]').fill("Commerçant")
    page.click("#addEnf")
    remplir_assure(page, 1, "TEST", "GRAND", f"01/01/{AUJ.year - 23}")
    page.click("#go3")
    expect(page.locator("#e2")).to_contain_text("Étudiant")
    ok("enfant de 23 ans non étudiant : refusé")
    page.locator("#travList > .trav").nth(1).locator('[data-k="naissance"]').fill(f"01/01/{AUJ.year - 27}")
    page.click("#go3")
    expect(page.locator("#e2")).to_contain_text("25 ans")
    ok("enfant de 27 ans : refusé (formule individuelle sur devis)")
    page.locator("#travList > .trav").nth(1).locator("button").click()
    page.locator("#travList > .trav").nth(0).locator('[data-k="naissance"]').fill("01/01/1950")
    page.click("#go3")
    expect(page.locator("#e2")).to_contain_text("70 ans")
    ok("assuré de plus de 70 ans : orienté vers un devis WhatsApp")
    page.goto(SITE + "/")
    page.fill("#effet", fr(AUJ))
    page.fill("#tel", "0612345678")
    page.fill("#email", "x@example.ma")
    page.click("#go2")
    p2_visible = page.locator("#p2").is_visible()
    effet = page.locator("#effet").input_value()
    assert not p2_visible or effet != fr(AUJ), "date d'effet du jour acceptée"
    ok("date d'effet aujourd'hui : refusée ou repoussée au lendemain")
    page.close()


def parcours_arabe(nav):
    print("\n4. Souscription en arabe")
    page = nav.new_page(viewport={"width": 390, "height": 860})
    page.goto(SITE + "/")
    page.click('.lang button[data-l="ar"]')
    assert page.evaluate("document.documentElement.dir") == "rtl"
    # Chiffres jamais à l'envers : dans « 350 000 DH », le 3 est à gauche du D
    pos = page.evaluate("""() => {const el=[...document.querySelectorAll('.perks li span')].find(e=>/DH/.test(e.textContent));
      const n=[...el.childNodes].find(x=>x.nodeType===3);const t=n.data;const r=(i)=>{const g=document.createRange();g.setStart(n,i);g.setEnd(n,i+1);return g.getBoundingClientRect().x};
      return [r(t.indexOf('3')), r(t.indexOf('D'))]}""")
    assert pos[0] < pos[1], pos
    ok("arabe : sens de lecture inversé, « 350 000 DH » dans le bon ordre")
    page.fill("#effet", fr(EFFET))
    page.fill("#tel", "0699887766")
    page.fill("#email", "fatima@example.ma")
    page.click("#go2")
    c = remplir_assure(page, 0, "IDRISSI", "FATIMA", "03/03/1975", cin="D445566")
    infos_contrat(c)
    page.click("#go3")
    for k in ("c1", "c2", "c3"):
        page.check("#" + k)
    page.screenshot(path=str(CAPTURES / "4-arabe-recap.png"))
    payer(page)
    expect(page.locator("#contenu")).to_be_visible(timeout=10000)
    ok("parcours complet en arabe jusqu'au paiement")
    page.close()


def cabinet_et_digitalia(nav, ref):
    print("\n5. Espace cabinet, émission chez MAI (faux portail), Digitalia")
    page = nav.new_page(viewport={"width": 1280, "height": 900})
    page.goto(SITE + "/admin")
    page.fill('input[type="password"]', "motdepasse-test")
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    d = page.request.get(f"{SITE}/api/admin/souscriptions/{ref}").json()
    assert d["statut"] == "payee" and len(d["pieces_presentes"]) == 1
    piece = page.request.get(f"{SITE}/api/admin/souscriptions/{ref}/pieces/{d['pieces_presentes'][0]['nom']}")
    assert piece.ok and piece.body()[:2] == b"\xff\xd8"
    ok("espace cabinet : souscription payée visible, copie de la CIN consultable")
    r = page.request.post(f"{SITE}/api/admin/souscriptions/{ref}/mai").json()
    assert r.get("numero_police") == "MAI-2026-000123", r
    saisie = faux_portail.SAISIES[-1]
    assert saisie["tarif"] == ["promo"] and saisie["cin"] == ["AB123456"], saisie
    ok("robot MAI : contrat saisi, tarif choisi = celui à 190 DH, n° de police MAI-2026-000123 relevé")
    s = db.get_souscription(ref)
    assert s["statut"] == "emise" and s["attestation_fichier"]
    ok("statut « émise », attestation récupérée")
    page.close()

    # Robot Digitalia côté cabinet : récupère la fiche, le reçu, l'attestation et la copie de la CIN
    sys.path.insert(0, str(ROOT / "robot_digitalia"))
    import robot_site_voyage as robot
    base = TMP / "cabinet.db"
    docs = TMP / "documents_site_voyage"
    bilan = robot.passage({"url": SITE, "cle": "cle-digitalia-test", "base": str(base), "docs": str(docs)})
    conn = sqlite3.connect(base)
    ligne = conn.execute("SELECT statut, numero_police, prime_ttc, fichiers_pieces, fichier_attestation FROM site_souscriptions "
                         "WHERE reference=?", (ref,)).fetchone()
    assert ligne and ligne[0] == "emise" and ligne[1] == "MAI-2026-000123" and ligne[2] == 580, ligne
    pj = json.loads(ligne[3])
    assert len(pj) == 1 and Path(pj[0]).read_bytes()[:2] == b"\xff\xd8" and Path(ligne[4]).exists()
    ok(f"robot Digitalia : {bilan['recues']} souscriptions reçues ; fiche, attestation et copie de CIN enregistrées")
    h = {"x-api-key": "cle-digitalia-test"}
    rest = httpx.get(f"{SITE}/api/admin/souscriptions/{ref}", cookies=None)
    assert rest.status_code in (401, 403)
    fiche = httpx.get(f"{SITE}/api/digitalia/souscriptions", params={"limite": 500}, headers=h).json()
    f = next(x for x in fiche["souscriptions"] if x["reference"] == ref)
    assert f["documents"]["pieces"] == []
    ok("après l'accusé de Digitalia, la copie de la CIN est effacée du site")


def main():
    print(f"Site de test : {SITE}  ·  captures : {CAPTURES}")
    with sync_playwright() as p:
        import glob
        chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))
        nav = p.chromium.launch(**({"executable_path": chrome[-1]} if chrome and not os.environ.get("E2E_CHROME_PAR_DEFAUT") else {}))
        ref = parcours_famille_complet(nav)
        parcours_refus_puis_relance(nav)
        controles(nav)
        parcours_arabe(nav)
        cabinet_et_digitalia(nav, ref)
        nav.close()
    print(f"\nRÉSULTAT : {len(OK)} vérifications réussies, 0 échec.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\n  ✘ ÉCHEC : {type(e).__name__}: {e}")
        sys.exit(1)
