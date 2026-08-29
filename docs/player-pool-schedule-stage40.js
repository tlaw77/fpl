(()=>{
const BUILD='player-pool-schedule-20260829-1038';
const BASE='https://raw.githubusercontent.com/tlaw77/fpl/main/data/';
let schedule=null,loading=null;
const DAY=86400000;
function clubFor(row){const sub=[...row.querySelectorAll('.subtle')].find(x=>/ · (GKP|DEF|MID|FWD) · /.test(x.textContent||''));return (sub?.textContent||'').split(' · ')[0].trim()}
function removeLongSchedule(row){
  const walker=document.createTreeWalker(row,NodeFilter.SHOW_TEXT);const nodes=[];let node;
  while((node=walker.nextNode()))nodes.push(node);
  nodes.forEach(x=>{const t=x.nodeValue||'';if(/Schedule:\s*\d+\s+non-PL\s+club\s+fixture/i.test(t)||/Schedule:.*6-GW\s+horizon/i.test(t))x.nodeValue=t.replace(/\s*Schedule:\s*\d+\s+non-PL\s+club\s+fixture(?:s)?\s+in\s+6-GW\s+horizon\s*/ig,'').replace(/\s*Schedule:.*?6-GW\s+horizon\s*/ig,'')});
  [...row.querySelectorAll('*')].forEach(el=>{const own=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.nodeValue||'').join('').trim();if(/^Schedule:/i.test(own)&&/6-GW\s+horizon/i.test(el.textContent||''))el.remove()});
}
function nearEvent(club){const rows=schedule?.clubs?.[club]||[],now=Date.now();return rows.map(x=>({...x,ts:new Date(x.date).getTime()})).filter(x=>Number.isFinite(x.ts)&&x.ts>=now&&x.ts<=now+8*DAY).sort((a,b)=>a.ts-b.ts)[0]||null}
function pillText(ev){const days=Math.max(0,Math.ceil((ev.ts-Date.now())/DAY));return days<=1?'MIDWEEK NEXT':`MIDWEEK ${days}D`}
function apply(){const host=document.getElementById('gp26-rows');if(!host)return;[...host.children].forEach(row=>{removeLongSchedule(row);row.querySelector('[data-short-schedule]')?.remove();if(!schedule)return;const club=clubFor(row),ev=nearEvent(club);if(!ev)return;const top=row.firstElementChild;if(!top)return;const right=top.lastElementChild;const p=document.createElement('span');p.dataset.shortSchedule='1';p.title=`${ev.competition}: ${ev.name}`;p.textContent=pillText(ev);p.style.cssText='display:inline-flex;margin-left:6px;padding:3px 6px;border-radius:999px;border:1px solid #fbbf2455;background:#2b230f;color:#fcd34d;font-size:7px;font-weight:900;white-space:nowrap;vertical-align:middle';if(right)right.appendChild(p);else top.appendChild(p)});document.documentElement.dataset.playerPoolScheduleBuild=BUILD}
async function load(){if(schedule){apply();return}if(loading)return loading;loading=(async()=>{const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),8000);try{const r=await fetch(`${BASE}schedule_load.json?ps40=${Date.now()}`,{cache:'no-store',signal:ctl.signal});schedule=r.ok?await r.json():{clubs:{}};apply()}catch{schedule={clubs:{}};apply()}finally{clearTimeout(t);loading=null}})();return loading}
function settle(){[30,120,350,800,1500].forEach(ms=>setTimeout(apply,ms));load()}
function bind(){document.querySelector('#decision-nav button[data-view="pool"]')?.addEventListener('click',settle,{passive:true});document.addEventListener('input',e=>{if(e.target?.id==='gp26-q')setTimeout(apply,80)},{passive:true});document.addEventListener('change',e=>{if(e.target?.id==='gp26-pos'||e.target?.id==='gp26-sort')setTimeout(apply,80)},{passive:true});window.addEventListener('fplCoreDataReady',settle,{passive:true});window.addEventListener('fplSafePlanUpdated',settle,{passive:true});if(document.querySelector('.dashboard-view.active')?.id==='view-pool')settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();