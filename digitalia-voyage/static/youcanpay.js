/* Page de paiement YouCan Pay : affiche le formulaire de carte (yp.js), confirme, puis renvoie vers le suivi */
(function(){
  "use strict";
  var box=document.getElementById("ycp");if(!box)return;
  var d=box.dataset,btn=document.getElementById("payer"),err=document.getElementById("erreur");
  var MSG={
    fr:{charge:"Chargement du formulaire…",payer:btn.textContent,encours:"Paiement en cours…",indispo:"Le formulaire de paiement ne s'affiche pas. Réessayez dans un instant ou écrivez-nous sur WhatsApp au 07 08 29 50 52.",verif:"Paiement accepté, vérification en cours…"},
    ar:{charge:"جارٍ تحميل استمارة الأداء…",payer:btn.textContent,encours:"جارٍ الأداء…",indispo:"تعذر عرض استمارة الأداء. أعد المحاولة بعد لحظات أو راسلنا عبر واتساب على 07 08 29 50 52.",verif:"تم قبول الأداء، جارٍ التحقق…"}
  }[d.langue==="ar"?"ar":"fr"];
  function erreur(m){err.textContent=m||"";err.hidden=!m}
  function versSuivi(){location.href=d.suivi}
  if(typeof window.yp!=="function"){erreur(MSG.indispo);return}
  btn.textContent=MSG.charge;
  var paiement=window.yp(d.cle,{locale:d.langue}).elements({token:d.jeton,container:"#payment",gateways:["credit-card"]});
  paiement.mount().then(function(){btn.disabled=false;btn.textContent=MSG.payer})
    .catch(function(){erreur(MSG.indispo);btn.textContent=MSG.payer});
  btn.addEventListener("click",function(){
    erreur();btn.disabled=true;btn.textContent=MSG.encours;
    paiement.confirm().then(function(r){
      if(r.status!=="succeeded"){
        erreur((r.error&&r.error.message)||"Paiement refusé.");btn.disabled=false;btn.textContent=MSG.payer;return;
      }
      btn.textContent=MSG.verif;
      var tid=(r.transaction&&(r.transaction.id||r.transaction.transaction_id))||"";
      fetch("/api/paiement/youcanpay/confirmer",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ref:d.ref,t:d.t,transaction_id:String(tid)})}).then(versSuivi,versSuivi);
    });
  });
})();
