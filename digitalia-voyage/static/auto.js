/* Devis assurance automobile : formulaire, contrôles, envoi au cabinet */
(function(){
  "use strict";
  var T=DG.T,$=function(i){return document.getElementById(i)};
  function frVersIso(s){var m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec((s||"").trim());if(!m)return "";
    var d=new Date(+m[3],+m[2]-1,+m[1]);if(d.getMonth()!==+m[2]-1)return "";return m[3]+"-"+m[2]+"-"+m[1]}
  // Saisie des dates : les barres « / » se placent toutes seules
  document.querySelectorAll(".date-fr").forEach(function(i){i.addEventListener("input",function(){
    var d=i.value.replace(/\D/g,"").slice(0,8);i.value=d.length>4?d.slice(0,2)+"/"+d.slice(2,4)+"/"+d.slice(4):d.length>2?d.slice(0,2)+"/"+d.slice(2):d})});
  function val(id){return $(id).value.trim()}
  function radio(n){var r=document.querySelector('input[name="'+n+'"]:checked');return r?r.value:""}
  function err(m){var e=$("e");e.textContent=m||"";e.hidden=!m;if(m)e.scrollIntoView({behavior:"smooth",block:"center"})}
  var today=new Date().toISOString().slice(0,10);

  $("f").addEventListener("submit",function(ev){
    ev.preventDefault();
    var c={type_vehicule:radio("type_vehicule"),marque:val("marque"),modele:val("modele"),immatriculation:val("immatriculation"),
      mise_en_circulation:frVersIso(val("mise_en_circulation")),puissance_fiscale:parseInt(val("puissance_fiscale"),10),
      carburant:$("carburant").value,valeur:parseInt(val("valeur").replace(/\D/g,""),10)||0,usage:$("usage").value,
      nom:val("nom"),naissance:frVersIso(val("naissance")),date_permis:frVersIso(val("date_permis")),ville:val("ville"),
      assureur_actuel:val("assureur_actuel"),echeance_actuelle:frVersIso(val("echeance_actuelle"))||null,
      sinistres_3_ans:radio("sinistres_3_ans"),formule:radio("formule"),
      options:[].map.call(document.querySelectorAll('input[name="options"]:checked'),function(x){return x.value}),
      telephone:val("telephone"),email:val("email"),message:val("message")};
    if(!c.marque)return err(T("Indiquez la marque du véhicule."));
    if(!c.mise_en_circulation||c.mise_en_circulation>today)return err(T("Date de 1re mise en circulation invalide (format JJ/MM/AAAA)."));
    if(!(c.puissance_fiscale>=1&&c.puissance_fiscale<=60))return err(T("Indiquez la puissance fiscale (en CV, sur la carte grise)."));
    if(c.nom.length<2)return err(T("Indiquez le nom et le prénom du conducteur."));
    if(!c.naissance||c.naissance>today)return err(T("Date de naissance invalide (format JJ/MM/AAAA)."));
    if(!c.date_permis||c.date_permis>today)return err(T("Date du permis invalide (format JJ/MM/AAAA)."));
    if(val("echeance_actuelle")&&!c.echeance_actuelle)return err(T("Échéance actuelle invalide (format JJ/MM/AAAA)."));
    if(c.telephone.replace(/\D/g,"").length<9)return err(T("Indiquez un numéro WhatsApp valide : le devis y sera envoyé."));
    if(c.email&&!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(c.email))return err(T("Adresse e-mail invalide."));
    if(!$("c1").checked)return err(T("Cochez la case d'accord pour envoyer votre demande."));
    err();var b=$("go");b.disabled=true;b.textContent=T("Envoi en cours…");
    fetch("/api/devis/auto",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(c)})
      .then(function(r){return r.json().catch(function(){return {}}).then(function(j){if(!r.ok)throw (j.detail&&j.detail.message)||(r.status===429?T("Trop de tentatives, réessayez plus tard."):T("Vérifiez les champs du formulaire."));return j})})
      .then(function(){
        $("form").hidden=true;$("ok").hidden=false;
        var txt="Bonjour, je viens de demander un devis d'assurance auto : "+c.marque+(c.modele?" "+c.modele:"")+", "+c.formule+" ("+c.nom+").";
        $("wa").href="https://wa.me/212708295052?text="+encodeURIComponent(txt);
        window.scrollTo({top:0,behavior:"smooth"});
      })
      .catch(function(m){err(typeof m==="string"?m:T("Le service est momentanément indisponible. Réessayez ou écrivez-nous sur WhatsApp."))})
      .then(function(){b.disabled=false;b.textContent=T("Recevoir mon devis")});
  });
})();
