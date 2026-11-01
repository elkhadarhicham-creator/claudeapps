"""Base SQLite : souscriptions, demandes de devis, journal des événements."""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from . import config

DB_PATH = config.DATA_DIR / "digitalia.db"
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS souscriptions (
  ref TEXT PRIMARY KEY,
  token TEXT NOT NULL,
  offre TEXT NOT NULL,
  produit TEXT NOT NULL,
  duree_ans INTEGER NOT NULL DEFAULT 1,
  options TEXT,
  date_effet TEXT NOT NULL,
  date_echeance TEXT NOT NULL,
  prime_ttc REAL NOT NULL,
  telephone TEXT NOT NULL,
  email TEXT,
  lang TEXT DEFAULT 'fr',
  assures TEXT NOT NULL,
  consentements TEXT NOT NULL,
  statut TEXT NOT NULL,            -- attente_paiement | payee | emise | echec_paiement | annulee
  transaction_id TEXT,
  auth_code TEXT,
  paiement_detail TEXT,
  numero_police TEXT,
  attestation_fichier TEXT,
  webhook_statut TEXT,
  digitalia_importe_le TEXT,
  maj_le TEXT,
  seq INTEGER,                     -- compteur de modifications (reprise par Digitalia)
  ip TEXT,
  cree_le TEXT NOT NULL,
  payee_le TEXT,
  emise_le TEXT
);
CREATE INDEX IF NOT EXISTS idx_sous_statut ON souscriptions(statut);
CREATE TABLE IF NOT EXISTS devis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  offre TEXT NOT NULL,
  nom TEXT,
  telephone TEXT NOT NULL,
  date_depart TEXT,
  message TEXT,
  statut TEXT NOT NULL DEFAULT 'nouveau',
  cree_le TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref TEXT,
  evenement TEXT NOT NULL,
  detail TEXT,
  le TEXT NOT NULL
);
"""

JSON_FIELDS = ("assures", "consentements", "paiement_detail", "options")


def now() -> str:
    return datetime.now(config.TZ).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


_conn = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _connect()
        _conn.executescript(SCHEMA)
        # Mise à niveau d'une base existante (colonnes ajoutées après la 1re version)
        cols = {r[1] for r in _conn.execute("PRAGMA table_info(souscriptions)")}
        for col, ddl in (("duree_ans", "INTEGER NOT NULL DEFAULT 1"), ("options", "TEXT"),
                         ("digitalia_importe_le", "TEXT"), ("maj_le", "TEXT"), ("seq", "INTEGER")):
            if col not in cols:
                _conn.execute(f"ALTER TABLE souscriptions ADD COLUMN {col} {ddl}")
        cols_devis = {r[1] for r in _conn.execute("PRAGMA table_info(devis)")}
        for col in ("email", "details"):  # details : fiche complète en JSON (ex. devis automobile)
            if col not in cols_devis:
                _conn.execute(f"ALTER TABLE devis ADD COLUMN {col} TEXT")
        _conn.commit()
    return _conn


@contextmanager
def tx():
    with _lock:
        c = conn()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def row_to_dict(r) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in JSON_FIELDS:
        if d.get(k):
            d[k] = json.loads(d[k])
    return d


def log(ref: str | None, evenement: str, detail=None) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO journal(ref, evenement, detail, le) VALUES (?,?,?,?)",
            (ref, evenement, json.dumps(detail, ensure_ascii=False) if detail is not None else None, now()),
        )


def get_souscription(ref: str) -> dict | None:
    with _lock:
        r = conn().execute("SELECT * FROM souscriptions WHERE ref=?", (ref,)).fetchone()
    return row_to_dict(r)


def insert_souscription(d: dict) -> None:
    d = dict(d)
    for k in JSON_FIELDS:
        if k in d and not isinstance(d[k], str) and d[k] is not None:
            d[k] = json.dumps(d[k], ensure_ascii=False)
    with tx() as c:
        d["seq"] = c.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM souscriptions").fetchone()[0]
        cols = ",".join(d)
        c.execute(f"INSERT INTO souscriptions({cols}) VALUES ({','.join('?' * len(d))})", tuple(d.values()))


def update_souscription(ref: str, _signaler: bool = True, **fields) -> None:
    """_signaler=False : modification technique qui ne doit pas être renvoyée à Digitalia."""
    for k in JSON_FIELDS:
        if k in fields and fields[k] is not None and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k], ensure_ascii=False)
    with tx() as c:
        if _signaler:
            fields.setdefault("maj_le", now())
            fields["seq"] = c.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM souscriptions").fetchone()[0]
        sets = ",".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE souscriptions SET {sets} WHERE ref=?", (*fields.values(), ref))


def list_souscriptions(statut: str | None = None, q: str | None = None, limit: int = 200) -> list[dict]:
    sql, args = "SELECT * FROM souscriptions WHERE 1=1", []
    if statut:
        sql += " AND statut=?"
        args.append(statut)
    if q:
        sql += " AND (ref LIKE ? OR telephone LIKE ? OR assures LIKE ? OR numero_police LIKE ?)"
        args += [f"%{q}%"] * 4
    sql += " ORDER BY cree_le DESC LIMIT ?"
    args.append(limit)
    with _lock:
        rows = conn().execute(sql, args).fetchall()
    return [row_to_dict(r) for r in rows]


def souscriptions_depuis(depuis: str | None, non_importees: bool, limit: int) -> list[dict]:
    """Souscriptions payées ou émises, triées par date de mise à jour (synchronisation incrémentale)."""
    curseur = int(depuis) if (depuis or "").isdigit() else 0
    sql = "SELECT * FROM souscriptions WHERE statut IN ('payee','emise','annulee') AND seq > ?"
    args: list = [curseur]
    if non_importees:
        sql += " AND digitalia_importe_le IS NULL"
    sql += " ORDER BY seq LIMIT ?"
    args.append(limit)
    with _lock:
        rows = conn().execute(sql, args).fetchall()
    return [row_to_dict(r) for r in rows]


def journal(ref: str) -> list[dict]:
    with _lock:
        rows = conn().execute("SELECT evenement, detail, le FROM journal WHERE ref=? ORDER BY id", (ref,)).fetchall()
    return [dict(r) for r in rows]


def stats() -> dict:
    today = datetime.now(config.TZ).date().isoformat()
    month = today[:7]
    with _lock:
        c = conn()
        q = lambda sql, *a: c.execute(sql, a).fetchone()[0]  # noqa: E731
        paid = "statut IN ('payee','emise')"
        return {
            "jour_nb": q(f"SELECT COUNT(*) FROM souscriptions WHERE {paid} AND substr(payee_le,1,10)=?", today),
            "jour_ca": q(f"SELECT COALESCE(SUM(prime_ttc),0) FROM souscriptions WHERE {paid} AND substr(payee_le,1,10)=?", today),
            "mois_nb": q(f"SELECT COUNT(*) FROM souscriptions WHERE {paid} AND substr(payee_le,1,7)=?", month),
            "mois_ca": q(f"SELECT COALESCE(SUM(prime_ttc),0) FROM souscriptions WHERE {paid} AND substr(payee_le,1,7)=?", month),
            "a_emettre": q("SELECT COUNT(*) FROM souscriptions WHERE statut='payee'"),
            "devis_nouveaux": q("SELECT COUNT(*) FROM devis WHERE statut='nouveau'"),
        }


def insert_devis(d: dict) -> int:
    with tx() as c:
        cur = c.execute(
            "INSERT INTO devis(offre, nom, telephone, date_depart, message, email, details, cree_le) VALUES (?,?,?,?,?,?,?,?)",
            (d["offre"], d.get("nom"), d["telephone"], d.get("date_depart"), d.get("message"), d.get("email"),
             json.dumps(d["details"], ensure_ascii=False) if d.get("details") else None, now()),
        )
        return cur.lastrowid


def list_devis(limit: int = 200) -> list[dict]:
    with _lock:
        rows = conn().execute("SELECT * FROM devis ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details"]) if d.get("details") else None
        out.append(d)
    return out


def update_devis(i: int, statut: str) -> None:
    with tx() as c:
        c.execute("UPDATE devis SET statut=? WHERE id=?", (statut, i))
