const DC_DATA='https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json';
const dcEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function dcFx(p){return (p.fixtures||[])[0]||null}
function playerTile(p){const f=dcFx(p);return `<div class="dc-player"><div><strong>${dcEsc(p.player)}</strong></div><span>${dcEsc(p.position)} · £${Number(p.price||0).toFixed(1)}m · ${f?`${dcEsc(f.opponent)} ${f.venue} FDR ${f.difficulty}`:'—'}</span></div>`}
function renderShapeView(d){
  const rows=[...(d.current_squad_next5||d.squad_next5||[])];
  const by={GKP:[],DEF:[],MID:[],FWD:[]};rows.forEach(p=>by[p.position]?.push(p));
  const spend=Object.fromEntries(Object.entries(by).map(([k,v])=>[k,v.reduce((s,p)=>s+Number(p.price||0),0)]));
  const total=Object.values(spend).reduce((a,b)=>a+b,0)||1;
  const defShare=spend.DEF/total;
  const orientation=defShare>0.27?'Defence-heavy':defShare<0.20?'Attack-heavy':'Balanced';
  const next3=pos=>by[pos].map(p=>(p.fixtures||[]).slice(0,3).reduce((s,f)=>s+(6-Number(f.difficulty||3)),0)).reduce((a,b)=>a+b,0)/(Math.max(1,by[pos].length)*3);
  const bench=rows.filter(p=>Number(p.slot||99)>11||Number(p.multiplier||0)===0);
  const benchSpend=bench.reduce((s,p)=>s+Number(p.price||0),0);
  const strengths=[['DEF',next3('DEF')],['MID',next3('MID')],['FWD',next3('FWD')]].sort((a,b)=>b[1]-a[1]);
  const lead=strengths[0];
  const orientText=lead[0]==='DEF'?'The defence has the strongest aggregate next-3 fixture profile, so a temporarily defence-heavier XI can be justified if those defenders actually start.':lead[0]==='MID'?'Midfield currently has the strongest aggregate next-3 fixture profile; avoid over-investing in defence if it forces a strong midfielder onto the bench.':'Forwards currently have the strongest aggregate next-3 fixture profile; preserve enough budget up front to exploit it.';
  const el=document.querySelector('#dc-shape-view');if(!el)return;
  el.innerHTML=`<div class="dc-four">${Object.entries(spend).map(([pos,val])=>`<div class="dc-stat"><span>${pos}</span><strong>£${val.toFixed(1)}m</strong><small>${(100*val/total).toFixed(0)}% of squad value</small></div>`).join('')}</div><div class="dc-two"><section class="dc-card"><p class="eyebrow">CURRENT ORIENTATION</p><h3>${orientation}</h3><p>Defence uses ${(defShare*100).toFixed(0)}% of squad value. ${dcEsc(orientText)}</p><div class="dc-shape-bars"><div><span>DEF next 3</span><b style="width:${Math.min(100,next3('DEF')*20)}%"></b></div><div><span>MID next 3</span><b style="width:${Math.min(100,next3('MID')*20)}%"></b></div><div><span>FWD next 3</span><b style="width:${Math.min(100,next3('FWD')*20)}%"></b></div></div></section><section class="dc-card"><p class="eyebrow">BENCH INVESTMENT</p><h3>£${benchSpend.toFixed(1)}m on bench</h3><p>The goal is not the cheapest possible bench; it is the cheapest bench that still gives reliable minutes when you need them.</p><div class="dc-player-list">${bench.map(playerTile).join('')}</div></section></div><section class="dc-card dc-wide"><p class="eyebrow">3–5 WEEK STRUCTURE</p><h3>Orient transfers around where starts will come from.</h3><p>Prefer upgrades that create a player you expect to start repeatedly over the next few gameweeks. Avoid tying money up in a player mainly destined for your bench unless that specifically prepares for rotation, a blank/double, or Bench Boost.</p></section>`;
}
function setupViews(){
  const nav=document.querySelector('#decision-nav');if(!nav||nav.dataset.ready==='1')return;nav.dataset.ready='1';
  const ids=['transfer','team','shape','pool','intel'];
  function activate(name){if(!ids.includes(name))name='transfer';ids.forEach(v=>document.querySelector(`#view-${v}`)?.classList.toggle('active',v===name));nav.querySelectorAll('button[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));try{localStorage.setItem('fplDashboardView',name)}catch{};window.dispatchEvent(new CustomEvent('fplViewChanged',{detail:{view:name}}))}
  nav.addEventListener('click',e=>{const b=e.target.closest('button[data-view]');if(b)activate(b.dataset.view)});
  activate('transfer');
  window.FPLViews={activate};
}
async function bootDecisionCentre(){
  setupViews();
  try{const d=window.FPLData?await window.FPLData.json(DC_DATA):await (await fetch(DC_DATA)).json();renderShapeView(d)}catch(e){console.warn('shape view',e)}
}
bootDecisionCentre();
window.addEventListener('effectiveSquadRendered',e=>{if(e.detail)renderShapeView(e.detail)});
