/* Page de suivi client : état en direct, documents, relance du paiement */
(function(){
  "use strict";
  var T=DG.T,$=function(i){return document.getElementById(i)};
  var ref=decodeURIComponent(location.pathname.split("/").pop()),t=new URLSearchParams(location.search).get("t")||"";
  var q="?t="+encodeURIComponent(t),timer=null,dernier=null,essais=0;
  var ETATS={
    attente_paiement:["En attente du paiement","",0],
    echec_paiement:["Paiement non abouti","",0],
    payee:["Paiement reçu · contrat en cours d'émission","Votre attestation officielle arrive ici dès que la compagnie a émis le contrat. Vous serez prévenu sur WhatsApp.",2],
    emise:["Contrat émis","",4],
    annulee:["Annulé","",0]
  };
  function fr(s){if(!s)return "—";var p=s.slice(0,10).split("-");return p[2]+"/"+p[1]+"/"+p[0]}
  function rendre(s){
    dernier=s;$("contenu").hidden=false;$("ref").textContent=T("Réf.")+" "+s.ref;
    var e=ETATS[s.statut]||[s.statut,"",0];
    $("etat").textContent=T(e[0]);$("etatTxt").textContent=e[1]?" "+T(e[1]):"";
    [].forEach.call($("pipe").children,function(li,i){var ok=i<e[2];li.className=ok?"ok":(i===e[2]&&s.statut==="payee"?"wait":"");li.querySelector("i").textContent=ok?"✓":""});
    $("police").textContent=s.numero_police?T("N° de contrat")+" "+s.numero_police:"";
    var dl=$("recap");dl.innerHTML="";
    function row(k,v){var dt=document.createElement("dt");dt.textContent=k;var dd=document.createElement("dd");dd.textContent=v;dl.append(dt,dd)}
    row(T("Formule"),T(s.produit));row(T("Période"),fr(s.date_effet)+" → "+fr(s.date_echeance));
    if(s.vehicule)row(T("Assistance auto"),[s.vehicule.immatriculation,s.vehicule.marque,s.vehicule.modele].filter(Boolean).join(" "));
    row(T("Prime TTC"),s.prime_ttc.toFixed(2).replace(".",",")+" DH");
    s.assures.forEach(function(a){row(T(a.lien),a.nom+" "+a.prenom)});
    $("dlRecu").hidden=!s.recu;$("dlRecu").href="/documents/"+encodeURIComponent(s.ref)+"/recu.pdf"+q;
    $("dlAtt").hidden=!s.attestation;$("dlAtt").href="/documents/"+encodeURIComponent(s.ref)+"/attestation.pdf"+q;
    $("retry").hidden=!(s.statut==="echec_paiement"||s.statut==="attente_paiement");
  }
  function charger(){
    fetch("/api/suivi/"+encodeURIComponent(ref)+q).then(function(r){if(!r.ok)throw r;return r.json()}).then(function(s){
      rendre(s);essais++;
      clearTimeout(timer);
      // Rafraîchissement automatique tant que le contrat n'est pas émis
      if(s.statut==="payee"||(s.statut==="attente_paiement"&&essais<40))timer=setTimeout(charger,s.statut==="payee"?15000:3000);
    }).catch(function(r){if(r&&r.status===404){$("introuvable").hidden=false;$("ref").textContent=""}else timer=setTimeout(charger,8000)});
  }
  $("retry").addEventListener("click",function(){
    var b=this;b.disabled=true;
    fetch("/api/souscriptions/"+encodeURIComponent(ref)+"/paiement"+q,{method:"POST"}).then(function(r){if(!r.ok)throw r;return r.json()}).then(function(p){
      var f=$("payForm");f.action=p.action;f.innerHTML="";
      Object.keys(p.fields).forEach(function(k){var i=document.createElement("input");i.type="hidden";i.name=k;i.value=p.fields[k];f.appendChild(i)});
      f.submit();
    }).catch(function(){b.disabled=false;$("e").hidden=false;$("e").textContent=T("Le service est momentanément indisponible. Réessayez ou écrivez-nous sur WhatsApp.")});
  });
  $("copy").addEventListener("click",function(){var b=this;(navigator.clipboard?navigator.clipboard.writeText(location.href):Promise.reject()).then(function(){b.textContent=T("Lien copié")}).catch(function(){})});
  DG.onLang(function(){if(dernier)rendre(dernier)});
  charger();
})();
