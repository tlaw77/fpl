(()=>{
const BUILD='market-direction-v1-20260826-2122-hotfix';
function classify(row){
  const text=(row.innerText||'').toLowerCase();
  if(/strong rise pressure|rise pressure/.test(text))return'rise';
  if(/strong fall pressure|fall pressure/.test(text))return'fall';
  return'neutral';
}
function netSpan(row){
  return [...row.querySelectorAll('.market-meta span')].find(x=>/\bnet\b/i.test(x.textContent||''))||null;
}
function pressureSpan(row){
  return [...row.querySelectorAll('.market-meta span')].find(x=>/pressure|stable/i.test(x.textContent||''))||null;
}
function patchRow(row){
  const dir=classify(row);
  row.classList.remove('market-dir-rise','market-dir-fall','market-dir-neutral');
  row.classList.add(`market-dir-${dir}`);
  const net=netSpan(row),pressure=pressureSpan(row);
  if(net){
    let arrow=net.querySelector('.market-dir-arrow');
    if(!arrow){arrow=document.createElement('b');arrow.className='market-dir-arrow';net.prepend(arrow)}
    arrow.textContent=dir==='rise'?'↑':dir==='fall'?'↓':'→';
    net.classList.add('market-net-direction');
  }
  if(pressure){pressure.classList.add('market-pressure-cell')}
}
function patch(){
  const host=document.querySelector('#market-urgency');
  if(!host)return;
  host.querySelectorAll('.market-row').forEach(patchRow);
  host.dataset.marketDirectionBuild=BUILD;
}
function start(){
  patch();setTimeout(patch,400);setTimeout(patch,1200);
  const host=document.querySelector('#market-urgency');
  if(host)new MutationObserver(()=>patch()).observe(host,{childList:true,subtree:true});
  window.addEventListener('fplPlanChanged',()=>setTimeout(patch,60));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
window.FPLMarketDirection={build:BUILD,patch};
})();