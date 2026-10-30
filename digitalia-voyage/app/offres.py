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
