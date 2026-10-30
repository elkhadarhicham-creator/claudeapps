/* Service worker : met en cache la coquille du site (installation sur l'écran d'accueil, ouverture rapide).
   Les appels /api, /paiement et /documents passent toujours par le réseau. */
const C="dg-v1",SHELL=["/","/static/style.css","/static/i18n.js","/static/app.js","/static/icon.svg"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==location.origin||!SHELL.includes(u.pathname))return;
  e.respondWith(fetch(e.request).then(r=>{const k=r.clone();caches.open(C).then(c=>c.put(e.request,k));return r}).catch(()=>caches.match(e.request)));
});
