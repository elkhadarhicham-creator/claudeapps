import os as _os

"""Catalogue des formules. Le prix est toujours recalculé côté serveur."""

OFFRES = {
    "FAM_MONDE_AN": {
        "code": "FAM_MONDE_AN",
        "nom": "Famille · Monde entier · 12 mois",
        "prix": 190.00,
        "mois": 12,
        "famille": True,
        "en_ligne": True,
        "zone": "Monde entier",
    },
    "IND_SCH": {"code": "IND_SCH", "nom": "Individuel · Schengen", "prix": None, "en_ligne": False},
    "OMRA": {"code": "OMRA", "nom": "Omra / Hajj", "prix": None, "en_ligne": False},
    "ETU": {"code": "ETU", "nom": "Étudiant à l'étranger", "prix": None, "en_ligne": False},
}

MAX_ENFANTS = 8
LIENS = ("Souscripteur", "Conjoint(e)", "Enfant")

# Conditions de la formule famille (à confirmer avec les conditions générales de la compagnie) :
# enfants de moins de 25 ans et souscripteur de 70 ans au plus, à la date d'effet.
AGE_MAX_ENFANT = int(_os.environ.get("AGE_MAX_ENFANT", "25"))        # strictement moins de
AGE_MAX_SOUSCRIPTEUR = int(_os.environ.get("AGE_MAX_SOUSCRIPTEUR", "70"))  # au plus


def age_a(naissance, date):
    return date.year - naissance.year - ((date.month, date.day) < (naissance.month, naissance.day))
