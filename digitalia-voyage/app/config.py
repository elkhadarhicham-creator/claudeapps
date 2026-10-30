"""Configuration lue depuis les variables d'environnement (fichier .env en local)."""
import os
import secrets
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


TZ = ZoneInfo("Africa/Casablanca")

# Adresse publique du site (sert aux liens WhatsApp, au QR code et aux URL de retour CMI)
SITE_URL = env("SITE_URL", "http://localhost:8000").rstrip("/")
DATA_DIR = Path(env("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "attestations").mkdir(exist_ok=True)

# Clé secrète : signe les sessions admin, les liens clients et les codes de vérification.
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    _f = DATA_DIR / ".secret_key"
    if not _f.exists():
        _f.write_text(secrets.token_urlsafe(48))
    SECRET_KEY = _f.read_text().strip()

ADMIN_PASSWORD = env("ADMIN_PASSWORD")

# Paiement CMI. Sans identifiants, le site tourne en mode démonstration.
CMI_CLIENT_ID = env("CMI_CLIENT_ID")
CMI_STORE_KEY = env("CMI_STORE_KEY")
CMI_GATEWAY_URL = env("CMI_GATEWAY_URL", "https://testpayment.cmi.co.ma/fim/est3Dgate")
PAYMENT_DEMO = not (CMI_CLIENT_ID and CMI_STORE_KEY)
DEMO_STORE_KEY = "demo-store-key"

# Lecture automatique des pièces d'identité (Claude)
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-opus-5-5")

# WhatsApp Business (API Cloud de Meta) - facultatif
WHATSAPP_TOKEN = env("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = env("WHATSAPP_PHONE_ID")
WHATSAPP_TEMPLATE = env("WHATSAPP_TEMPLATE")  # modèle approuvé par Meta, ex. "souscription_confirmee"
WHATSAPP_CABINET = env("WHATSAPP_CABINET", "212708295052")

# E-mail (SMTP) - facultatif
SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587") or 587)
SMTP_USER = env("SMTP_USER")
SMTP_PASSWORD = env("SMTP_PASSWORD")
SMTP_FROM = env("SMTP_FROM", SMTP_USER)
NOTIFY_EMAIL = env("NOTIFY_EMAIL")  # e-mail du cabinet prévenu à chaque paiement

# Envoi de la fiche vers l'application Digitalia - facultatif
DIGITALIA_WEBHOOK_URL = env("DIGITALIA_WEBHOOK_URL")
# Clé que Digitalia présente pour récupérer les souscriptions (en-tête X-Api-Key)
DIGITALIA_API_KEY = env("DIGITALIA_API_KEY")

COMPAGNIE = env("COMPAGNIE", "Maroc Assistance Internationale")
