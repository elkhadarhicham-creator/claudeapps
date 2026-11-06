import glob
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import faux_portail  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="digitalia-test-"))
PORTAIL = faux_portail.demarrer()

# Scénario du robot calqué sur le modèle livré, pointé vers le faux portail
sc = json.loads((ROOT / "mai_scenario.exemple.json").read_text(encoding="utf-8"))
sc["connexion"][0]["url"] = PORTAIL + "/"
sc["connexion"][-1]["contient"] = "/accueil"
sc["souscription"][0]["url"] = PORTAIL + "/Souscriptions"
(TMP / "scenario.json").write_text(json.dumps(sc), encoding="utf-8")

chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))
os.environ.update({
    "DATA_DIR": str(TMP), "SITE_URL": "http://testserver", "ADMIN_PASSWORD": "motdepasse-test",
    "DIGITALIA_API_KEY": "cle-digitalia-test", "SECRET_KEY": "secret-de-test",
    "MAI_MODE": "validation", "MAI_LOGIN": "cabinet", "MAI_PASSWORD": "secret",
    "MAI_SCENARIO": str(TMP / "scenario.json"), "MAI_CHROMIUM_PATH": chrome[-1] if chrome else "",
})
for k in ("CMI_CLIENT_ID", "CMI_STORE_KEY", "ANTHROPIC_API_KEY", "DIGITALIA_WEBHOOK_URL", "WHATSAPP_TOKEN", "SMTP_HOST"):
    os.environ.pop(k, None)
