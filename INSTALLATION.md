# 📱 INSTALLATION COMPLÈTE - RAPPROCHEMENT ASSURANCES

## 🎯 Vue d'ensemble

Cette solution complète comprend 3 composants :
- **Backend API** (FastAPI) - Serveur central
- **Application Desktop** (PyQt5) - Windows/Mac/Linux
- **Application Mobile** (React Native) - Android/iOS

---

## 🔧 PRÉ-REQUIS

### Système général
- Python 3.9+ (pour le backend et le script de rapprochement)
- Node.js 14+ (pour l'app mobile)
- Git

### Pour chaque plateforme

**Windows :**
- Visual Studio Build Tools (pour les dépendances Python)
- Android SDK (pour les tests sur mobile)

**Mac :**
- Xcode Command Line Tools
- CocoaPods

**Linux :**
- build-essential
- libssl-dev

---

## 📦 INSTALLATION

### Étape 1️⃣ : Installer les dépendances Python

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Installer les dépendances
pip install fastapi uvicorn pandas pdfplumber openpyxl PyQt5 websocket-client requests
```

### Étape 2️⃣ : Démarrer le serveur backend

```bash
python backend_api.py
```

La sortie doit être :
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Vérifiez à : `http://localhost:8000/docs`

---

## 🖥️ APPLICATION DESKTOP

### Installation

```bash
# Les dépendances sont déjà installées (étape 1)
# Lancer l'app
python app_desktop.py
```

### Fonctionnalités

✅ Dashboard temps réel  
✅ Gestion des alertes avec code couleur  
✅ Historique des rapports  
✅ Synchronisation automatique avec le serveur  
✅ Notifications système  
✅ Export PDF (en développement)  

### Configuration

Dans l'app, allez à **⚙️ Configuration** pour :
- Définir l'URL du serveur (défaut: http://localhost:8000)
- Configurer le dossier des rapports
- Ajouter votre email pour les rapports

---

## 📱 APPLICATION MOBILE (ANDROID)

### Installation avec Expo (le plus facile!)

**Option 1 : Depuis le web avec Expo Cloud**

```bash
# Installer Expo CLI
npm install -g eas-cli expo-cli

# Créer un projet Expo
npx create-expo-app RapprochementAssurances
cd RapprochementAssurances

# Copier les fichiers
cp ../app_mobile.js ./App.js

# Installer les dépendances
npm install @react-navigation/native @react-navigation/bottom-tabs \
  react-native-screens react-native-safe-area-context \
  react-native-gesture-handler react-native-reanimated \
  @react-native-async-storage/async-storage \
  expo-notifications react-native-chart-kit

# Démarrer le serveur
expo start

# Scanner le QR code avec l'app Expo Go sur votre téléphone
# ou taper 'a' pour lancer Android
```

**Option 2 : Build APK pour installer directement**

```bash
# Créer un compte sur expo.dev si ce n'est pas fait
eas login

# Build pour Android
eas build --platform android

# L'APK sera prêt en 10-15 minutes
# Lien de téléchargement fourni par mail
```

### Configuration mobile

Avant de lancer l'app :

1. **Configurer l'URL du serveur** (si pas sur localhost) :
   ```javascript
   // Dans app_mobile.js, ligne 15
   const API_URL = 'http://VOTRE_IP:8000'; // Remplacer par votre IP
   ```

2. **Autoriser les notifications** quand demandé au premier lancement

3. **Se connecter au même réseau** que le serveur (important!)

### Fonctionnalités mobiles

✅ Dashboard avec statistiques temps réel  
✅ Alertes critiques avec notifications push  
✅ Historique des rapports  
✅ Traitement des alertes  
✅ Synchronisation en temps réel via WebSocket  
✅ Mode hors ligne (lecture depuis cache local)  

---

## 📊 LANCER LE SCRIPT DE RAPPROCHEMENT

### Automatiquement (depuis les apps)

- **Desktop** : Bouton 🚀 "Générer Rapport"
- **Mobile** : À venir (via l'app desktop)

### Manuellement

```bash
# Depuis le répertoire du projet
python rapprochement_auto_FIXED.py

# Sélectionner le jour à contrôler (défaut: aujourd'hui)
# Le rapport Excel est généré dans ./Rapports_Generes/
```

---

## 🔗 ARCHITECTURE RÉSEAU

```
┌─────────────────────────────────────────────────────┐
│           BACKEND API (FastAPI)                     │
│  http://localhost:8000                             │
│  ├── /api/status          → État du système        │
│  ├── /api/alerts          → Liste des alertes      │
│  ├── /api/rapports        → Liste des rapports     │
│  ├── /ws/alerts           → WebSocket temps réel   │
│  └── /docs                → Documentation Swagger   │
└─────────────────────────────────────────────────────┘
         ▲                        ▲
         │                        │
    ┌────┴────┐            ┌─────┴──────┐
    │ DESKTOP │            │   MOBILE   │
    │ (PyQt5) │            │  (React)   │
    └─────────┘            └────────────┘
```

---

## 🧪 TESTS

### Vérifier que tout fonctionne

```bash
# 1. Backend OK ?
curl http://localhost:8000/api/status

# Réponse attendue:
# {"status":"en_ligne","timestamp":"...","rapports_generes":0,...}

# 2. WebSocket OK ?
# Ouvrir dans un navigateur: http://localhost:8000/docs
# Cliquer sur "GET /ws/alerts" et tester

# 3. Base de données OK ?
# Vérifier que le fichier 'rapprochement.db' existe
ls -la rapprochement.db
```

---

## 🚀 DÉPLOIEMENT EN PRODUCTION

### Sur un serveur (AWS, Digital Ocean, etc.)

```bash
# 1. Cloner le repo
git clone <repo>
cd claudeapps

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Démarrer avec gunicorn (plus robuste que uvicorn seul)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 backend_api:app

# 5. Utiliser Nginx en reverse proxy (optionnel mais recommandé)
# Voir: https://www.nginx.com/blog/deploying-nginx-gunicorn/
```

### Fichier requirements.txt

```txt
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.1
pdfplumber==0.10.3
openpyxl==3.1.2
PyQt5==5.15.9
websocket-client==1.6.4
requests==2.31.0
python-multipart==0.0.6
gunicorn==21.2.0
```

### Configuration de sécurité (production)

```python
# Ajouter à backend_api.py
from fastapi_cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://votredomaine.com"],  # Ne pas utiliser "*"!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)
```

---

## 📞 TROUBLESHOOTING

### ❌ "Connection refused" depuis mobile/desktop

→ Vérifier que le backend est lancé  
→ Vérifier l'adresse IP (utiliser `ipconfig` sur Windows, `ifconfig` sur Mac/Linux)  
→ Vérifier le firewall  

### ❌ "ModuleNotFoundError: No module named 'PyQt5'"

```bash
# Réinstaller PyQt5
pip install PyQt5 --force-reinstall
```

### ❌ "Erreur PDF non reconnue"

→ Le script a besoin d'un PDF "État d'encaissements" spécifique  
→ Vérifier que le fichier suit le format exact  
→ Consulter le journal_diagnostic.txt généré  

### ❌ L'app mobile ne voit pas le serveur

→ Vérifier que le téléphone et l'ordi sont sur le même réseau  
→ Utiliser l'adresse IP locale (ex: 192.168.x.x) et non localhost  
→ Désactiver le firewall temporairement pour tester  

---

## 📚 DOCUMENTATION SUPPLÉMENTAIRE

- API REST : http://localhost:8000/docs (Swagger)
- Source du backend : `backend_api.py`
- Source du desktop : `app_desktop.py`
- Source du mobile : `app_mobile.js`
- Script de rapprochement : `rapprochement_auto_FIXED.py`

---

## 📝 PROCHAINES VERSIONS

- ✅ v1.0.0 - MVP complet (Desktop + Mobile + API)
- 🔄 v1.1.0 - Export PDF avanc
- 🔄 v1.2.0 - Intégration avec Google Drive
- 🔄 v1.3.0 - Authentification multi-utilisateurs
- 🔄 v2.0.0 - Mode hors ligne complet

---

## 👨‍💻 SUPPORT

Pour toute question ou bug:
1. Consulter le journal_diagnostic.txt
2. Vérifier les logs du terminal
3. Envoyer un email : support@assurances-elkhaddar.ma

---

**Bon travail! 🎉**
