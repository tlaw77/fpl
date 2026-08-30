(()=>{
const BUILD='league-pack-positioning-20260831-0046';
const KEY='fplWorkingPlanV2';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
function saved(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function starters(rows){const a=(rows||[]).filter(p=>(p.slot||99)<=11||p.starter||n(p.multiplier)>0);return (a.length>=11?a:(rows||[])).slice(0,11)}
function applyPlan(rows){const base=(rows||[]).map(x=>({...x})),m=saved()?.moves?.[0];if(!m?.out||!m?.in)return base;const oid=Number(m.out.player_id),on=norm(m.out.player);const out=base.filter(p=>!(oid&&Number(p.player_id)===oid)&&norm(p.player)!==on);if(!out.some(p=>Number(p.player_id)===Number(m.in.player_id)))out.push({...m.in,_planned:true});return out}
function name(p){return p?.player||p?.web_name||''}
function score(p){return n(p?.six_gw_score??p?.decision_score??p?.score_improvement)}
function nearest(d){const me=d?.me||{},rs=[...(d?.rivals||[])];return rs.sort((a,b)=>Math.abs(n(a.total_points)-n(me.total_points))-Math.abs(n(b.total_points)-n(me.total_points)))[0]||null}
function evaluate(d){
 const rivals=d?.rivals||[],raw=d.current_squad_next5||d.squad_next5||d.squad||[],my=starters(applyPlan(raw));
 const counts=new Map(),samples=new Map();
 rivals.forEach(r=>starters(r.picks||[]).forEach(p=>{const id=Number(p.player_id);if(!id)return;counts.set(id,(counts.get(id)||0)+1);if(!samples.has(id))samples.set(id,p)}));
 const rivalN=Math.max(1,rivals.length),coreCut=Math.max(2,Math.ceil(rivalN*.5)),myIds=new Set(my.map(p=>Number(p.player_id)));
 const shields=my.filter(p=>(counts.get(Number(p.player_id))||0)>=coreCut).sort((a,b)=>(counts.get(Number(b.player_id))||0)-(counts.get(Number(a.player_id))||0));
 const edges=my.filter(p=>{const c=counts.get(Number(p.player_id))||0;return c<=Math.max(1,Math.floor(rivalN*.28))&&score(p)>=8}).sort((a,b)=>score(b)-score(a));
 const threats=[...counts.entries()].filter(([id,c])=>!myIds.has(id)&&c>=coreCut).map(([id,c])=>({p:samples.get(id)||{player:`#${id}`},count:c})).sort((a,b)=>b.count-a.count||score(b.p)-score(a.p));
 let status='BALANCED',tone='#60a5fa',summary='Your XI has a useful mix of shared players and different ways to gain.';
 if(shields.length<3&&edges.length>=5){status='HIGH VARIANCE';tone='#fbbf24';summary='Your XI is more different from the pack than protected by it. Prioritise dependable upgrades before adding another differential.'}
 else if(shields.length<3){status='EXPOSED';tone='#fb7185';summary='You have relatively little protection from popular players. If two options are close, favour one strong common starter.'}
 else if(edges.length<1){status='BALANCED';tone='#60a5fa';summary='You are well protected but have few routes to gain. One strong differential is enough; there is no need to force several.'}
 else if(edges.length>4){status='HIGH VARIANCE';tone='#fbbf24';summary='You already have plenty of routes to gain. Prefer dependable upgrades and keep the strongest shared core.'}
 const near=nearest(d),gap=near?n(near.total_points)-n(d.me?.total_points):0,nearTxt=near?`${gap>0?`${gap} pts behind`:`${Math.abs(gap)} pts ahead of`} ${near.team_name||near.manager||'nearest rival'}`:'';
 return {my,shields,edges,threats,status,tone,summary,nearTxt,coreCut,rivalN};
}
function intelCard(host,e){
 if(!host)return;
 let sec=host.querySelector('[data-league-squad-intelligence]');
 if(!sec){sec=document.createElement('section');sec.className='dc-card';sec.dataset.leagueSquadIntelligence='1'}
 sec.innerHTML=`<p class="eyebrow">LEAGUE SQUAD INTELLIGENCE</p><div class="panel-head" style="margin-top:4px"><div><p class="eyebrow" style="margin-bottom:3px">LEAGUE POSITIONING</p><h3>${esc(e.status)} · squad vs pack</h3></div><div class="subtle">${e.rivalN} rivals</div></div><p class="subtle">${esc(e.summary)}</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:9px"><div style="border-left:4px solid #60a5fa;background:#142139;border-radius:11px;padding:9px"><strong>Pack shields</strong><div class="subtle" style="margin-top:5px">${esc(e.shields.slice(0,5).map(name).join(', ')||'No strong shared players in the XI')}</div></div><div style="border-left:4px solid #34d399;background:#142139;border-radius:11px;padding:9px"><strong>Your useful edges</strong><div class="subtle" style="margin-top:5px">${esc(e.edges.slice(0,5).map(name).join(', ')||'No clear quality differential')}</div></div></div><div style="margin-top:8px;border-left:4px solid #fb7185;background:#142139;border-radius:11px;padding:9px"><strong>Pack threats you lack</strong><div class="subtle" style="margin-top:5px">${esc(e.threats.slice(0,5).map(x=>name(x.p)).join(', ')||'No major uncovered pack threat')}</div></div><div style="margin-top:9px;padding:10px 11px;border-radius:11px;background:#101a2d;border:1px solid ${e.tone}55;border-left:4px solid ${e.tone}"><div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><strong>Does your squad fit the pack strategy?</strong><span style="font-size:8px;font-weight:900;letter-spacing:.08em;line-height:1;text-transform:uppercase;color:${e.tone};border:1px solid ${e.tone}66;border-radius:999px;padding:5px 8px;white-space:nowrap">${esc(e.status)}</span></div><div class="subtle" style="margin-top:5px">${e.shields.length} strong shields · ${e.edges.length} quality edges · ${e.threats.length} major uncovered threats</div><div class="subtle" style="margin-top:5px"><b style="color:${e.tone}">Squad aim:</b> ${esc(e.summary)}</div>${e.nearTxt?`<div class="subtle" style="margin-top:5px">Nearest-rival context: ${esc(e.nearTxt)}. Chasing one rival stays secondary this early in the season.</div>`:''}</div>`;
 const tl=host.querySelector('[data-threats-leverage-board]');
 if(tl)tl.insertAdjacentElement('afterend',sec);else host.appendChild(sec);
}
function shapeCard(host,e){host.querySelector('[data-pack-shape]')?.remove();const sec=document.createElement('section');sec.className='dc-card';sec.dataset.packShape='1';sec.innerHTML=`<div class="panel-head"><div><p class="eyebrow">SQUAD VS LEAGUE PACK</p><h3>${esc(e.status)}</h3></div><span style="font-size:8px;font-weight:900;color:${e.tone};border:1px solid ${e.tone}55;border-radius:999px;padding:4px 7px">${e.shields.length} shields · ${e.edges.length} edges</span></div><p class="subtle">${esc(e.summary)}</p><div class="subtle" style="margin-top:6px"><b style="color:#60a5fa">Coverage:</b> ${esc(e.shields.slice(0,4).map(name).join(', ')||'thin')}</div><div class="subtle" style="margin-top:3px"><b style="color:#34d399">Leverage:</b> ${esc(e.edges.slice(0,4).map(name).join(', ')||'limited')}</div>${e.threats.length?`<div class="subtle" style="margin-top:3px"><b style="color:#fb7185">Missing pack threats:</b> ${esc(e.threats.slice(0,4).map(x=>name(x.p)).join(', '))}</div>`:''}`;host.prepend(sec)}
function render(){const d=window.FPLCoreData;if(!d)return;const e=evaluate(d);intelCard(document.getElementById('dc-intel-view'),e);const sh=document.getElementById('dc-shape-view');if(sh)shapeCard(sh,e);document.documentElement.dataset.packPositioningBuild=BUILD}
function settle(){[120,480,1050,1800].forEach(ms=>setTimeout(render,ms))}
function bind(){['intel','shape'].forEach(v=>document.querySelector(`#decision-nav button[data-view="${v}"]`)?.addEventListener('click',settle,{passive:true}));window.addEventListener('fplCoreDataReady',settle,{passive:true});window.addEventListener('fplSafePlanUpdated',settle,{passive:true});if(window.FPLCoreData)settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();