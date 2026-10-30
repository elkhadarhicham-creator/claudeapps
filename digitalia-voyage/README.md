# Digitalia Assurance Voyage

Site de souscription en ligne de l'assurance voyage famille (190 DH / an) d'Assurances Elkhaddar, Rabat et Salé.

## Ce que fait le site

| Fonction | Détail |
|---|---|
| Souscription en ligne | Formule, assurés, vérification, paiement. Français, arabe et darija (sens de lecture inversé). |
| Lecture des pièces d'identité | Photo de la CIN ou du passeport, champs remplis automatiquement par l'IA (Claude). La photo n'est jamais conservée. |
| Paiement par carte | Passerelle **CMI** (3-D Secure, cartes marocaines et internationales). Le site ne voit jamais le numéro de carte ; seul le rappel signé du CMI valide un paiement. Mode démonstration tant que le contrat commerçant n'est pas signé. |
| Reçu PDF | Généré au paiement, avec **QR code de vérification** pour les consulats (`/verifier/<réf>`). |
| Suivi client | Lien personnel `/suivi/<réf>?t=…` : état en direct, reçu, attestation, relance du paiement en cas d'échec. |
| Portail Maroc Assistance | Robot qui saisit le contrat sur **portail.mai.ma**, relève le n° de police et télécharge l'attestation. |
| Liaison Digitalia | Envoi de chaque fiche au paiement et à l'émission, plus une API de reprise de toutes les souscriptions. |
| Espace cabinet `/admin` | Chiffre d'affaires du jour et du mois, contrats à émettre, fiche avec boutons « Copier », émission, dépôt de l'attestation, devis, export Excel. |
| Devis | Formules Schengen individuel, Omra/Hajj et Étudiant : demande enregistrée et suivie dans l'admin. |
| Notifications | WhatsApp Business (API Cloud de Meta) et e-mail, si configurés ; sinon bouton WhatsApp en un clic dans l'admin. |
| Application installable | Ajout à l'écran d'accueil du téléphone (PWA). |

## Démarrer en local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # puis compléter au minimum ADMIN_PASSWORD
.venv/bin/uvicorn app.main:app --reload
```

Site : http://localhost:8000 · Espace cabinet : http://localhost:8000/admin

Tests : `.venv/bin/python -m pytest -q tests`. Les tests font tout le parcours, y compris le robot du portail, sur un faux portail local.

## Mise en ligne

Guide pas à pas (Hetzner, environ 4 € par mois, HTTPS automatique) : `deploy/MISE_EN_LIGNE.md`. Le script `deploy/installer.sh` installe ou met à jour le site sur un serveur Ubuntu.

Avec Docker, sur un serveur au Maroc ou en Europe :

```bash
docker build -t digitalia-voyage .
docker run -d -p 8000:8000 --env-file .env -v digitalia-data:/data digitalia-voyage
```

Placer le site derrière HTTPS (Caddy, Nginx ou l'hébergeur), puis renseigner `SITE_URL` avec l'adresse HTTPS. Sauvegarder le volume `/data`, qui contient la base `digitalia.db` et les attestations.

## Paiement CMI

1. Signer le contrat commerçant e-commerce avec votre banque. Elle fournit le `clientid` et la `storekey` du CMI.
2. Renseigner `CMI_CLIENT_ID`, `CMI_STORE_KEY` et `CMI_GATEWAY_URL` (test, puis production).
3. Dans l'espace commerçant CMI, déclarer l'adresse de rappel `https://votre-site/paiement/cmi/callback`.
4. Faire un paiement test. L'intégration suit le kit CMI « 3D_PAY_HOSTING », hachage ver3 en SHA-512. À confirmer avec la documentation remise par la banque.

## Portail Maroc Assistance (portail.mai.ma)

Le portail n'a pas d'API publique. Un robot (navigateur automatique) l'utilise comme un conseiller, avec les identifiants du cabinet.

1. Sur un ordinateur : `pip install playwright && playwright install chromium`, puis
   `playwright codegen https://portail.mai.ma/Souscriptions`.
   Se connecter et faire une souscription test : l'outil note chaque champ cliqué.
2. Copier `mai_scenario.exemple.json` en `mai_scenario.json` et y reporter les sélecteurs relevés : champs, boutons « Ajouter un bénéficiaire », « Valider », lien de l'attestation.
3. Renseigner `MAI_LOGIN`, `MAI_PASSWORD` et laisser `MAI_DRY_RUN=true` : le robot remplit tout sans valider. Vérifier dans l'admin (bouton « Tester la saisie »).
4. Passer `MAI_DRY_RUN=false`. Ensuite, avec `MAI_MODE=validation`, le conseiller contrôle et clique « Émettre via le portail ». Avec `MAI_MODE=auto`, l'émission est lancée dès le paiement.

En cas d'échec, une capture d'écran du portail est visible dans la fiche admin. Le contrat reste « à émettre » pour une saisie manuelle. Vérifier que les conditions d'utilisation du portail MAI autorisent cette automatisation.

## Liaison avec Digitalia

**Envoi automatique** : si `DIGITALIA_WEBHOOK_URL` est défini, chaque fiche y est envoyée en `POST` JSON au paiement puis à l'émission. Elle est signée dans l'en-tête `X-Digitalia-Signature` (HMAC-SHA256 du corps avec `SECRET_KEY`). Le bouton « Synchroniser Digitalia » de l'admin renvoie toutes les fiches non confirmées.

**Reprise de toutes les souscriptions** (en-tête `X-Api-Key: DIGITALIA_API_KEY`) :

- `GET /api/digitalia/souscriptions?limite=500` renvoie tout l'historique, page par page. Repasser `depuis=<curseur>` pour la page suivante, tant que `suite` vaut `true`.
- `GET /api/digitalia/souscriptions?non_importees=true` renvoie seulement ce qui n'a pas encore été importé.
- `POST /api/digitalia/accuse` avec `{"references": ["DGV-…"]}` confirme l'import.

**Robot côté cabinet** : le dossier `robot_digitalia/` contient le robot à installer à côté de Digitalia, sur le PC direction. Il passe toutes les 15 minutes : il récupère les souscriptions, les range dans la table `site_souscriptions` de la base Digitalia et télécharge le reçu et l'attestation. Il les verse ensuite dans les clients, contrats et encaissements via `integration_digitalia.py`. Les consignes pour faire écrire ce branchement par Claude sur le PC sont dans `robot_digitalia/CONSIGNES_CLAUDE_PC.md`.

Le script `digitalia_sync.py` fait tout cela et produit un fichier JSON prêt à importer :
`python digitalia_sync.py --site https://votre-site --cle VOTRE_CLE`

Contenu d'une fiche : référence, statut, n° de police, formule, compagnie, dates, prime, encaissement (transaction, autorisation, date), souscripteur, assurés (nom, prénom, naissance, CIN, passeport, adresse), consentements horodatés.

## À fournir par le cabinet avant la mise en ligne

- Conditions générales de la compagnie en PDF : `static/conditions-generales.pdf`.
- Adresses et horaires des agences de Rabat et Salé (section « Nous contacter »).
- Vérification des numéros légaux du pied de page (ICE à 15 chiffres, n° d'agrément).
- Numéro de déclaration CNDP (loi 09-08).
