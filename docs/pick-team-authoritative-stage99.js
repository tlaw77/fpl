(()=>{
const BUILD='pick-team-authoritative-stage99-20260903-2146';
const BASE='https://raw.githubusercontent.com/tlaw77/fpl/main/data/';
const q=(s,r=document)=>r.querySelector(s), n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
let loading=null;
async function get(name){try{const r=await fetch(`${BASE}${name}?a99=${Date.now()}`,{cache:'no-store'});return r.ok?await r.json():null}catch{return null}}
function posOrder(p){return {GKP:0,DEF:1,MID:2,FWD:3}[p?.position]??9}
function firstFixture(p){return (p?.fixtures||[])[0]||null}
function fixtureText(p){const f=firstFixture(p);return f?`${String(f.opponent||'').slice(0,3).toUpperCase()} ${f.venue||''} · FDR ${n(f.difficulty,3)}`:'Fixture pending'}
const KIT={'Arsenal':['solid','#e30613','#fff','ARS'],'Aston Villa':['sleeves','#6a1538','#95c8e8','AVL'],'Bournemouth':['stripes','#d71920','#111','BOU'],'Brentford':['stripes','#e30613','#fff','BRE'],'Brighton':['stripes','#0057b8','#fff','BHA'],'Chelsea':['solid','#034694','#fff','CHE'],'Coventry City':['solid','#6ec6e8','#fff','COV'],'Crystal Palace':['stripes','#1b458f','#c4122e','CRY'],'Everton':['solid','#003399','#fff','EVE'],'Fulham':['solid','#fff','#111','FUL'],'Ipswich Town':['solid','#0054a6','#fff','IPS'],'Leeds':['solid','#fff','#1d428a','LEE'],'Liverpool':['solid','#c8102e','#fff','LIV'],'Man City':['solid','#6cabdd','#fff','MCI'],'Man Utd':['solid','#da291c','#111','MUN'],'Newcastle':['stripes','#fff','#111','NEW'],"Nott'm Forest":['solid','#d00','#fff','NFO'],'Sunderland':['stripes','#eb172b','#fff','SUN'],'Spurs':['sleeves','#fff','#132257','TOT'],'Tottenham':['sleeves','#fff','#132257','TOT'],'West Ham':['sleeves','#7a263a','#1bb1e7','WHU'],'Wolves':['solid','#fdb913','#111','WOL']};
function shirt(p){const [pattern,c1,c2,code]=KIT[p?.club]||['solid','#cbd5e1','#475569',String(p?.club||'CLB').replace(/[^A-Za-z]/g,'').slice(0,3).toUpperCase()||'CLB'];return `<div class="pitch-shirt kit-${pattern}" style="--kit1:${c1};--kit2:${c2}"><span>${esc(code)}</span></div>`}
function pitchPlayer(p,capId,vcId){const id=Number(p?.player_id||0),tag=id===capId?'C':id===vcId?'VC':'';return `<div class="a99-pitch-player">${shirt(p)}<div class="a99-player-name">${tag?`<i class="${tag==='C'?'cap':'vice'}">${tag}</i>`:''}<strong>${esc(p?.player||'—')}</strong></div><small>${esc(fixtureText(p))}</small><em>£${n(p?.price).toFixed(1)}m</em></div>`}
function benchTile(p){return `<div class="a99-bench-player"><strong>${esc(p?.player||'—')}</strong><span>${esc(p?.club||'')} · ${esc(p?.position||'')} · ${esc(fixtureText(p))}</span><b>£${n(p?.price).toFixed(1)}m</b></div>`}
function row(label,players,capId,vcId){return `<div class="a99-pitch-row"><span class="a99-row-label">${label}</span><div class="a99-pitch-row-players">${players.map(p=>pitchPlayer(p,capId,vcId)).join('')}</div></div>`}
function render(latest,review,pool){
 const host=q('#dc-team-view');if(!host||review?.status!=='SUCCESS')return;
 const ids=(review.recommended_xi_ids||[]).map(Number);if(ids.length!==11)return;
 const base=latest?.current_squad_next5||latest?.squad_next5||latest?.current_squad||latest?.squad||[];
 const poolRows=pool?.players||[];const byId=new Map([...poolRows,...base].map(x=>[Number(x.player_id),x]));
 const squad=base.map(x=>byId.get(Number(x.player_id))||x),xi=ids.map(id=>byId.get(id)).filter(Boolean);if(xi.length!==11)return;
 const idSet=new Set(ids),bench=squad.filter(x=>!idSet.has(Number(x.player_id))).sort((a,b)=>posOrder(a)-posOrder(b));
 const by={GKP:[],DEF:[],MID:[],FWD:[]};xi.forEach(p=>by[p.position]?.push(p));
 const formation=['DEF','MID','FWD'].map(pos=>by[pos].length).join('-');
 const capId=Number(review?.captain?.player_id||0),vcId=Number(review?.vice_captain?.player_id||0);
 const cap=byId.get(capId)||review.captain||{},vc=byId.get(vcId)||review.vice_captain||{};
 host.querySelector('[data-authoritative-pick-team]')?.remove();
 const sec=document.createElement('section');sec.className='a99-card';sec.dataset.authoritativePickTeam='1';
 sec.innerHTML=`<div class="a99-head"><div><p class="eyebrow">PICK TEAM · AUTHORITATIVE</p><h2>${esc(formation)} · GW${esc(review.next_gw||latest?.next_gw||'—')}</h2><p>${esc(cap.player||'—')} captain · ${esc(vc.player||'—')} vice</p></div><span>MODEL XI</span></div><div class="a99-pitch"><div class="a99-pitch-lines"></div>${row('GK',by.GKP,capId,vcId)}${row('DEF',by.DEF,capId,vcId)}${row('MID',by.MID,capId,vcId)}${row('FWD',by.FWD,capId,vcId)}</div><div class="a99-bench"><div class="a99-bench-head"><p class="a99-label">BENCH</p><span>Authoritative squad remainder</span></div>${bench.map(benchTile).join('')}</div><details><summary>Why this is authoritative</summary><p>The pitch, formation, bench and armband all come from the shared calibrated captaincy/selection model also used by the simulations. The visual layer no longer chooses its own XI.</p></details>`;
 const mode=host.querySelector('[data-global-phase-strip]');if(mode)mode.insertAdjacentElement('afterend',sec);else host.prepend(sec);
 if(sec.isConnected&&sec.querySelectorAll('.a99-pitch-player').length===11){host.querySelectorAll('[data-pick-orientations],[data-consolidation-group="gw-selection"],.pitch-panel,.pitch-impact,.pitch-bench-panel,.selection-rationale,.captain-rationale').forEach(el=>{if(!sec.contains(el))el.style.display='none'});}
 document.documentElement.dataset.pickTeamAuthoritativeBuild=BUILD;
}
async function run(){if(loading)return loading;loading=Promise.all([get('latest.json'),get('captaincy_review.json'),get('player_pool.json')]).then(([l,r,p])=>render(l,r,p)).finally(()=>loading=null);return loading}
function bind(){q('#decision-nav button[data-view="team"]')?.addEventListener('click',()=>setTimeout(run,80),{passive:true});window.addEventListener('fplCoreDataReady',()=>{if(q('.dashboard-view.active')?.id==='view-team')setTimeout(run,120)},{passive:true});window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='team')setTimeout(run,80)},{passive:true});if(q('.dashboard-view.active')?.id==='view-team')run()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();