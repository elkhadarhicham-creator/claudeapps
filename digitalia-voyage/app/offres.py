import os as _os

"""Catalogue des formules. Le prix est toujours recalculé côté serveur."""

OFFRES = {
    "FAM_MONDE_AN": {
        "code": "FAM_MONDE_AN",
        "nom": "Famille · Monde entier",
        "prix": 190.00,
        "mois": 12,
        "famille": True,
        "en_ligne": True,
        "zone": "Monde entier",
        "durees_ans": [1, 2, 3, 4, 5],
    },
    "IND_SCH": {"code": "IND_SCH", "nom": "Individuel · Schengen", "prix": None, "en_ligne": False},
    "OMRA": {"code": "OMRA", "nom": "Omra / Hajj", "prix": None, "en_ligne": False},
    "ETU": {"code": "ETU", "nom": "Étudiant à l'étranger", "prix": None, "en_ligne": False},
}

# Option « Assistance auto au voyage » (dépannage, remorquage, rapatriement du véhicule)
# PRIX À CONFIRMER par le cabinet avec la compagnie : réglable par OPTION_AUTO_PRIX_AN.
OPTION_AUTO = {
    "code": "ASSIST_AUTO",
    "nom": "Assistance auto au voyage",
    "prix_an": float(_os.environ.get("OPTION_AUTO_PRIX_AN", "150")),
}

MAX_ENFANTS = 8
LIENS = ("Souscripteur", "Conjoint(e)", "Enfant")

# Conditions de la formule famille (à confirmer avec les conditions générales de la compagnie) :
# enfants de moins de 25 ans et souscripteur de 70 ans au plus, à la date d'effet.
AGE_MAX_ENFANT = int(_os.environ.get("AGE_MAX_ENFANT", "25"))        # strictement moins de
AGE_MAX_SOUSCRIPTEUR = int(_os.environ.get("AGE_MAX_SOUSCRIPTEUR", "70"))  # au plus


def libelle_duree(n: int) -> str:
    return f"{n} an" if n == 1 else f"{n} ans"


def tarif(offre: dict, duree_ans: int, option_auto: bool) -> float:
    """Prime TTC totale : prix annuel × nombre d'années, plus l'option auto éventuelle."""
    total = offre["prix"] * duree_ans
    if option_auto:
        total += OPTION_AUTO["prix_an"] * duree_ans
    return round(total, 2)


def age_a(naissance, date):
    return date.year - naissance.year - ((date.month, date.day) < (naissance.month, naissance.day))
