"""Liaison avec le portail intermédiaires de Maroc Assistance (portail.mai.ma).

Le portail n'offre pas d'API publique : un robot (navigateur Chromium piloté par
Playwright) se connecte avec les identifiants du cabinet, saisit la souscription,
relève le numéro de police et télécharge l'attestation.

Les écrans du portail sont décrits dans un fichier de scénario JSON
(mai_scenario.json, voir mai_scenario.exemple.json). Pour l'écrire, enregistrer
une saisie une fois avec :   playwright codegen https://portail.mai.ma/Souscriptions
puis reporter les sélecteurs obtenus dans le scénario.

Modes (variable MAI_MODE) :
  manuel     - pas de robot ; le conseiller saisit sur le portail (fiche à copier dans l'admin)
  validation - le conseiller contrôle la souscription puis clique « Émettre via le portail » (défaut)
  auto       - le robot émet le contrat dès la confirmation du paiement
"""
import json
import logging
import re
import threading
from datetime import date
from pathlib import Path

from . import config, db

log = logging.getLogger("digitalia.mai")

MODE = config.env("MAI_MODE", "validation")
LOGIN = config.env("MAI_LOGIN")
PASSWORD = config.env("MAI_PASSWORD")
SCENARIO = Path(config.env("MAI_SCENARIO", str(config.BASE_DIR / "mai_scenario.json")))
CHROMIUM = config.env("MAI_CHROMIUM_PATH")  # facultatif : chemin d'un Chromium déjà installé
DRY_RUN = config.env("MAI_DRY_RUN", "false").lower() == "true"  # n'exécute pas les étapes "final"
TIMEOUT_MS = int(config.env("MAI_TIMEOUT_MS", "30000") or 30000)
# Tarif à sélectionner sur le portail (relevé du 31/10/2026 : prime client 350 DH, net à payer 265,19 DH)
TARIF_LIBELLE = config.env("MAI_TARIF_LIBELLE", "NV Tarif IM <70 ANS à 350,00dh")
DOSSIER = config.DATA_DIR / "mai"
DOSSIER.mkdir(exist_ok=True)

_verrou = threading.Lock()  # un seul robot à la fois sur le compte du cabinet


class ErreurPortail(Exception):
    pass


def configure() -> bool:
    return MODE in ("validation", "auto") and bool(LOGIN and PASSWORD) and SCENARIO.exists()


def etat() -> dict:
    return {"mode": MODE, "configure": configure(), "identifiants": bool(LOGIN and PASSWORD),
            "scenario": SCENARIO.exists(), "essai_a_blanc": DRY_RUN}


def _fr(d: str | None) -> str:
    return date.fromisoformat(d).strftime("%d/%m/%Y") if d else ""


def _tel_mai(tel: str) -> str:
    d = "".join(ch for ch in tel if ch.isdigit())
    if d.startswith("00212"):
        d = "0" + d[5:]
    elif d.startswith("212"):
        d = "0" + d[3:]
    return d


def variables(s: dict) -> dict:
    sous = next((a for a in s["assures"] if a["lien"] == "Souscripteur"), s["assures"][0])
    v = {
        "ref": s["ref"], "telephone": s["telephone"], "email": s.get("email") or "",
        "date_effet": s["date_effet"], "date_effet_fr": _fr(s["date_effet"]),
        "date_echeance": s["date_echeance"], "date_echeance_fr": _fr(s["date_echeance"]),
        "prime": f"{s['prime_ttc']:.2f}", "nb_assures": str(len(s["assures"])),
        "duree_ans": str(s.get("duree_ans") or 1),
        "duree_mai": "1 An" if (s.get("duree_ans") or 1) == 1 else f"{s.get('duree_ans')} Ans",  # libellé du portail
        "telephone_mai": _tel_mai(s["telephone"]),  # 10 chiffres commençant par 0
        "tarif_mai": TARIF_LIBELLE,  # tarif à choisir sur le portail
        "MAI_LOGIN": LOGIN, "MAI_PASSWORD": PASSWORD,
    }
    for cle in ("vehicule", "vehicule2"):
        for k, val in ((s.get("options") or {}).get(cle) or {}).items():
            v[f"{cle}.{k}"] = val or ""
    for k, val in sous.items():
        v[f"souscripteur.{k}"] = val or ""
    v["souscripteur.naissance_fr"] = _fr(sous.get("naissance"))
    return v


def _variables_assure(a: dict, i: int) -> dict:
    v = {f"assure.{k}": (val or "") for k, val in a.items()}
    v["assure.naissance_fr"] = _fr(a.get("naissance"))
    v["assure.exp_passeport_fr"] = _fr(a.get("exp_passeport"))
    v["i"] = str(i)
    v["n"] = str(i + 1)
    return v


_PH = re.compile(r"\{([A-Za-z_][\w.]*)\}")


def remplir(texte: str, v: dict) -> str:
    return _PH.sub(lambda m: str(v.get(m.group(1), m.group(0))), texte)


