# Mettre le site en ligne (OVHcloud : serveur + nom de domaine, un seul panier)

Prix indicatifs relevés en octobre 2026, à vérifier dans le panier :

- **VPS-1** (2 vCores, 4 Go de mémoire, 40 Go, sauvegarde quotidienne incluse) : environ 3,81 € HT/mois avec engagement 12 mois, environ 4,49 € HT/mois sans engagement ;
- **nom de domaine .com** : environ 7,99 € HT la 1re année, environ 14 € HT ensuite.

## 1. Ce que vous faites (15 minutes)

1. Allez sur **https://www.ovhcloud.com/fr/vps/** et cliquez sur **Commander** sous **VPS-1** :
   - **Image** : Ubuntu (la version la plus récente proposée) ;
   - **Localisation** : France (Gravelines, Roubaix ou Strasbourg) ;
   - **Engagement** : 12 mois (le moins cher par mois).
2. Dans le même panier, ajoutez le **nom de domaine** : sur **https://www.ovhcloud.com/fr/domains/**, cherchez par exemple `digitalia-assurance.com` ou `digitalia-voyage.com` et ajoutez-le au panier. Refusez les options payantes : hébergement web, e-mail et DNS Anycast sont inutiles ici.
3. Payez. OVH vous envoie par e-mail l'**adresse IP** du VPS et le mot de passe de l'utilisateur `ubuntu`.
4. Dans l'espace client OVH, ouvrez **Noms de domaine → votre domaine → Zone DNS** et ajoutez deux enregistrements **A** vers l'adresse IP du VPS :
   - sous-domaine vide (domaine nu) ;
   - sous-domaine `www`.
5. Facultatif mais conseillé : créez une clé API sur **https://console.anthropic.com** pour la lecture automatique des CIN.

## 2. Ce que Claude sur le PC fait

Collez ce message dans Claude sur le PC (onglet Code), en remplaçant l'adresse IP, le domaine et la clé :

```
Installe le site Digitalia Assurance Voyage sur mon VPS OVH.
Adresse IP : 51.xx.xx.xx — utilisateur : ubuntu — mot de passe : (celui reçu par e-mail)
Nom de domaine : www.digitalia-assurance.com
Clé Anthropic : sk-ant-... (ou « pas encore »)
1. Connecte-toi en SSH, installe ma clé SSH et désactive ensuite la connexion par mot de passe.
2. Vérifie que le domaine pointe bien vers l'adresse IP (sinon attends quelques minutes).
3. Lance :
curl -fsSL https://raw.githubusercontent.com/elkhadarhicham-creator/claudeapps/claude/new-session-mmyzq5/digitalia-voyage/deploy/installer.sh | sudo DOMAINE=<domaine> ANTHROPIC_API_KEY=<clé> bash
4. Attends la fin, puis donne-moi l'adresse du site, le mot de passe de l'espace cabinet et la clé du robot Digitalia affichés à la fin.
5. Range la clé du robot et l'adresse du site dans robot_site_voyage.ini.
```

Le script installe Docker, télécharge le site, crée les réglages (mot de passe cabinet, clé Digitalia, clé secrète), puis démarre le site avec un certificat HTTPS automatique.

Sans nom de domaine, laissez `DOMAINE` vide : le site prend alors une adresse gratuite basée sur l'adresse IP, par exemple `https://51-xx-xx-xx.sslip.io`.

## 3. Ensuite

- **Mettre à jour le site** : relancer la même commande. Les données et les réglages sont conservés.
- **Paiement CMI** : après signature du contrat commerçant, ajouter `CMI_CLIENT_ID` et `CMI_STORE_KEY` dans `/opt/digitalia/digitalia-voyage/.env`, puis relancer.
- **Changer de domaine** : modifier `SITE_URL` dans ce même fichier, puis relancer.
- **Données** : elles sont dans le volume Docker `donnees`. Le VPS-1 inclut une sauvegarde quotidienne.

## Alternative : Hetzner

Hetzner (Allemagne) vend un serveur comparable, CX23 ou CAX11, pour environ 6 €/mois, mais pas de nom de domaine. Le même script fonctionne : il faut se connecter en `root`, et `sudo` est alors inutile.
