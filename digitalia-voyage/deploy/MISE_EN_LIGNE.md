# Mettre le site en ligne (Hostinger : serveur VPS + nom de domaine, un seul compte)

Choix du cabinet : **Hostinger**, serveur **VPS KVM 1** et domaine **digitaliassurance.com**.

## 1. Ce que vous faites (15 minutes)

1. Sur **hostinger.fr** → **VPS** → **KVM 1** (1 vCPU, 4 Go) :
   - **durée** : 12 mois ;
   - **emplacement** : France (sinon Pays-Bas ou Allemagne) ;
   - **système** : **Ubuntu 24.04**, simple, **sans panneau de contrôle** ;
   - **mot de passe root** : un mot de passe fort, à garder précieusement ;
   - décochez les options payantes (sauvegardes quotidiennes, Monarx, e-mail).
2. **Domaine** : ajoutez **digitaliassurance.com** (1 an). Refusez e-mail et SSL payants. Gardez la protection WHOIS si elle est gratuite.
3. Payez. Dans **hPanel → VPS**, notez l'**adresse IP** du serveur.
4. **Relier le domaine au serveur** : hPanel → **Domaines** → digitaliassurance.com → **DNS / Serveurs de noms** → **Gérer les enregistrements DNS** :
   - supprimez les enregistrements **A** existants pour `@` et `www` (page d'attente Hostinger) ;
   - ajoutez un enregistrement **A**, nom `@`, valeur = adresse IP du VPS ;
   - ajoutez un enregistrement **A**, nom `www`, valeur = adresse IP du VPS.
   La prise en compte prend de quelques minutes à quelques heures.
5. Si le **pare-feu** du VPS est activé dans hPanel, autorisez les ports **22** (SSH), **80** et **443** (site).
6. Facultatif mais conseillé : créez une clé API sur **https://console.anthropic.com** pour la lecture automatique des CIN.

## 2. Ce que Claude sur le PC fait

Collez ce message dans Claude sur le PC (onglet Code), en remplaçant l'adresse IP et la clé :

```
Installe le site Digitalia Assurance Voyage sur mon VPS Hostinger.
Adresse IP : xx.xx.xx.xx — utilisateur : root — mot de passe : (celui choisi à la commande ; je le taperai moi-même)
Nom de domaine : www.digitaliassurance.com
Clé Anthropic : sk-ant-... (ou « pas encore »)
1. Connecte-toi en SSH, installe ma clé SSH et désactive ensuite la connexion par mot de passe.
2. Vérifie que digitaliassurance.com et www.digitaliassurance.com pointent bien vers l'adresse IP (sinon attends).
3. Lance :
curl -fsSL https://raw.githubusercontent.com/elkhadarhicham-creator/claudeapps/claude/new-session-mmyzq5/digitalia-voyage/deploy/installer.sh | DOMAINE=www.digitaliassurance.com ANTHROPIC_API_KEY=<clé> bash
4. Attends la fin, puis donne-moi l'adresse du site, le mot de passe de l'espace cabinet et la clé du robot Digitalia affichés à la fin.
5. Range la clé du robot et l'adresse du site dans robot_site_voyage.ini.
```

Le script installe Docker, télécharge le site, crée les réglages (mot de passe cabinet, clé Digitalia, clé secrète), puis démarre le site avec un certificat HTTPS automatique. L'adresse sans « www » redirige vers `www.digitaliassurance.com`.

Sans nom de domaine, laissez `DOMAINE` vide : le site prend alors une adresse gratuite basée sur l'adresse IP, par exemple `https://51-xx-xx-xx.sslip.io`.

## 3. Ensuite

- **Mettre à jour le site** : relancer la même commande. Les données et les réglages sont conservés.
- **Paiement CMI** : après signature du contrat commerçant, ajouter `CMI_CLIENT_ID` et `CMI_STORE_KEY` dans `/opt/digitalia/digitalia-voyage/.env`, puis relancer.
- **Changer de domaine** : modifier `SITE_URL` dans ce même fichier, puis relancer.
- **Données** : elles sont dans le volume Docker `donnees`. Activez aussi les sauvegardes (« Snapshots et sauvegardes ») dans hPanel.

## Autres hébergeurs

Le même script fonctionne sur tout serveur Ubuntu : **OVHcloud** VPS-1 (utilisateur `ubuntu`, ajouter `sudo` devant `DOMAINE=…`, zone DNS dans l'espace client OVH) ou **Hetzner** Cloud (utilisateur `root`, domaine à acheter ailleurs).
