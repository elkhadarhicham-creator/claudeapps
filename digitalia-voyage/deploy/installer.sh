#!/usr/bin/env bash
# Installation / mise à jour du site sur un serveur Ubuntu (Hetzner CAX11 ou autre).
# Usage (en root sur le serveur) :
#   curl -fsSL https://raw.githubusercontent.com/elkhadarhicham-creator/claudeapps/claude/new-session-mmyzq5/digitalia-voyage/deploy/installer.sh | bash
# Relancer la même commande met le site à jour sans toucher aux données ni aux réglages.
set -euo pipefail
DEPOT="https://github.com/elkhadarhicham-creator/claudeapps.git"
BRANCHE="${BRANCHE:-claude/new-session-mmyzq5}"
DOSSIER=/opt/digitalia

if ! command -v docker >/dev/null; then
  echo "→ Installation de Docker"
  curl -fsSL https://get.docker.com | sh
fi
command -v git >/dev/null || { apt-get update -q && apt-get install -yq git; }

if [ -d "$DOSSIER/.git" ]; then
  echo "→ Mise à jour du code"
  git -C "$DOSSIER" fetch -q origin "$BRANCHE" && git -C "$DOSSIER" checkout -q -B "$BRANCHE" "origin/$BRANCHE"
else
  echo "→ Téléchargement du code"
  git clone -q --depth 1 -b "$BRANCHE" "$DEPOT" "$DOSSIER"
fi
cd "$DOSSIER/digitalia-voyage"

IP=$(curl -fsS4 https://api.ipify.org || hostname -I | awk '{print $1}')
if [ ! -f .env ]; then
  echo "→ Création des réglages (.env)"
  DOMAINE_PAR_DEFAUT="${IP//./-}.sslip.io"
  aleat() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1"; }
  ADMIN=$(aleat 14); CLE=$(aleat 40)
  cp .env.example .env
  sed -i "s#^SITE_URL=.*#SITE_URL=https://${DOMAINE:-$DOMAINE_PAR_DEFAUT}#" .env
  sed -i "s#^ADMIN_PASSWORD=.*#ADMIN_PASSWORD=$ADMIN#" .env
  sed -i "s#^SECRET_KEY=.*#SECRET_KEY=$(aleat 64)#" .env
  sed -i "s#^DIGITALIA_API_KEY=.*#DIGITALIA_API_KEY=$CLE#" .env
  sed -i "s#^MAI_MODE=.*#MAI_MODE=manuel#" .env
  [ -n "${ANTHROPIC_API_KEY:-}" ] && sed -i "s#^ANTHROPIC_API_KEY=.*#ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY#" .env
  chmod 600 .env
  echo
  echo "============================================================"
  echo " À NOTER (affiché une seule fois) :"
  echo "   Mot de passe espace cabinet (/admin) : $ADMIN"
  echo "   Clé pour le robot Digitalia           : $CLE"
  echo "============================================================"
fi
DOMAINE=$(grep '^SITE_URL=' .env | sed 's#^SITE_URL=https\?://##')

echo "→ Construction et démarrage (5 à 10 minutes la première fois)"
cd deploy
DOMAINE="$DOMAINE" docker compose up -d --build
for i in $(seq 1 60); do
  if curl -fsS "https://$DOMAINE/sante" >/dev/null 2>&1; then
    echo; echo "✓ Site en ligne : https://$DOMAINE   (espace cabinet : https://$DOMAINE/admin)"; exit 0
  fi
  sleep 5
done
echo "Le site démarre encore. Vérifier avec : cd $DOSSIER/digitalia-voyage/deploy && docker compose logs --tail 50"
