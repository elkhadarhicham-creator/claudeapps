# Mettre le site en ligne (Hetzner, environ 4 € par mois)

## 1. Ce que vous faites (10 minutes)

1. Créez un compte sur **https://www.hetzner.com/cloud**. Hetzner demande une carte bancaire et parfois une pièce d'identité.
2. Sur le PC direction, ouvrez Claude (onglet Code, dossier `pont_analysis`) et demandez :
   > Crée-moi une clé SSH pour un serveur et affiche la clé publique.

   Copiez la ligne qui commence par `ssh-ed25519`.
3. Dans la console Hetzner, cliquez sur **Add Server** :
   - **Location** : Falkenstein ou Nuremberg (Allemagne) ;
   - **Image** : Ubuntu 24.04 ;
   - **Type** : le moins cher qui a au moins 4 Go de mémoire, **CAX11** (Arm) ou **CX22** (x86). Les deux conviennent ;
   - **SSH keys** : collez la clé copiée à l'étape 2 ;
   - laissez le reste par défaut, puis **Create & Buy now**.
4. Notez l'**adresse IP** du serveur, par exemple `91.98.12.34`.
5. Facultatif mais conseillé : créez une clé API sur **https://console.anthropic.com**, pour la lecture automatique des CIN.

## 2. Ce que Claude sur le PC fait

Collez ce message dans Claude sur le PC, en remplaçant l'adresse IP et la clé :

```
Installe le site Digitalia Assurance Voyage sur mon serveur Hetzner.
Adresse IP : 91.98.12.34
Clé Anthropic : sk-ant-... (ou « pas encore »)
Connecte-toi en SSH (root, avec la clé créée tout à l'heure) et lance :
curl -fsSL https://raw.githubusercontent.com/elkhadarhicham-creator/claudeapps/claude/new-session-mmyzq5/digitalia-voyage/deploy/installer.sh | ANTHROPIC_API_KEY=<clé> bash
Attends la fin, puis donne-moi l'adresse du site, le mot de passe de l'espace cabinet et la clé du robot Digitalia affichés à la fin.
Range ensuite la clé du robot dans robot_site_voyage.ini (cle_api) avec l'adresse du site (url).
```

Le script installe Docker, télécharge le site, crée les réglages (mot de passe cabinet, clé Digitalia, clé secrète) et démarre le site avec un certificat HTTPS automatique.

Le site est alors en ligne à l'adresse **https://91-98-12-34.sslip.io**, gratuite, construite à partir de l'adresse IP.

## 3. Ensuite

- **Mettre à jour le site** : relancer la même commande `curl … | bash`. Les données et les réglages sont conservés.
- **Nom de domaine** (plus tard) : faire pointer le domaine vers l'adresse IP du serveur, remplacer `SITE_URL` dans `/opt/digitalia/digitalia-voyage/.env`, puis relancer la commande.
- **Paiement CMI** : après signature du contrat commerçant, ajouter `CMI_CLIENT_ID` et `CMI_STORE_KEY` dans le même fichier `.env`, puis relancer.
- **Sauvegardes** : activer « Backups » dans la console Hetzner (+20 % du prix du serveur). Les données sont dans le volume Docker `donnees`.
- **Réglages modifiables** : tous dans `/opt/digitalia/digitalia-voyage/.env` (voir `.env.example`).
