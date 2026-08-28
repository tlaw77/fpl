(()=>{
const BUILD='player-explorer-relative-colour-20260828-2248';
const GOOD='#34d399',MID='#fbbf24',BAD='#fb7185',SHIELD='#60a5fa',NEUTRAL='#94a3b8';
const num=s=>{const m=String(s||'').replace(/,/g,'').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):NaN};
function toneByRank(value,values){const clean=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!Number.isFinite(value)||clean.length<4)return NEUTRAL;const q1=clean[Math.floor((clean.length-1)*.33)],q2=clean[Math.floor((clean.length-1)*.67)];return value>=q2?GOOD:value>=q1?MID:BAD}
function eoTone(v){if(!Number.isFinite(v))return NEUTRAL;if(v<30)return GOOD;if(v>=70)return SHIELD;return MID}
function cells(row){const metricWrap=[...row.querySelectorAll('div')].find(d=>d.style?.gridTemplateColumns?.includes('repeat(5')));return metricWrap?[...metricWrap.children].slice(0,5):[]}
function apply(){const host=document.getElementById('gp26-rows');if(!host)return;const rows=[...host.children].filter(x=>x.querySelector('strong'));
 const parsed=rows.map(row=>{const cs=cells(row);return{row,cs,vals:cs.map(c=>num(c.querySelector('b')?.textContent))}}).filter(x=>x.cs.length===5);
 if(!parsed.length)return;
 const cols=[0,1,2,3].map(i=>parsed.map(x=>x.vals[i]));
 parsed.forEach(x=>x.cs.forEach((c,i)=>{const v=x.vals[i],colour=i===4?eoTone(v):toneByRank(v,cols[i]);const b=c.querySelector('b'),bar=c.querySelector('i');if(b){b.style.color=colour;b.style.fontWeight='900'}if(bar){bar.style.background=colour;bar.style.opacity='1'}c.title=i===4?(v<30?'Low ownership: leverage opportunity':v>=70?'High ownership: shield/coverage':'Mid ownership: neutral context'):(colour===GOOD?'Strong relative to the visible comparison set':colour===MID?'Middle of the visible comparison set':colour===BAD?'Weak relative to the visible comparison set':'Relative context unavailable') }));
 document.documentElement.dataset.playerExplorerRelativeColourBuild=BUILD;
}
function bindControls(){const host=document.getElementById('dc-pool-view');if(!host)return;['gp26-q','gp26-pos','gp26-sort'].forEach(id=>{const el=document.getElementById(id);if(!el||el.dataset.relativeColourBound)return;el.dataset.relativeColourBound='1';el.addEventListener(id==='gp26-q'?'input':'change',()=>setTimeout(apply,25),{passive:true})})}
function refresh(){setTimeout(()=>{bindControls();apply()},250);setTimeout(()=>{bindControls();apply()},800)}
function bind(){document.querySelector('#decision-nav button[data-view="pool"]')?.addEventListener('click',refresh,{passive:true});window.addEventListener('fplSafePlanUpdated',refresh);if(document.querySelector('.dashboard-view.active')?.id==='view-pool')refresh()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();