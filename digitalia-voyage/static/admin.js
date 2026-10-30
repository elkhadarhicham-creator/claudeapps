/* Espace cabinet */
(function(){
  "use strict";
  var $=function(i){return document.getElementById(i)},statut="payee",onglet="sous",tmr;
  var LIB={attente_paiement:"En attente",echec_paiement:"Échec paiement",payee:"À émettre",emise:"Émise",annulee:"Annulée",
           nouveau:"Nouveau",traite:"Traité",converti:"Converti",perdu:"Perdu"};
  var DH=function(n){return (n||0).toLocaleString("fr-MA",{minimumFractionDigits:2,maximumFractionDigits:2})+" DH"};
  function fr(s){if(!s)return "—";var p=s.slice(0,10).split("-");return p[2]+"/"+p[1]+"/"+p[0]+(s.length>10?" "+s.slice(11,16):"")}
  function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
  function api(url,opts){return fetch(url,Object.assign({credentials:"same-origin"},opts||{})).then(function(r){
    if(r.status===401){montrerLogin();throw new Error("auth")}
    return r.json().then(function(j){if(!r.ok){var e=new Error((j.detail&&j.detail.message)||"Erreur");throw e}return j})})}

  function montrerLogin(){$("login").hidden=false;$("app").hidden=true;$("menu").hidden=true}
  $("login").addEventListener("submit",function(ev){ev.preventDefault();
    fetch("/api/admin/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mot_de_passe:$("pw").value})})
      .then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.detail&&j.detail.message);return j})})
      .then(function(){$("pw").value="";$("eLogin").hidden=true;charger()})
      .catch(function(e){$("eLogin").hidden=false;$("eLogin").textContent=e.message||"Erreur"});
  });
  $("logout").addEventListener("click",function(e){e.preventDefault();fetch("/api/admin/logout",{method:"POST"}).then(montrerLogin)});
  $("sync").addEventListener("click",function(e){e.preventDefault();
    api("/api/admin/digitalia/synchroniser",{method:"POST"}).then(function(r){alert(r.envoyees+" fiche(s) envoyée(s) à Digitalia, "+r.erreurs+" erreur(s).")}).catch(function(e){alert(e.message)})});

  document.querySelectorAll(".tabs button").forEach(function(b){b.addEventListener("click",function(){
    document.querySelectorAll(".tabs button").forEach(function(x){x.classList.remove("on")});b.classList.add("on");
    onglet=b.dataset.tab||"sous";statut=b.dataset.s||"";$("q").hidden=onglet==="devis";charger()})});
  $("q").addEventListener("input",function(){clearTimeout(tmr);tmr=setTimeout(charger,250)});

  function tuiles(s){var t=$("tiles");t.innerHTML="";
    [["Aujourd'hui",DH(s.jour_ca),s.jour_nb+" contrat(s)"],["Ce mois",DH(s.mois_ca),s.mois_nb+" contrat(s)"],
     ["À émettre",String(s.a_emettre),"payés, en attente de la compagnie",s.a_emettre>0],["Devis",String(s.devis_nouveaux),"nouvelles demandes",s.devis_nouveaux>0]]
    .forEach(function(x){var d=el("div","tile"+(x[3]?" hot":""));d.append(el("small",null,x[0]),el("b",null,x[1]),el("small",null,x[2]));t.appendChild(d)})}

  function charger(){
    if(onglet==="devis")return api("/api/admin/devis").then(listeDevis);
    var p=new URLSearchParams();if(statut)p.set("statut",statut);if($("q").value.trim())p.set("q",$("q").value.trim());
    return api("/api/admin/tableau?"+p).then(function(r){
      $("login").hidden=true;$("app").hidden=false;$("menu").hidden=false;$("demoBanner").hidden=!r.demo;tuiles(r.stats);
      var L=$("liste");L.innerHTML="";
      if(!r.souscriptions.length)L.appendChild(el("p","vide","Aucune souscription."));
      r.souscriptions.forEach(function(s){
        var b=el("button","item");b.type="button";
        var c1=el("div");c1.append(el("b",null,s.ref),el("small",null,fr(s.cree_le)));
        var c2=el("div","c2");c2.append(el("b",null,s.souscripteur),el("small",null,s.nb_assures+" assuré(s) · "+s.telephone));
        var c3=el("div","c3");c3.append(el("b",null,DH(s.prime_ttc)),el("small",null,"effet "+fr(s.date_effet)));
        b.append(c1,c2,c3,el("span","badge b-"+s.statut,LIB[s.statut]||s.statut));
        b.addEventListener("click",function(){ouvrir(s.ref)});L.appendChild(b);
      });
    }).catch(function(){});
  }

  function listeDevis(r){var L=$("liste");L.innerHTML="";
    if(!r.devis.length)L.appendChild(el("p","vide","Aucune demande de devis."));
    r.devis.forEach(function(d){
      var w=el("div","item");w.style.cursor="default";
      var c1=el("div");c1.append(el("b",null,d.nom||"—"),el("small",null,fr(d.cree_le)));
      var c2=el("div","c2");c2.append(el("b",null,d.offre),el("small",null,(d.date_depart?"départ "+fr(d.date_depart)+" · ":"")+(d.message||"")));
      var a=el("a","c3",d.telephone);a.href="https://wa.me/"+tel(d.telephone);a.target="_blank";a.rel="noopener";
      var sel=el("select");["nouveau","traite","converti","perdu"].forEach(function(s){var o=el("option",null,LIB[s]);o.value=s;sel.appendChild(o)});sel.value=d.statut;
      sel.addEventListener("change",function(){api("/api/admin/devis/"+d.id,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({statut:sel.value})})});
      w.append(c1,c2,a,sel);L.appendChild(w);
    });
  }
  function tel(t){var d=(t||"").replace(/\D/g,"");if(d.indexOf("00")===0)d=d.slice(2);if(d[0]==="0"&&d.length===10)d="212"+d.slice(1);return d}

  function kvs(lignes){var dl=el("dl","kvs");lignes.forEach(function(l){if(!l[1])return;var b=el("button","cp","Copier");b.type="button";
    b.addEventListener("click",function(){navigator.clipboard&&navigator.clipboard.writeText(l[1]).then(function(){b.textContent="Copié ✓"})});
    dl.append(el("dt",null,l[0]),el("dd",null,l[1]),b)});return dl}
  function sec(titre){var s=el("div","sec");s.appendChild(el("h3",null,titre));return s}

  function ouvrir(ref){api("/api/admin/souscriptions/"+encodeURIComponent(ref)).then(function(s){
    $("fRef").textContent=s.ref+" · "+(LIB[s.statut]||s.statut);var B=$("fBody");B.innerHTML="";
    var c=sec("Contrat");c.appendChild(kvs([["Formule",s.produit],["Date d'effet",fr(s.date_effet)],["Échéance",fr(s.date_echeance)],
      ["Prime TTC",DH(s.prime_ttc)],["WhatsApp",s.telephone],["E-mail",s.email],["Transaction",s.transaction_id],["Autorisation",s.auth_code],
      ["Payée le",s.payee_le&&fr(s.payee_le)],["N° police",s.numero_police]]));B.appendChild(c);
    s.assures.forEach(function(a,i){var x=sec("Assuré "+(i+1)+" · "+a.lien);
      x.appendChild(kvs([["Nom",a.nom],["Prénom",a.prenom],["Naissance",fr(a.naissance)],["CIN",a.cin],["Passeport",a.passeport],
        ["Fin passeport",a.exp_passeport&&fr(a.exp_passeport)],["Adresse",a.adresse]]));B.appendChild(x)});
    var act=sec("Actions"),acts=el("div","acts");
    var w=el("a","btn gold","Envoyer sur WhatsApp");w.href=s.whatsapp_lien;w.target="_blank";w.rel="noopener";acts.appendChild(w);
    var sv=el("a","btn line","Page de suivi client");sv.href=s.lien_suivi;sv.target="_blank";sv.rel="noopener";acts.appendChild(sv);
    var dg=el("button","btn line","Renvoyer à Digitalia");dg.type="button";dg.addEventListener("click",function(){api("/api/admin/souscriptions/"+s.ref+"/digitalia",{method:"POST"}).then(function(r){dg.textContent=r.ok?"Envoyé ✓":"Échec de l'envoi"}).catch(function(e){alert(e.message)})});acts.appendChild(dg);
    if(s.statut!=="annulee"){var an=el("button","btn line","Annuler");an.type="button";an.addEventListener("click",function(){if(confirm("Annuler "+s.ref+" ? (le remboursement éventuel se fait depuis l'espace commerçant CMI)"))api("/api/admin/souscriptions/"+s.ref+"/annuler",{method:"POST"}).then(function(){$("fiche").close();charger()})});acts.appendChild(an)}
    act.appendChild(acts);B.appendChild(act);
    if(s.statut==="payee"){
      var mx=sec("Portail Maroc Assistance"),ma=el("div","acts");
      var po=el("a","btn line","Ouvrir portail.mai.ma");po.href="https://portail.mai.ma/Souscriptions";po.target="_blank";po.rel="noopener";
      if(s.mai.configure){
        var rb=el("button","btn gold",s.mai.essai_a_blanc?"Tester la saisie (essai à blanc)":"Émettre via le portail");rb.type="button";
        var info=el("p","hint",s.mai.essai_a_blanc?"Essai à blanc : le robot remplit le portail sans valider la souscription.":"Le robot saisit le contrat, relève le n° de police, télécharge l'attestation et prévient le client.");
        rb.addEventListener("click",function(){if(!confirm("Avez-vous contrôlé les informations ? Le robot va saisir le contrat sur le portail MAI."))return;
          rb.disabled=true;rb.textContent="Saisie en cours sur le portail… (1 à 2 min)";
          api("/api/admin/souscriptions/"+s.ref+"/mai",{method:"POST"}).then(function(r){
            alert(r.essai_a_blanc?"Essai à blanc réussi : le robot a rempli le portail sans valider.":"Contrat émis : n° "+r.numero_police+(r.attestation?" · attestation récupérée":""));$("fiche").close();charger()})
          .catch(function(e){rb.disabled=false;rb.textContent="Réessayer via le portail";info.textContent="Échec : "+e.message+" — saisissez le contrat à la main sur le portail puis enregistrez l'émission ci-dessous."})});
        ma.append(rb,po);mx.append(ma,info);
      }else{
        ma.appendChild(po);mx.append(ma,el("p","hint","Robot non configuré ("+(s.mai.identifiants?"":"identifiants MAI_LOGIN / MAI_PASSWORD, ")+(s.mai.scenario?"":"fichier mai_scenario.json, ")+"mode "+s.mai.mode+"). Saisissez le contrat sur le portail avec les boutons « Copier », puis enregistrez l'émission ci-dessous."));
      }
      if(s.mai_capture){var cap=el("a","btn line","Voir la capture du dernier échec");cap.href="/api/admin/souscriptions/"+s.ref+"/mai-capture.png";cap.target="_blank";ma.appendChild(cap)}
      B.appendChild(mx);
    }
    if(s.statut==="payee"||s.statut==="emise"){
      var em=sec(s.statut==="emise"?"Mettre à jour l'émission":"Contrat émis chez la compagnie");
      var f=el("form","stack");
      f.innerHTML='<div class="field"><label for="np">N° de police</label><input id="np" name="numero_police" required maxlength="40"></div>'
        +'<div class="field"><label for="att">Attestation de la compagnie (PDF)</label><input id="att" name="attestation" type="file" accept="application/pdf"></div>'
        +'<p class="hint">Le client est prévenu sur WhatsApp et télécharge l\'attestation depuis sa page de suivi.</p><button class="btn">Enregistrer l\'émission</button><p class="err" hidden></p>';
      f.querySelector("#np").value=s.numero_police||"";
      f.addEventListener("submit",function(ev){ev.preventDefault();var fd=new FormData(f);
        if(!f.querySelector("#att").files.length)fd.delete("attestation");
        api("/api/admin/souscriptions/"+s.ref+"/emettre",{method:"POST",body:fd}).then(function(){$("fiche").close();charger()})
          .catch(function(e){var p=f.querySelector(".err");p.hidden=false;p.textContent=e.message})});
      em.appendChild(f);B.appendChild(em);
    }
    var j=sec("Historique"),ul=el("ul","jr");s.journal.forEach(function(x){ul.appendChild(el("li",null,fr(x.le)+" · "+x.evenement.replace(/_/g," ")))});j.appendChild(ul);B.appendChild(j);
    var fj=sec("Fiche Digitalia (JSON)"),pre=el("pre","json",JSON.stringify(s.fiche_digitalia,null,2));fj.appendChild(pre);B.appendChild(fj);
    $("fiche").showModal();
  })}
  $("fClose").addEventListener("click",function(){$("fiche").close()});
  charger();
  setInterval(function(){if(!$("app").hidden&&!$("fiche").open)charger()},30000);
})();
