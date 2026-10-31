# Construire le script de souscription du portail Maroc Assistance

*À coller dans Claude (Claude Code) sur le PC du cabinet. Hicham reste devant l'écran : c'est lui qui se connecte au portail.*

---

Bonjour Claude. Le site « Digitalia Assurance Voyage » (dépôt GitHub `elkhadarhicham-creator/claudeapps`, branche `claude/new-session-mmyzq5`, dossier `digitalia-voyage`) contient un robot qui saisit les contrats Injad Monde sur le portail intermédiaire de Maroc Assistance. Il lui manque le **scénario** : les sélecteurs exacts des écrans du portail. Il faut l'écrire avec Hicham, en enregistrant une vraie saisie.

## Étapes

1. Récupère le dossier `digitalia-voyage` du dépôt. Lis `app/mai.py` (actions possibles : goto, fill, type, select, check, click, press, wait, wait_url, pause, repeter, lire, telecharger) et `mai_scenario.exemple.json` (forme du fichier et variables disponibles).
2. Installe l'outil d'enregistrement :
   `pip install playwright` puis `python -m playwright install chromium`.
3. Lance l'enregistreur et laisse Hicham faire **une souscription complète**, sans la valider à la fin si possible :
   `python -m playwright codegen --target python -o enregistrement_mai.py https://portail.mai.ma/Souscriptions`
   - connexion avec ses identifiants : **ne les écris jamais dans un fichier**, le scénario utilise `{MAI_LOGIN}` et `{MAI_PASSWORD}` ;
   - produit Injad Monde, durée, date d'effet ;
   - « Vos données personnelles » : civilité, prénom, nom, CIN, date de naissance, lieu de naissance, situation familiale, adresse, ville, code postal, pays de résidence, GSM, profession, mail et confirmation, assurance maladie / mutuelle, circonstances aggravantes ;
   - « Informations véhicule » (bouton +) : immatriculation, marque, et 2e véhicule si possible ;
   - ajout du conjoint et d'un enfant (bénéficiaires) ;
   - récapitulatif, validation, page du n° de police, téléchargement de l'attestation.
   Ne rien envoyer en « Télécharger CIN » : les copies vont dans Digitalia, pas au portail.
4. Transforme `enregistrement_mai.py` en `mai_scenario.json`, au format de `mai_scenario.exemple.json`, avec les variables du site :
   `{souscripteur.civilite}` (M. / Mme), `{souscripteur.prenom}`, `{souscripteur.nom}`, `{souscripteur.cin}`, `{souscripteur.naissance_fr}`, `{souscripteur.lieu_naissance}`, `{souscripteur.situation_familiale}`, `{souscripteur.adresse}`, `{souscripteur.ville}`, `{souscripteur.code_postal}`, `{telephone}`, `{souscripteur.profession}`, `{email}`, `{souscripteur.mutuelle}`, `{souscripteur.circonstances}`, `{date_effet_fr}`, `{duree_ans}`, `{vehicule.immatriculation}`, `{vehicule.marque}`, `{vehicule2.immatriculation}`, `{vehicule2.marque}` ; pour chaque bénéficiaire, un bloc `repeter` (début 1) avec `{assure.lien}`, `{assure.nom}`, `{assure.prenom}`, `{assure.naissance_fr}`, `{assure.cin}`, `{assure.passeport}`, `{i}` (0, 1, 2…), `{n}` (1, 2, 3…).
   - Les listes déroulantes du portail : note leurs libellés exacts et indique les correspondances si les valeurs du site diffèrent (ex. « Marié(e) » ↔ « Marié »). Signale-les à Hicham.
   - Marque `"final": true` sur le clic de validation définitive.
   - Bloc `resultat` : une étape `lire` nommée `numero_police`. Bloc `attestation` : une étape `telecharger`.
   - Préfère des sélecteurs stables : `id`, `name`, libellé (`get_by_label`), plutôt que des positions.
5. Teste à blanc : `MAI_DRY_RUN=true`, avec une souscription de test, pour que tout soit rempli sans être validé. Hicham regarde l'écran (`headless=False` le temps du test) et corrige ce qui manque.
6. Pousse `mai_scenario.json` et les corrections éventuelles sur la branche `claude/new-session-mmyzq5`, sans aucun identifiant ni donnée de client réelle. Supprime `enregistrement_mai.py` s'il contient le mot de passe.

## Règles

- Ne jamais valider un vrai contrat pendant les essais sans l'accord explicite de Hicham.
- Aucun identifiant, mot de passe ou numéro de CIN réel dans les fichiers poussés sur GitHub.
- Vérifier avec Hicham que les conditions d'utilisation du portail autorisent l'automatisation.
