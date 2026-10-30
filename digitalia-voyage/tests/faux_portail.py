"""Faux portail intermédiaires (imite portail.mai.ma) pour tester le robot sans toucher au vrai."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SAISIES = []

PAGE_LOGIN = b"""<!doctype html><form action="/accueil" method="get">
<input id="UserName" name="u"><input id="Password" name="p" type="password"><button type="submit">Connexion</button></form>"""

PAGE_FORM = """<!doctype html><h1>Souscriptions</h1><button onclick="nouv()">Nouvelle souscription</button>
<form id="f" action="/valider" method="post" hidden>
<select id="Produit" name="produit"><option value="x">Autre</option><option value="fam">Famille Monde entier 12 mois</option></select>
<input id="DateEffet" name="effet"><input id="Souscripteur_Nom" name="nom"><input id="Souscripteur_Prenom" name="prenom">
<input id="Souscripteur_CIN" name="cin"><input id="Souscripteur_Passeport" name="pass"><input id="Souscripteur_DateNaissance" name="naiss">
<input id="Souscripteur_Telephone" name="tel"><input id="Souscripteur_Adresse" name="adr">
<div id="benef"></div><button type="button" onclick="ajout()">Ajouter un bénéficiaire</button>
<button type="submit">Valider la souscription</button></form>
<script>var n=1;function nouv(){document.getElementById('f').hidden=false}
function ajout(){var d=document.createElement('div');['Nom','Prenom','DateNaissance','Passeport'].forEach(function(k){
var i=document.createElement('input');i.id='Beneficiaires_'+n+'__'+k;i.name='b'+n+k;d.appendChild(i)});document.getElementById('benef').appendChild(d);n++}</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", extra=None):
        body = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._send(PAGE_LOGIN)
        elif u.path == "/accueil":
            q = parse_qs(u.query)
            if q.get("u") == ["cabinet"] and q.get("p") == ["secret"]:
                self._send("<p>Bienvenue sur portail.mai.ma</p>")
            else:
                self._send("<p>Identifiants invalides</p>")
        elif u.path == "/Souscriptions":
            self._send(PAGE_FORM)
        elif u.path == "/attestation.pdf":
            self._send(b"%PDF-1.4\n% fausse attestation\n%%EOF", "application/pdf",
                       {"Content-Disposition": 'attachment; filename="attestation.pdf"'})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        SAISIES.append(parse_qs(self.rfile.read(n).decode()))
        self._send('<p>Souscription enregistrée.</p><p class="numero-police">Police n° MAI-2026-000123</p>'
                   '<a href="/attestation.pdf">Imprimer l\'attestation</a>')


def demarrer() -> str:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}"
