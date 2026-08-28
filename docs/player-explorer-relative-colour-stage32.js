(()=>{
const BUILD='player-explorer-relative-colour-20260828-2358';
const GOOD='#34d399',MID='#fbbf24',BAD='#fb7185',SHIELD='#60a5fa',NEUTRAL='#94a3b8';
const num=s=>{const m=String(s||'').replace(/,/g,'').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):NaN};
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
let poolData=window.FPLPlayerPoolData||null;
const originalFetch=window.fetch.bind(window);
window.fetch=(...args)=>{const p=originalFetch(...args);const url=String(args?.[0]||'');if(url.includes('player_pool.json'))p.then(r=>r.clone().json()).then(d=>{poolData=d;window.FPLPlayerPoolData=d;setTimeout(refresh,20)}).catch(()=>{});return p};
function toneByRank(value,values){const clean=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!Number.isFinite(value)||clean.length<4)return NEUTRAL;const q1=clean[Math.floor((clean.length-1)*.33)],q2=clean[Math.floor((clean.length-1)*.67)];return value>=q2?GOOD:value>=q1?MID:BAD}
function eoTone(v){if(!Number.isFinite(v))return NEUTRAL;if(v<30)return GOOD;if(v>=70)return SHIELD;return MID}
function cells(row){const metricWrap=[...row.querySelectorAll('div')].find(d=>d.style?.gridTemplateColumns?.includes('repeat(5')));return metricWrap?[...metricWrap.children].slice(0,5):[]}
function rowName(row){const raw=row.querySelector('strong')?.textContent||'';return raw.replace(/^\d+\.\s*/,'').split(' · ')[0].trim()}
function playerMap(){return new Map((poolData?.players||[]).map(p=>[norm(p.player),p]))}
function workloadTone(p){if(p?.schedule_risk==='High')return BAD;if(p?.schedule_risk==='Medium')return MID;return GOOD}
function applyWorkload(rows){if(!poolData)return;const pm=playerMap();rows.forEach(row=>{const p=pm.get(norm(rowName(row)));if(!p)return;const cs=cells(row),minuteCell=cs[2];if(minuteCell&&p.adjusted_availability!=null){const pct=Math.round(Number(p.adjusted_availability)*100),b=minuteCell.querySelector('b'),bar=minuteCell.querySelector('i');if(b)b.textContent=`${pct}%`;if(bar)bar.style.width=`${Math.max(0,Math.min(100,pct))}%`;minuteCell.title=p.schedule_note||'Adjusted minutes outlook'}
 let note=row.querySelector('[data-workload-note]');const meaningful=p.player_workload_observed||p.schedule_risk==='High'||p.schedule_risk==='Medium'||(p.extra_club_fixtures_6gw||0)>0;if(!meaningful){note?.remove();return}if(!note){note=document.createElement('div');note.dataset.workloadNote='1';note.style.cssText='font-size:8px;margin-top:4px;line-height:1.35';const head=row.firstElementChild;head?.appendChild(note)}const prefix=p.player_workload_observed?'Workload':'Schedule';note.textContent=`${prefix}: ${p.schedule_note||'fixture load monitored'}`;note.style.color=workloadTone(p);});}
function apply(){const host=document.getElementById('gp26-rows');if(!host)return;const rows=[...host.children].filter(x=>x.querySelector('strong'));applyWorkload(rows);
 const parsed=rows.map(row=>{const cs=cells(row);return{row,cs,vals:cs.map(c=>num(c.querySelector('b')?.textContent))}}).filter(x=>x.cs.length===5);
 if(!parsed.length)return;
 const cols=[0,1,2,3].map(i=>parsed.map(x=>x.vals[i]));
 parsed.forEach(x=>x.cs.forEach((c,i)=>{const v=x.vals[i],colour=i===4?eoTone(v):toneByRank(v,cols[i]);const b=c.querySelector('b'),bar=c.querySelector('i');if(b){b.style.color=colour;b.style.fontWeight='900'}if(bar){bar.style.background=colour;bar.style.opacity='1'}if(i!==2||!c.title)c.title=i===4?(v<30?'Low ownership: leverage opportunity':v>=70?'High ownership: shield/coverage':'Mid ownership: neutral context'):(colour===GOOD?'Strong relative to the visible comparison set':colour===MID?'Middle of the visible comparison set':colour===BAD?'Weak relative to the visible comparison set':'Relative context unavailable') }));
 document.documentElement.dataset.playerExplorerRelativeColourBuild=BUILD;
}
function bindControls(){const host=document.getElementById('dc-pool-view');if(!host)return;['gp26-q','gp26-pos','gp26-sort'].forEach(id=>{const el=document.getElementById(id);if(!el||el.dataset.relativeColourBound)return;el.dataset.relativeColourBound='1';el.addEventListener(id==='gp26-q'?'input':'change',()=>setTimeout(apply,25),{passive:true})})}
function refresh(){setTimeout(()=>{bindControls();apply()},250);setTimeout(()=>{bindControls();apply()},800)}
function bind(){document.querySelector('#decision-nav button[data-view="pool"]')?.addEventListener('click',refresh,{passive:true});window.addEventListener('fplSafePlanUpdated',refresh);if(document.querySelector('.dashboard-view.active')?.id==='view-pool')refresh()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();