"""Construit brouillon/digitalia-brouillon.html : le site en un seul fichier, consultable sans serveur.

Mode maquette : les appels au serveur sont simulés (devis, paiement), rien n'est envoyé.
Usage : python brouillon/construire.py
"""
import base64
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
ST = ICI.parent / "static"

html = (ST / "index.html").read_text(encoding="utf-8")
css = (ST / "style.css").read_text(encoding="utf-8")
i18n = (ST / "i18n.js").read_text(encoding="utf-8")
app = (ST / "app.js").read_text(encoding="utf-8")
icone = "data:image/svg+xml;base64," + base64.b64encode((ST / "icon.svg").read_bytes()).decode()

MAQUETTE = r'''
  // ── Mode maquette : aucun serveur, réponses simulées ; la CIN est lue par Claude depuis la page
  var PROMPT_PIECE="Cette image doit être une carte nationale d'identité marocaine (CIN, recto ou verso) ou la page d'identité d'un passeport. "
    +"Lis le texte latin, le texte arabe et la bande MRZ si elle est présente. Réponds uniquement par un objet JSON : "
    +'{"lisible":true|false,"type":"CIN"|"PASSEPORT"|"AUTRE","nom":"","prenom":"","naissance":"AAAA-MM-JJ","cin":"","passeport":"","exp_passeport":"AAAA-MM-JJ","adresse":""}. '
    +"Noms et prénoms en majuscules latines, tels qu'écrits sur la pièce. Le verso de la CIN porte l'adresse. "
    +"Sur un passeport marocain, le numéro de CIN figure souvent comme « numéro personnel ». "
    +"Laisse une chaîne vide pour tout champ absent ou illisible : n'invente rien. Si l'image n'est pas une pièce d'identité, mets lisible à false.";
  var _lecteur=null;
  function lecteur(){
    if(!_lecteur)_lecteur=(window.claude&&claude.use?claude.use("sample"):Promise.resolve(null)).then(function(s){
      if(!s)return null;return s.limits().then(function(l){return l&&l.images?s:null},function(){return null})}).catch(function(){return null});
    return _lecteur}
  function api(url,opts){
    var corps={};try{corps=JSON.parse((opts&&opts.body)||"{}")}catch(e){}
    if(url.indexOf("/api/config")===0)return lecteur().then(function(l){return {ocr:!!l,paiement_demo:true,whatsapp:"212708295052"}});
    if(url.indexOf("/api/ocr")===0)return lecteur().then(function(l){
      if(!l){var e=new Error("indisponible");e.status=503;e.code="indisponible";throw e}
      return l.json(PROMPT_PIECE,{images:[opts.body.get("fichier")],modelTier:"default"}).then(function(r){
        return r&&r.lisible?{ok:true,data:r}:{ok:false,code:"illisible"}
      },function(err){var e=new Error(err.code||"erreur");e.code=err.code==="image_rejected"?"image":err.code;e.status=err.code==="rate_limited"?429:422;throw e})});
    if(url.indexOf("/api/devis")===0)return Promise.resolve({ok:true});
    if(url.indexOf("/api/souscriptions")===0){
      var e=new Error("Maquette : sur le site en ligne, ce bouton enregistre la souscription puis ouvre la page bancaire 3-D Secure du CMI.");
      e.status=422;e.code="maquette";return Promise.reject(e)}
    return Promise.reject(new Error("maquette"));
  }'''
app = re.sub(r"  function api\(url,opts\)\{.*?\n  \}\n", lambda m: MAQUETTE.lstrip("\n") + "\n", app, count=1, flags=re.S)
app = app.replace('if("serviceWorker" in navigator)navigator.serviceWorker.register("/sw.js").catch(function(){});', "")
assert "Mode maquette" in app

html = html.replace('<link rel="stylesheet" href="/static/style.css">', "<style>\n" + css + "\n</style>")
html = html.replace('<script src="/static/i18n.js" defer></script>\n', "").replace('<script src="/static/app.js" defer></script>\n', "")
html = html.replace('<link rel="manifest" href="/manifest.webmanifest">\n', "")
html = html.replace('href="/static/icon.svg"', f'href="{icone}"').replace('src="/static/icon.svg"', f'src="{icone}"')
html = html.replace('href="/static/conditions.html"', 'href="#garanties"')
bandeau = ('<div style="background:#e0a93a;color:#3f1c37;font:600 13px/1.4 Poppins,system-ui,sans-serif;'
           'text-align:center;padding:8px 16px">Brouillon (maquette) : les paiements et devis ne sont pas envoyés.</div>\n')
html = html.replace("<body>\n", "<body>\n" + bandeau, 1)
html = html.replace("</body>", "<script>\n" + i18n + "\n</script>\n<script>\n" + app + "\n</script>\n</body>")
assert "/static/" not in html, re.findall(r'.{30}/static/.{30}', html)
(ICI / "digitalia-brouillon.html").write_text(html, encoding="utf-8")
print("ok", len(html))
