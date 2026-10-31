# Relevé du portail intermédiaire Maroc Assistance (31/10/2026)

Relevé fait par Claude dans Chrome, sur le compte du cabinet, sans valider de contrat. Identifiants et données de clients retirés.

## Navigation
- Connexion (mot de passe enregistré dans Chrome), puis clic hors de la bannière pour la fermer.
- Menu ☰ : Souscription → Nouvelle souscription = `/Souscriptions/Create` ; Suivi souscriptions = `/Souscriptions/Index`.
- Autres rubriques : Demande d'attestation `/Attestation/Index`, Liste des impayés `/Impayes/Index`, Factures `/Factures/Index`, Déclaration semestrielle ACAPS `/ImpayeAcaps2/Index`, Demande de restitution `/Restitution/Index`, Etat CP `/EtatCP/Index`.
- Affichage : à largeur moyenne (≈ 900 px), le cadre « Règlement » recouvre les colonnes du haut. Le robot doit travailler en fenêtre large (1400 px) ; à la main, zoom Chrome 80 %.

## Formulaire `/Souscriptions/Create`
- Produit : liste (INJAD MONDE, SCHENGEN VISA, EXPATRIE, INTERNATIONAL STUDENT ASSISTANCE FERME, AUTO COMPLEMENTAIRE PLUS OP 1/2/3, AUTO PREMIUM DF, ASSISTANCE LOUEURS GOLD ETRANGER / MAROC).
- Type de souscripteur : Personne Physique / Personne Morale.
- Assuré principal : fiche contact (prénom*, nom*, sexe, CIN ou passeport, date de naissance, lieu de naissance, civilité, situation familiale, adresse, ville, pays, code postal, fonction, email, mobile, téléphone) ; case « est le souscripteur ».
- Assurance couvrant le même risque : SANS, SAHAM ASSISTANCE, AXA ASSISTANCE, WAFA IMA ASSISTANCE, RMA ASSISTANCE.
- Assurance maladie : 25 choix (CNOPS, CNSS, compagnies…) + SANS. **Liste exacte à relever.**
- Date d'effet JJ/MM/AAAA. Durées Injad Monde : 6 mois, 1 An, 2 Ans, 3 Ans, 4 Ans, 5 Ans.
- Tarif (chargé quand produit + assuré + durée sont remplis) : « Tarif 1 an < 70 ans » ou « NV Tarif IM <70 ANS à 350,00dh » ; 6 mois : « Tarif 6 mois IM SV < 70 ans ».
- Mode de règlement : Espèce, Chèque, Virement.
- Boutons : « Enregistrer la souscription » puis « Confirmer » → souscription en **Brouillon**.
- Ensuite : « Ajouter un bénéficiaire » → « Enregistrer le bénéficiaire » (liens : Enfant, Conjoint, Ascendant) ; véhicules par « Gérer les véhicules ».
- Validation du contrat : action **« Activer »** dans le Suivi souscriptions (⚠ définitive).
- Règles de saisie : CIN `^[a-zA-Z]{1,2}[0-9]{1,6}[a-zA-Z]?$` ; téléphone 10 chiffres commençant par 0.

## API internes (lecture)
- `GET /api/GetListeDurees?produit_id=<id>`
- `GET /api/GetListeTarifsDuree?produit_id=<id>&produit_name=…&axm_assureprincipalid=<id>&duree=…&datedeffet=JJ/MM/AAAA&idSouscription=<id>`
- `GET /api/GetListeRemises?…` : aucune remise configurée.
- Recalcul : `UpdateSouscriptionPriceLevel`, `UpdateDureeSouscription`.

## Primes Injad Monde relevées (DH)
| Durée | Tarif | Prime client | Commission nette | Net à payer à MAI |
|---|---|---|---|---|
| 6 mois | Tarif 6 mois IM SV < 70 ans | 700,00 | 178,55 | 530,38 |
| 1 an | Tarif 1 an < 70 ans | 890,00 | 227,02 | 674,33 |
| 1 an | NV Tarif IM <70 ANS à 350,00dh | 350,00 | 89,27 | 265,19 |
| 2 ans | (les deux tarifs) | identique à 1 an | | ⚠ à vérifier avec MAI |

Ajouter un conjoint ne change pas la prime.

## Encore à relever
- Les `id` / `name` exacts de chaque champ et bouton (script JavaScript du prompt, sur `/Souscriptions/Create`, sur la fiche contact, sur l'ajout de bénéficiaire et sur « Gérer les véhicules »).
- La liste exacte des 25 assurances maladie.
- Où lire le n° de police après « Activer », et comment télécharger l'attestation.