def _executer(page, etapes: list, v: dict, s: dict, resultat: dict) -> None:
    for e in etapes:
        a = e["action"]
        if e.get("final") and DRY_RUN:
            log.info("[essai à blanc] étape finale ignorée : %s", e)
            continue
        sel = remplir(e["selector"], v) if "selector" in e else None
        val = remplir(str(e.get("valeur", "")), v)
        if a == "goto":
            page.goto(remplir(e["url"], v))
        elif a == "fill":
            page.fill(sel, val)
        elif a == "type":
            page.locator(sel).press_sequentially(val, delay=40)
        elif a == "select":
            page.select_option(sel, label=val) if e.get("par") == "libelle" else page.select_option(sel, val)
        elif a == "check":
            page.check(sel)
        elif a == "click":
            page.click(sel)
        elif a == "press":
            page.press(sel, e.get("touche", "Enter"))
        elif a == "wait":
            page.wait_for_selector(sel)
        elif a == "wait_url":
            page.wait_for_url(re.compile(re.escape(e["contient"])))
        elif a == "pause":
            page.wait_for_timeout(int(e.get("ms", 500)))
        elif a == "repeter":
            # ex. pour chaque assuré : clic sur « Ajouter un bénéficiaire » puis saisie
            for i, assure in enumerate(s["assures"][e.get("debut", 0):], e.get("debut", 0)):
                _executer(page, e["etapes"], {**v, **_variables_assure(assure, i)}, s, resultat)
        elif a == "lire":
            txt = page.locator(sel).first.inner_text().strip()
            if e.get("regex"):
                m = re.search(e["regex"], txt)
                txt = m.group(1) if m and m.groups() else (m.group(0) if m else "")
            if not txt:
                raise ErreurPortail(f"Valeur introuvable : {e['nom']}")
            resultat[e["nom"]] = txt
        elif a == "telecharger":
            with page.expect_download(timeout=TIMEOUT_MS) as dl:
                page.click(sel)
            dest = config.DATA_DIR / "attestations" / f"{s['ref']}.pdf"
            dl.value.save_as(dest)
            if not dest.read_bytes()[:4] == b"%PDF":
                raise ErreurPortail("Le fichier téléchargé n'est pas un PDF.")
            resultat["attestation_fichier"] = dest.name
        else:
            raise ErreurPortail(f"Action inconnue dans le scénario : {a}")


def emettre(ref: str) -> dict:
    """Saisit la souscription sur le portail et récupère police + attestation. Ne lève pas d'exception."""
    s = db.get_souscription(ref)
    if not s or s["statut"] != "payee":
        return {"ok": False, "erreur": "La souscription doit être payée et non encore émise."}
    if not configure():
        return {"ok": False, "erreur": "Robot portail MAI non configuré (MAI_LOGIN, MAI_PASSWORD, mai_scenario.json)."}
    from playwright.sync_api import Error as PWError
    from playwright.sync_api import sync_playwright

    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    v = variables(s)
    resultat: dict = {}
    with _verrou:
        db.log(ref, "mai_debut", {"essai_a_blanc": DRY_RUN})
        try:
            with sync_playwright() as p:
                nav = p.chromium.launch(**({"executable_path": CHROMIUM} if CHROMIUM else {}))
                ctx = nav.new_context(accept_downloads=True, locale="fr-FR")
                page = ctx.new_page()
                page.set_default_timeout(TIMEOUT_MS)
                try:
                    for bloc in ("connexion", "souscription", "resultat", "attestation"):
                        _executer(page, scenario.get(bloc, []), v, s, resultat)
                except (PWError, ErreurPortail) as e:
                    capture = DOSSIER / f"{ref}-erreur.png"
                    try:
                        page.screenshot(path=str(capture), full_page=True)
                    except PWError:
                        pass
                    raise ErreurPortail(str(e).splitlines()[0][:300]) from e
                finally:
                    nav.close()
        except (PWError, ErreurPortail) as e:
            db.log(ref, "mai_erreur", {"erreur": str(e)})
            log.error("Robot MAI %s : %s", ref, e)
            return {"ok": False, "erreur": str(e)}

    if DRY_RUN:
        db.log(ref, "mai_essai_a_blanc_ok", resultat)
        return {"ok": True, "essai_a_blanc": True, **resultat}
    police = resultat.get("numero_police")
    if not police:
        db.log(ref, "mai_erreur", {"erreur": "numéro de police non relevé"})
        return {"ok": False, "erreur": "Saisie faite mais numéro de police non relevé : vérifier sur le portail."}
    champs = {"numero_police": police, "statut": "emise", "emise_le": db.now()}
    if resultat.get("attestation_fichier"):
        champs["attestation_fichier"] = resultat["attestation_fichier"]
    db.update_souscription(ref, **champs)
    db.log(ref, "emise", {"police": police, "par": "robot_mai"})
    from . import notifications
    notifications.apres_emission(ref)
    return {"ok": True, "numero_police": police, "attestation": bool(resultat.get("attestation_fichier"))}
