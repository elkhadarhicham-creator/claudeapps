# Règles du projet Digitalia Assurance Voyage

Consignes données par le cabinet (Hicham), à respecter dans toute modification :

## Langues (français, arabe, darija)
- **Les chiffres et les prix ne sont jamais à l'envers en arabe.** Tout montant s'écrit à la française
  (« 350 000 DH », « 30 000 € ») et s'affiche de gauche à droite, isolé du texte arabe.
  C'est fait automatiquement par `montants()` dans `static/i18n.js` (isolat U+2066…U+2069, espaces insécables)
  et par `[dir="rtl"] td.y` dans `static/style.css`. Toute nouvelle traduction contenant un prix doit passer par là ;
  vérifier dans Chromium en arabe que le chiffre est à gauche de « DH ».
- Les prix restent en français (« DH », pas « درهم »).
- Dates au format JJ/MM/AAAA.

## Produit et prix
- Injad Monde (Maroc Assistance), famille + 1 véhicule : **190 DH TTC par an** (prix du cabinet, promotion MAI).
  2e véhicule : +100 DH/an. + 70 ans : sur devis tant que `PRIX_INJAD_FAMILLE_70` est vide.
- Le robot MAI choisit sur le portail le tarif dont la prime TTC affichée égale le prix payé ; sinon il n'émet rien.

## Données
- Les copies de CIN / passeport vont dans Digitalia, jamais sur le portail MAI ; elles sont effacées du site
  après l'accusé de réception de Digitalia.
- Pas de mention « Intermédiaire agréé ACAPS » ni « Maroc Assistance » dans le bandeau de confiance
  (la mention légale du pied de page reste).
