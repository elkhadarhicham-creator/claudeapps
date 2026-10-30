/* Digitalia Assurance Voyage — tunnel de souscription relié au serveur */
(function(){
  "use strict";
  var T=DG.T;
  var $=function(i){return document.getElementById(i)};
  var CFG={ocr:false,paiement_demo:true,whatsapp:"212708295052"};
  var OFFRES={
    FAM_MONDE_AN:{nom:"Famille · Monde entier · 12 mois",prix:190,mois:12},
    IND_SCH:{nom:"Individuel · Schengen",prix:null},
    OMRA:{nom:"Omra / Hajj",prix:null},
    ETU:{nom:"Étudiant à l'étranger",prix:null}
  };
  var CARDS=[
    {tag:"Promotion · souscription en ligne",star:true,name:"Famille · Monde entier",items:["Souscripteur, conjoint et enfants","Tous visas : Schengen et monde","12 mois, voyages multiples","Assistance 24h/24 et 7j/7"],price:"190 DH / an",key:"FAM_MONDE_AN"},
    {tag:"Sur devis",name:"Individuel · Schengen",items:["Un voyageur, durée du visa","Frais médicaux 30 000 € minimum","Rapatriement et assistance"],price:null,key:"IND_SCH"},
    {tag:"Sur devis",name:"Omra / Hajj",items:["Couverture en Arabie saoudite","Rapatriement sanitaire","Formules groupe"],price:null,key:"OMRA"},
    {tag:"Sur devis",name:"Étudiant à l'étranger",items:["Séjour d'études","Frais médicaux et hospitalisation","Rapatriement et assistance"],price:null,key:"ETU"}
  ];
  var wa=function(t){return "https://wa.me/"+CFG.whatsapp+(t?"?text="+encodeURIComponent(t):"")};

  function api(url,opts){
    return fetch(url,opts).then(function(r){
      return r.json().catch(function(){return {}}).then(function(j){
        if(!r.ok){var d=j.detail||j;var e=new Error(d.message||d.code||("HTTP "+r.status));e.status=r.status;e.code=d.code;throw e}
        return j;
      });
    });
  }
  function msgErreur(e){
    if(e.status===429)return T("Trop de tentatives, réessayez plus tard.");
    if(e.status===422&&e.message&&e.code)return e.message;
    return T("Le service est momentanément indisponible. Réessayez ou écrivez-nous sur WhatsApp.");
  }

  // ── Cartes formules
  CARDS.forEach(function(o){
    var el=document.createElement("article");el.className="offer"+(o.star?" star":"");
    el.innerHTML='<span class="tag"></span><h3></h3><ul></ul><div class="price"><b></b><span></span></div><button type="button"></button>';
    el.querySelector(".tag").textContent=o.tag;el.querySelector("h3").textContent=o.name;
    var ul=el.querySelector("ul");o.items.forEach(function(t){var li=document.createElement("li");li.textContent=t;ul.appendChild(li)});
    el.querySelector(".price b").textContent=o.price||"Tarif sur devis";
    el.querySelector(".price span").textContent=o.price?"TTC":"réponse sur WhatsApp";
    var b=el.querySelector("button");b.textContent=o.price?"Souscrire maintenant →":"Demander un devis →";
    b.addEventListener("click",function(){
      document.querySelector('input[name="offre"][value="'+o.key+'"]').checked=true;majOffre();show(1);
      $("souscrire").scrollIntoView({behavior:"smooth"});
    });
    $("offersGrid").appendChild(el);
  });

  // ── Dates (heure locale du Maroc côté navigateur)
  function iso(d){var m=d.getMonth()+1,j=d.getDate();return d.getFullYear()+"-"+(m<10?"0":"")+m+"-"+(j<10?"0":"")+j}
  function fr(s){if(!s)return "—";var p=s.split("-");return p[2]+"/"+p[1]+"/"+p[0]}
  // Dates toujours au format français JJ/MM/AAAA, quelle que soit la langue de l'appareil
  function isoVersFr(s){return s?s.slice(8,10)+"/"+s.slice(5,7)+"/"+s.slice(0,4):""}
  function frVersIso(s){var m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec((s||"").trim());if(!m)return "";
    var d=new Date(+m[3],+m[2]-1,+m[1]);return d.getDate()===+m[1]&&d.getMonth()===+m[2]-1?m[3]+"-"+m[2]+"-"+m[1]:""}
  function D(id){return frVersIso($(id).value)}
  document.addEventListener("input",function(e){var el=e.target;if(!el.classList||!el.classList.contains("date-fr"))return;
    var c=el.value.replace(/\D/g,"").slice(0,8),v=c.slice(0,2);if(c.length>2)v+="/"+c.slice(2,4);if(c.length>4)v+="/"+c.slice(4);
    if(e.inputType&&e.inputType.indexOf("delete")===0&&/\/$/.test(el.value))v=el.value;el.value=v;
    el.classList.toggle("bad",v.length===10&&!frVersIso(v))});
  var today=iso(new Date());
  function initDates(){if(!D("effet")||D("effet")<today)$("effet").value=isoVersFr(today);majEcheance()}
  function majEcheance(){var v=D("effet");if(!v){$("echeance").value="";return}var d=new Date(v+"T00:00:00");d.setFullYear(d.getFullYear()+1);d.setDate(d.getDate()-1);$("echeance").value=isoVersFr(iso(d))}
  $("effet").addEventListener("input",majEcheance);initDates();

  // ── Navigation
  function show(n){for(var i=1;i<=4;i++)$("p"+i).hidden=i!==n;
    [].forEach.call($("stepsBar").children,function(li,i){li.className=i+1===n?"on":(i+1<n?"done":"")});
    var card=$("p1").closest(".card");if(card&&card.getBoundingClientRect().top<0)card.scrollIntoView({behavior:"smooth"})}
  document.querySelectorAll("[data-back]").forEach(function(b){b.addEventListener("click",function(){show(+b.dataset.back)})});
  function err(id,m){var e=$(id);e.textContent=m||"";e.hidden=!m}
  function offre(){return document.querySelector('input[name="offre"]:checked').value}

  // ── Formule en ligne ou sur devis
  function majOffre(){
    var devis=!OFFRES[offre()].prix;
    $("devisBox").hidden=!devis;$("devisOk").hidden=true;
    $("effetLbl").textContent=T(devis?"Date de départ prévue":"Date d'effet");
    $("echeance").closest(".field").hidden=devis;
    $("go2").textContent=T(devis?"Demander un devis sur WhatsApp":"Continuer");
    err("e1");
  }
  document.querySelectorAll('input[name="offre"]').forEach(function(r){r.addEventListener("change",majOffre)});

  // ── Assurés
  var nTrav=0,ROLES=["Souscripteur","Conjoint(e)","Enfant"];
  function addTrav(role){
    nTrav++;
    var d=document.createElement("div");d.className="trav";
    d.innerHTML='<div class="trav-head"><b></b><select aria-label="Lien"></select><button type="button">Retirer</button></div>'
      +'<div class="scan"><label class="btn"><input type="file" accept="image/*" capture="environment">📷 Photographier CIN / passeport</label><span class="s-msg">Ou saisissez les champs ci-dessous.</span></div>'
      +'<div class="row"><div class="field"><label>Nom</label><input data-k="nom" autocomplete="off"></div><div class="field"><label>Prénom</label><input data-k="prenom" autocomplete="off"></div></div>'
      +'<div class="g3"><div class="field"><label>Date de naissance</label><input class="date-fr" type="text" inputmode="numeric" placeholder="JJ/MM/AAAA" maxlength="10" autocomplete="off" data-k="naissance"></div><div class="field"><label>N° CIN</label><input data-k="cin" autocomplete="off"></div><div class="field"><label>N° passeport</label><input data-k="passeport" autocomplete="off"></div></div>'
      +'<div class="row"><div class="field"><label>Fin de validité du passeport</label><input class="date-fr" type="text" inputmode="numeric" placeholder="JJ/MM/AAAA" maxlength="10" autocomplete="off" data-k="exp_passeport"></div><div class="field"><label>Adresse</label><input data-k="adresse" autocomplete="off"></div></div>';
    // libellés reliés aux champs (accessibilité)
    d.querySelectorAll(".field").forEach(function(f,i){var id="f"+nTrav+"_"+i;f.querySelector("input").id=id;f.querySelector("label").htmlFor=id});
    var sel=d.querySelector("select");ROLES.forEach(function(r){var o=document.createElement("option");o.value=r;o.textContent=T(r);sel.appendChild(o)});sel.value=role;
    if(role==="Souscripteur")sel.disabled=true;else sel.querySelector('option[value="Souscripteur"]').disabled=true;
    var rm=d.querySelector(".trav-head button");rm.hidden=role==="Souscripteur";rm.addEventListener("click",function(){d.remove();renum()});
    var fi=d.querySelector("input[type=file]"),msg=d.querySelector(".s-msg");
    if(!CFG.ocr){d.querySelector(".scan label").style.display="none";msg.textContent=T("Lecture automatique indisponible ici : saisissez les champs.")}
    fi.addEventListener("change",function(){if(fi.files[0])lire(fi.files[0],d,msg);fi.value=""});
    $("travList").appendChild(d);renum();
  }
  function renum(){[].forEach.call($("travList").children,function(c,i){c.querySelector(".trav-head b").textContent=T("Assuré")+" "+(i+1)})}
  $("addTrav").addEventListener("click",function(){
    var a=assures(),conj=a.some(function(x){return x.lien==="Conjoint(e)"});addTrav(conj?"Enfant":"Conjoint(e)")});

  // ── Lecture de la pièce d'identité (serveur → Claude). Photo réduite avant envoi, jamais conservée.
  function reduire(file){
    return new Promise(function(ok){
      if(!/^image\/(jpeg|png|webp)$/.test(file.type)||!window.createImageBitmap){ok(file);return}
      createImageBitmap(file).then(function(img){
        var max=1800,r=Math.min(1,max/Math.max(img.width,img.height));
        var c=document.createElement("canvas");c.width=Math.round(img.width*r);c.height=Math.round(img.height*r);
        c.getContext("2d").drawImage(img,0,0,c.width,c.height);
        c.toBlob(function(b){ok(b||file)},"image/jpeg",0.85);
      }).catch(function(){ok(file)});
    });
  }
  function lire(file,box,msg){
    if(file.size>8*1024*1024){msg.className="s-msg bad";msg.textContent=T("Photo trop lourde : 8 Mo maximum.");return}
    msg.className="s-msg";msg.textContent=T("Lecture en cours…");
    var bar=document.createElement("span");bar.className="bar";box.querySelector(".scan").appendChild(bar);
    reduire(file).then(function(blob){
      var fd=new FormData();fd.append("fichier",blob,"piece.jpg");
      return api("/api/ocr",{method:"POST",body:fd});
    }).then(function(r){
      if(!r.ok){msg.className="s-msg bad";msg.textContent=T("Document illisible : reprenez la photo bien à plat, sans reflet.");return}
      var n=0;["nom","prenom","naissance","cin","passeport","exp_passeport","adresse"].forEach(function(k){
        var v=r.data[k];if(v){var inp=box.querySelector('[data-k="'+k+'"]');if(inp){inp.value=inp.classList.contains("date-fr")?isoVersFr(v):v;n++}}});
      msg.className="s-msg ok";msg.textContent=(r.data.type==="PASSEPORT"?T("Passeport"):T("CIN"))+" — "+n+" "+T("champs remplis. Vérifiez-les.");
    }).catch(function(e){
      msg.className="s-msg bad";
      msg.textContent=e.status===429?T("Trop de tentatives, réessayez plus tard."):(e.code==="image"||e.code==="format"?T("Photo non acceptée : essayez un autre fichier."):T("Lecture impossible pour le moment : saisissez les champs."));
    }).then(function(){bar.remove()});
  }

  function assures(){return [].map.call($("travList").children,function(c){
    var o={lien:c.querySelector("select").value};c.querySelectorAll("[data-k]").forEach(function(i){o[i.dataset.k]=i.classList.contains("date-fr")?frVersIso(i.value):i.value.trim()});return o})}

  // ── Étape 1 → 2 (ou envoi d'une demande de devis)
  $("go2").addEventListener("click",function(){
    var o=OFFRES[offre()],tel=$("tel").value.replace(/\D/g,"");
    if(tel.length<9)return err("e1",T("Indiquez un numéro WhatsApp valide : l'attestation y sera envoyée."));
    if(!o.prix){
      if(!$("dNom").value.trim())return err("e1",T("Indiquez votre nom."));
      var b=this;b.disabled=true;b.textContent=T("Envoi en cours…");
      var corps={offre:offre(),nom:$("dNom").value.trim(),telephone:$("tel").value,date_depart:D("effet")||null,message:$("dMsg").value.trim()};
      api("/api/devis",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)}).then(function(){
        err("e1");var ok=$("devisOk");ok.innerHTML="";
        var s=document.createElement("span");s.textContent=T("Demande envoyée. Un conseiller vous répond sur WhatsApp.");
        var a=document.createElement("a");a.href=wa("Bonjour, je viens de demander un devis : "+o.nom+" ("+corps.nom+")."+(corps.message?" "+corps.message:""));
        a.target="_blank";a.rel="noopener";a.className="btn gold";a.style.marginTop="10px";a.textContent=T("Écrire maintenant sur WhatsApp");
        ok.append(s,a);ok.hidden=false;
      }).catch(function(e){err("e1",msgErreur(e))}).then(function(){b.disabled=false;majOffre();$("devisOk").hidden=false});
      return;
    }
    if(!D("effet")||D("effet")<today)return err("e1",T("Choisissez une date d'effet à partir d'aujourd'hui."));
    err("e1");if(!$("travList").children.length)addTrav("Souscripteur");show(2);
  });

  // ── Étape 2 → 3
  $("go3").addEventListener("click",function(){
    var a=assures(),pb=[];
    [].forEach.call($("travList").children,function(c,i){c.querySelectorAll(".date-fr").forEach(function(el){
      if(el.value.trim()&&!frVersIso(el.value))pb.push(T("Assuré")+" "+(i+1)+" : "+T("date invalide, format JJ/MM/AAAA"))})});
    a.forEach(function(x,i){
      var n=T("Assuré")+" "+(i+1)+" : ";
      if(!x.nom||!x.prenom||!x.naissance)pb.push(n+T("nom, prénom et date de naissance"));
      else if(!x.cin&&!x.passeport)pb.push(n+T("numéro de CIN ou de passeport"));
      else if(x.naissance>today)pb.push(n+T("date de naissance dans le futur"));
      if(x.exp_passeport&&x.exp_passeport<D("effet"))pb.push(n+T("passeport expiré à la date d'effet"));
    });
    if(pb.length)return err("e2",T("À compléter :")+" "+pb.join(" ; "));
    err("e2");
    var o=OFFRES[offre()],dl=$("recapList");dl.innerHTML="";
    function row(k,v){var dt=document.createElement("dt");dt.textContent=k;var dd=document.createElement("dd");dd.textContent=v;dl.append(dt,dd)}
    row(T("Formule"),T(o.nom));row(T("Période"),fr(D("effet"))+" → "+fr(D("echeance")));row("WhatsApp",$("tel").value);
    a.forEach(function(x){row(T(x.lien),x.nom+" "+x.prenom+" · "+T("né(e) le")+" "+fr(x.naissance)+(x.passeport?" · "+T("Passeport")+" "+x.passeport:"")+(x.cin?" · "+T("CIN")+" "+x.cin:""))});
    a.forEach(function(x,i){if(x.exp_passeport&&x.exp_passeport>=D("effet")&&x.exp_passeport<D("echeance"))row("⚠",T("Assuré")+" "+(i+1)+" : "+T("le passeport expire avant la fin du contrat (")+fr(x.exp_passeport)+")")});
    show(3);
  });

  // ── Étape 3 → 4
  $("go4").addEventListener("click",function(){
    if(!$("c1").checked||!$("c2").checked||!$("c3").checked)return err("e3",T("Cochez les trois cases pour continuer."));
    err("e3");show(4);
  });

  // ── Paiement : création de la souscription côté serveur puis redirection vers la page bancaire
  function envoyerVersBanque(p){
    var f=$("payForm");f.action=p.action;f.innerHTML="";
    Object.keys(p.fields).forEach(function(k){var i=document.createElement("input");i.type="hidden";i.name=k;i.value=p.fields[k];f.appendChild(i)});
    f.submit();
  }
  $("payBtn").addEventListener("click",function(){
    var b=this;b.disabled=true;b.textContent=T("Redirection vers la banque…");err("e4");
    var corps={offre:offre(),date_effet:D("effet"),telephone:$("tel").value,email:$("email").value.trim(),lang:DG.lang(),
      assures:assures(),consentements:{conditions_generales:$("c1").checked,exactitude:$("c2").checked,loi_09_08:$("c3").checked}};
    api("/api/souscriptions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)}).then(function(r){
      try{localStorage.setItem("dg-derniere",JSON.stringify({ref:r.ref,t:r.token}))}catch(e){}
      envoyerVersBanque(r.paiement);
    }).catch(function(e){
      err("e4",msgErreur(e));
      b.disabled=false;b.textContent=T("Payer 190,00 DH");
    });
  });
  // Retour arrière du navigateur depuis la banque : réactiver le bouton
  window.addEventListener("pageshow",function(){var b=$("payBtn");b.disabled=false;b.textContent=T("Payer 190,00 DH")});

  DG.onLang(function(){renum();majOffre();["e1","e2","e3","e4"].forEach(function(id){err(id)})});

  // ── Configuration serveur (lecture IA disponible, mode démo, numéro WhatsApp)
  api("/api/config").then(function(c){
    CFG=c;$("demoNote").hidden=!c.paiement_demo;
    if(c.aujourdhui){today=c.aujourdhui;initDates()}
    document.querySelectorAll(".trav").forEach(function(d){if(c.ocr){d.querySelector(".scan label").style.display="";d.querySelector(".s-msg").textContent=T("Ou saisissez les champs ci-dessous.")}});
  }).catch(function(){});

  majOffre();show(1);
  if("serviceWorker" in navigator)navigator.serviceWorker.register("/sw.js").catch(function(){});
})();
