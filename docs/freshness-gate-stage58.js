(()=>{
const BUILD='freshness-gate-20260829-2032';
const root=document.documentElement;
let readyTimer=null;
function ensureStatus(){
  if(document.getElementById('freshness-gate-status'))return;
  const nav=document.getElementById('decision-nav');
  if(!nav)return;
  const el=document.createElement('div');
  el.id='freshness-gate-status';
  el.innerHTML='<strong>Refreshing latest snapshot…</strong><br>Decision views will appear once current data is confirmed.';
  nav.insertAdjacentElement('afterend',el);
}
function hold(){
  clearTimeout(readyTimer);
  root.removeAttribute('data-fresh-ready');
  ensureStatus();
}
function release(){
  clearTimeout(readyTimer);
  readyTimer=setTimeout(()=>{
    root.setAttribute('data-fresh-ready','true');
    root.dataset.freshnessGateBuild=BUILD;
  },260);
}
function bind(){
  hold();
  window.addEventListener('fplCoreDataReady',release,{passive:true});
  window.addEventListener('pagehide',hold,{passive:true});
  window.addEventListener('pageshow',e=>{
    if(e.persisted){
      hold();
      // Force a clean reload on Safari BFCache restore so restored DOM never masquerades as current data.
      setTimeout(()=>location.reload(),30);
    }
  },{passive:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
