"""Signatures (liens clients, codes de vérification, session admin) et limitation de débit."""
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

from . import config


def sign(*parts: str, length: int = 16) -> str:
    msg = "|".join(parts).encode()
    return hmac.new(config.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:length]


def code_verification(ref: str) -> str:
    """Code court imprimé sous le QR du reçu ; permet à un tiers de vérifier l'authenticité."""
    return sign("verif", ref, length=10).upper()


def new_token() -> str:
    return secrets.token_urlsafe(24)


SESSION_TTL = 12 * 3600


def admin_session() -> str:
    exp = str(int(time.time()) + SESSION_TTL)
    return f"{exp}.{sign('admin', exp, length=40)}"


def admin_session_valide(v: str | None) -> bool:
    if not v or "." not in v:
        return False
    exp, sig = v.split(".", 1)
    if not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(sig, sign("admin", exp, length=40))


def mot_de_passe_ok(p: str) -> bool:
    return bool(config.ADMIN_PASSWORD) and hmac.compare_digest(p.encode(), config.ADMIN_PASSWORD.encode())


class RateLimiter:
    """Limite simple en mémoire : n requêtes par fenêtre de temps et par clé (IP)."""

    def __init__(self, n: int, fenetre: int):
        self.n, self.fenetre = n, fenetre
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def ok(self, cle: str) -> bool:
        t = time.time()
        with self.lock:
            q = self.hits[cle]
            while q and q[0] < t - self.fenetre:
                q.popleft()
            if len(q) >= self.n:
                return False
            q.append(t)
            return True
