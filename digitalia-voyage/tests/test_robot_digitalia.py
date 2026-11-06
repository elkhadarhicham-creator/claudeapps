"""Le robot côté cabinet, contre le vrai serveur HTTP du site."""
import socket
import sqlite3
import sys
import threading
import time
from pathlib import Path

import uvicorn
from test_site import c, payer, souscription

from app import main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "robot_digitalia"))
import robot_site_voyage as robot  # noqa: E402


def serveur() -> str:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}"


def test_robot_recupere_integre_et_reprend(tmp_path, monkeypatch):
    url = serveur()
    r1, r2 = souscription(), souscription()
    payer(r1)
    payer(r2)
    ref1, ref2 = r1.json()["ref"], r2.json()["ref"]

    vus = []

    def integrer(conn, s):  # faux Digitalia : contrat créé seulement une fois émis
        conn.execute("CREATE TABLE IF NOT EXISTS contrats (police TEXT, client_cin TEXT, prime REAL)")
        if s["statut"] == "payee":
            return False
        conn.execute("INSERT INTO contrats VALUES (?,?,?)", (s["numero_police"], s["souscripteur_cin"], s["prime_ttc"]))
        vus.append(s["reference"])

    monkeypatch.setattr(robot, "charger_integration", lambda: integrer)
    reg = {"url": url, "cle": "cle-digitalia-test", "base": str(tmp_path / "digitalia.db"), "docs": str(tmp_path / "docs")}

    b = robot.passage(reg, reprise=True)
    assert b["recues"] >= 2 and b["integrees"] == 0  # payées mais pas encore émises
    db = sqlite3.connect(reg["base"])
    lignes = dict(db.execute("SELECT reference, statut FROM site_souscriptions").fetchall())
    assert lignes[ref1] == "payee" and lignes[ref2] == "payee"
    assert (tmp_path / "docs" / f"{ref1}-recu.pdf").read_bytes().startswith(b"%PDF")

    # Le cabinet émet le contrat 1 avec l'attestation MAI
    c.post("/api/admin/login", json={"mot_de_passe": "motdepasse-test"})
    assert c.post(f"/api/admin/souscriptions/{ref1}/emettre", data={"numero_police": "MAI/2026/42"},
                  files={"attestation": ("a.pdf", b"%PDF-1.4 att", "application/pdf")}).status_code == 200

    b = robot.passage(reg)  # passage suivant : seule la modification revient
    assert b["recues"] == 1 and b["integrees"] == 1 and vus == [ref1]
    assert db.execute("SELECT police, client_cin FROM contrats").fetchall() == [("MAI/2026/42", "AB123456")]
    assert (tmp_path / "docs" / "MAI_2026_42-attestation.pdf").read_bytes().startswith(b"%PDF")
    ligne = db.execute("SELECT statut, numero_police, integre_le FROM site_souscriptions WHERE reference=?", (ref1,)).fetchone()
    assert ligne[0] == "emise" and ligne[1] == "MAI/2026/42" and ligne[2]

    assert robot.passage(reg)["recues"] == 0  # rien de neuf
    # Le site sait que Digitalia a tout importé
    h = {"x-api-key": "cle-digitalia-test"}
    restants = c.get("/api/digitalia/souscriptions", params={"non_importees": True, "limite": 1000}, headers=h).json()
    assert not {ref1, ref2} & {f["reference"] for f in restants["souscriptions"]}
