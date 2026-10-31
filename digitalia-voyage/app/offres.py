"""Catalogue des formules. Le prix est toujours recalculé côté serveur.

Formule en ligne : INJAD MONDE de Maroc Assistance Internationale
(notice d'information et conditions générales fournies par la compagnie) :
  - forfait familial annuel + 1 véhicule (moins de 70 ans) : 890 DH TTC
  - prime familiale + 70 ans : 1 080 DH TTC
  - surprime deuxième véhicule : 100 DH TTC
Les montants restent réglables par variables d'environnement si le barème change.
"""
import os as _os


def _prix(nom: str, defaut: str) -> float:
    return float(_os.environ.get(nom, defaut))


OFFRES = {
    "FAM_MONDE_AN": {
        "code": "FAM_MONDE_AN",
        "nom": "Injad Monde · Famille + 1 véhicule",
        "compagnie_produit": "INJAD MONDE",
        "prix": _prix("PRIX_INJAD_FAMILLE", "890"),          # forfait annuel, assurés de moins de 70 ans
        "prix_70": _prix("PRIX_INJAD_FAMILLE_70", "1080"),   # dès qu'un assuré a 70 ans ou plus
        "famille": True,
        "en_ligne": True,
        "zone": "Monde entier, y compris le Maroc",
        "durees_ans": [1, 2, 3, 4, 5],
    },
    "IND_SCH": {"code": "IND_SCH", "nom": "Individuel · Schengen", "prix": None, "en_ligne": False},
    "OMRA": {"code": "OMRA", "nom": "Omra / Hajj", "prix": None, "en_ligne": False},
    "ETU": {"code": "ETU", "nom": "Étudiant à l'étranger", "prix": None, "en_ligne": False},
}

# Surprime pour un deuxième véhicule inscrit au contrat
VEHICULE2 = {"code": "VEHICULE2", "nom": "2e véhicule", "prix_an": _prix("PRIX_INJAD_VEHICULE2", "100")}

MAX_ENFANTS = 8
LIENS = ("Souscripteur", "Conjoint(e)", "Enfant")

# Bénéficiaires Injad Monde : enfants célibataires à charge de moins de 21 ans,
# ou ayant au plus 25 ans s'ils poursuivent leurs études au Maroc.
AGE_MAX_ENFANT = int(_os.environ.get("AGE_MAX_ENFANT", "21"))            # strictement moins de
AGE_MAX_ENFANT_ETUDIANT = int(_os.environ.get("AGE_MAX_ENFANT_ETUDIANT", "25"))  # au plus
AGE_SENIOR = int(_os.environ.get("AGE_SENIOR", "70"))                    # à partir de : prime « + 70 ans »


def libelle_duree(n: int) -> str:
    return f"{n} an" if n == 1 else f"{n} ans"


def prix_annuel(offre: dict, senior: bool) -> float:
    return offre.get("prix_70") or offre["prix"] if senior else offre["prix"]


def tarif(offre: dict, duree_ans: int, senior: bool, deuxieme_vehicule: bool) -> float:
    """Prime TTC totale : prime annuelle × nombre d'années, plus la surprime du 2e véhicule."""
    total = prix_annuel(offre, senior) * duree_ans
    if deuxieme_vehicule:
        total += VEHICULE2["prix_an"] * duree_ans
    return round(total, 2)


def age_a(naissance, date):
    return date.year - naissance.year - ((date.month, date.day) < (naissance.month, naissance.day))
