(()=>{
const BUILD='app-fast-v1-20260827-0110';
const DATA='https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const fmt=(v,f='—')=>(v===null||v===undefined?f:v);
function kpi(label,value,note=''){return `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note)}</div></div>`}
function renderKpis(d){
  const el=document.getElementById('kpi-grid');if(!el)return;
  const me=d.me||{},r=d.rivals||[];
  const leader=Math.max(me.total_points||0,...r.map(x=>x.total_points||0));
  const above=r.filter(x=>(x.total_points||0)>(me.total_points||0)).sort((a,b)=>(a.total_points||0)-(b.total_points||0))[0];
  const live=me.live_calculated_points??me.gw_points,avg=d.league?.average_live_calculated_points;
  el.innerHTML=[
    kpi('Rank',`#${fmt(me.rank)}`,`${d.league?.manager_count||0} managers`),
    kpi('Live GW',fmt(live),avg!==undefined?`League avg ${Number(avg).toFixed(1)}`:`Official ${fmt(me.gw_points)}`),
    kpi('Gap to leader',leader-(me.total_points||0),leader===me.total_points?'You lead':'points'),
    kpi('Gap to next',above?(above.total_points||0)-(me.total_points||0):0,above?above.team_name:'No one above'),
    kpi('Bank',`£${Number(me.bank||0).toFixed(1)}m`,`TV £${Number(me.team_value||0).toFixed(1)}m`)
  ].join('');
}
function showTransfer(){
  const nav=document.getElementById('decision-nav');
  const btn=nav?.querySelector('button[data-view="transfer"]');
  document.querySelectorAll('.dashboard-view').forEach(v=>v.style.display='none');
  const view=document.getElementById('view-transfer');if(view)view.style.display='block';
  nav?.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
  btn?.classList.add('active');
}
function loadIntelApp(){
  if(window.__legacyIntelLoaded||document.querySelector('script[data-legacy-intel]'))return;
  window.__legacyIntelLoaded=true;
  const s=document.createElement('script');s.src='app.js?v=20260827-intel-lazy';s.dataset.legacyIntel='1';document.body.appendChild(s);
}
function bindIntel(){
  const btn=document.querySelector('#decision-nav button[data-view="intel"]');
  if(btn)btn.addEventListener('click',loadIntelApp,{once:true});
}
async function boot(){
  showTransfer();bindIntel();
  try{
    const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),8000);
    const r=await fetch(DATA,{cache:'no-store',signal:ctl.signal});clearTimeout(timer);
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    const d=await r.json();window.__latestDashboardData=d;
    const title=document.getElementById('league-title');if(title)title.textContent=d.league?.name||'FPL Dashboard';
    const gw=document.getElementById('gw-pill');if(gw)gw.textContent=`GW ${fmt(d.current_gw)} → ${fmt(d.next_gw)}`;
    const stamp=document.getElementById('last-updated');if(stamp)stamp.textContent=d.generated_at_utc?`Snapshot updated ${new Date(d.generated_at_utc).toLocaleString()}`:'Latest snapshot';
    renderKpis(d);
    document.documentElement.dataset.coreReady=BUILD;
    window.dispatchEvent(new CustomEvent('fplCoreReady',{detail:d}));
  }catch(e){
    const title=document.getElementById('league-title');if(title)title.textContent='FPL Decision Centre';
    const stamp=document.getElementById('last-updated');if(stamp)stamp.textContent='Core data is taking longer than expected — transfer tools can still load independently.';
  }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
window.FPLFastApp={build:BUILD,loadIntelApp};
})();
