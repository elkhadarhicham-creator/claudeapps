"""Versement d'une souscription du site dans les tables de Digitalia.

MODÈLE À COMPLÉTER sur le PC du cabinet par Claude, qui connaît le schéma réel de Digitalia
(voir CONSIGNES_CLAUDE_PC.md). Copier ce fichier en integration_digitalia.py à côté du robot.

Le robot appelle integrer(conn, s) pour chaque souscription pas encore intégrée, dans une
transaction : si la fonction lève une exception, rien n'est écrit et l'erreur est notée dans
site_souscriptions.integration_erreur ; le robot réessaie au passage suivant.

Valeur de retour :
  False  -> pas encore (ex. contrat payé mais n° de police pas encore émis) : réessayé plus tard
  autre  -> intégrée (la ligne est marquée integre_le)

s : dict d'une ligne de site_souscriptions (reference, statut, numero_police, date_effet,
    date_echeance, prime_ttc, encaissement_date, transaction_cmi, souscripteur_cin, assures_json,
    fichier_attestation, …).
"""
import json


def integrer(conn, s: dict):
    if s["statut"] == "payee":
        return False  # on attend l'émission chez Maroc Assistance (n° de police)

    if s["statut"] == "annulee":
        # Règle Digitalia : une annulation est un avenant inverse (signe -1) lié à la quittance d'origine.
        raise NotImplementedError("Annulation : créer l'avenant inverse dans Digitalia")

    assures = json.loads(s["assures_json"])  # noqa: F841

    # 1. Client : chercher par CIN (puis passeport, puis nom + date de naissance), sinon créer
    #    avec le prochain code « AAAA-NNNNN ». Ne jamais créer de doublon de CIN.
    # 2. Police + quittance : compagnie Maroc Assistance, branche Assistance voyage,
    #    n° de police = s["numero_police"], effet / échéance, prime TTC, date de saisie = date du paiement,
    #    origine « site web », bénéficiaires = assures.
    # 3. Encaissement : reçu suivant dans la numérotation Digitalia, mode carte bancaire (CMI),
    #    montant = s["encaissement_montant"], date = s["encaissement_date"],
    #    référence = s["transaction_cmi"], affecté à la quittance créée en 2.
    # 4. Scan : copier s["fichier_attestation"] dans le dossier des scans, nommé par le n° de police.
    # 5. Journal des opérations : « robot site voyage ».
    raise NotImplementedError("À compléter avec le schéma réel de Digitalia")
