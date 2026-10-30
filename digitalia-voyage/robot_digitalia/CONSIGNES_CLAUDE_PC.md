# Brancher le site « Digitalia Assurance Voyage » sur Digitalia

*À coller dans Claude (Claude Code) sur le PC direction, dans le dossier de Digitalia (`Documents\pont_analysis`).*

---

Bonjour Claude. Le cabinet a un site de souscription en ligne d'assurance voyage : formule famille monde entier à 190 DH, paiement par carte CMI, contrat émis chez Maroc Assistance. Il faut que chaque souscription du site arrive automatiquement dans Digitalia, comme les données de MATU.

## Ce qui existe déjà

- `robot_site_voyage.py`, à placer dans le dossier de Digitalia. Il n'a besoin d'aucune bibliothèque. À chaque passage :
  - il récupère les souscriptions payées, émises ou annulées sur le site ;
  - il les enregistre dans la base de Digitalia, table **`site_souscriptions`** (une ligne par souscription) ;
  - il télécharge le reçu et l'attestation MAI dans `documents_site_voyage\` ;
  - il appelle `integration_digitalia.integrer(conn, ligne)` s'il existe.
- `integration_digitalia.exemple.py` : modèle de cette fonction, avec les étapes à suivre.

## Ce que je te demande

1. **Lis le code et le schéma de Digitalia** : clients, polices, quittances, encaissements, scans, journal des opérations, robot MATU.
2. **Écris `integration_digitalia.py`** à partir du modèle, en respectant les règles du cabinet :
   - **Client** : chercher par CIN, puis passeport, puis nom et date de naissance. Ne jamais créer de doublon de CIN (l'audit en a déjà trouvé 22). Sinon, créer le client avec le prochain code « AAAA-NNNNN » et le téléphone WhatsApp.
   - **Contrat** : seulement quand `statut = 'emise'`. Tant que le statut est `payee`, renvoyer `False` : le robot réessaiera.
     - Compagnie Maroc Assistance, branche Assistance voyage.
     - N° de contrôle = n° de police (règle des Risques Divers).
     - Effet et échéance du site, prime TTC 190 DH.
     - **Date de saisie = date du paiement**, puisque la production d'un jour se compte en date de saisie.
     - Origine « site web », assurés en bénéficiaires.
   - **Encaissement** :
     - reçu pris dans la suite normale des numéros (aucun trou : c'est un contrôle de l'audit) ;
     - mode « carte bancaire CMI », n° de transaction CMI en référence ;
     - **affecté à la quittance créée**, sans reproduire le bug d'Analysis qui affectait à l'ancienne quittance ;
     - il n'entre pas dans la caisse espèces de l'agent : c'est la banque qui verse.
   - **Annulation** (`statut = 'annulee'`) : avenant inverse (signe −1) lié à la quittance d'origine, jamais un simple statut. Si le client a payé, ristourne à rembourser par le CMI.
   - **Scan** : copier `fichier_attestation` dans le dossier des scans de Digitalia, nommé par le n° de police, pour que le contrôle « scan manquant » passe.
   - **Commission** : taux Maroc Assistance / Assistance voyage de la table des branches et catégories.
   - **Journal des opérations** : chaque écriture signée « robot site voyage ».
3. **Robotise** : lance `robot_site_voyage.py` toutes les 15 minutes, avec le même mécanisme que le robot MATU. Si MATU n'a pas de planificateur, utiliser le Planificateur de tâches Windows :
   `schtasks /Create /SC MINUTE /MO 15 /TN "Digitalia site voyage" /TR "python C:\…\robot_site_voyage.py"`
4. **Affiche dans Digitalia** :
   - une tuile « Site web » sur le tableau de bord : souscriptions du jour, montant, contrats payés en attente d'émission chez MAI ;
   - les lignes `integration_erreur` dans la page Contrôles, avec une alerte WhatsApp à Hicham si une souscription payée n'est pas émise après 24 h.
5. **Reprends l'historique** : `python robot_site_voyage.py --reprise`, d'abord sur une **copie** de la base, puis compare le nombre de souscriptions, le total des primes et les encaissements avec l'export Excel de l'espace cabinet du site (`/admin`).

## Option temps réel (Digitalia est joignable par Tailscale)

Digitalia est une application web sur le port 8080 (`http://100.66.131.67:8080`), joignable par le réseau Tailscale du cabinet. Si le serveur du site rejoint ce réseau Tailscale, le site peut **pousser** chaque souscription à Digitalia à la seconde, au lieu d'attendre le passage du robot :

1. Ajouter à Digitalia une route `POST /api/site-voyage/souscriptions`. Elle reçoit la fiche JSON (même format que le robot) et vérifie l'en-tête `X-Digitalia-Signature`, un HMAC-SHA256 du corps calculé avec la `SECRET_KEY` du site. Elle refuse tout envoi mal signé, puis enregistre la fiche dans `site_souscriptions` et appelle `integrer()`, comme le robot.
2. Sur le serveur du site, régler `DIGITALIA_WEBHOOK_URL=http://100.66.131.67:8080/api/site-voyage/souscriptions`.
3. Garder quand même le robot toutes les 15 minutes, en filet de sécurité si le PC était éteint au moment d'un envoi.

Ne jamais ouvrir Digitalia sur internet : elle doit rester derrière Tailscale.

## Réglages

Au premier lancement, le robot crée `robot_site_voyage.ini` :

```ini
[site]
url = https://adresse-du-site
cle_api = (valeur de DIGITALIA_API_KEY sur le serveur du site)

[digitalia]
base = C:\…\chemin\de\la\base\digitalia.db
dossier_documents = C:\…\documents_site_voyage
```

## Règles à respecter

- Ne jamais toucher à Analysis ni à sa base : lecture seule.
- Tester d'abord sur une copie de la base de Digitalia.
- Aucune correction de données existantes sans validation de Hicham.
