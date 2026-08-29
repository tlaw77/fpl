(()=>{
const BUILD='player-explorer-squad-badges-20260829-0748';
const KEY='fplWorkingPlanV2';
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
function plan(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function badge(text,title,colour,bg,border,extra=''){const s=document.createElement('span');s.textContent=text;s.title=title;s.setAttribute('aria-label',title);s.style.cssText=`display:inline-flex;align-items:center;justify-content:center;vertical-align:2px;margin-left:6px;min-width:18px;height:18px;padding:0 5px;border-radius:999px;font-size:9px;font-weight:900;line-height:1;color:${colour};background:${bg};border:1px ${extra||'solid'} ${border};box-sizing:border-box`;return s}
function currentRows(d){return d?.current_squad_next5||d?.current_squad||d?.squad_next5||d?.squad||[]}
function confirmedIncomingNames(d){const names=new Set();const current=currentRows(d),base=d?.squad_next5||d?.squad||[],baseIds=new Set(base.map(p=>Number(p.player_id)).filter(Boolean));current.forEach(p=>{if(!baseIds.has(Number(p.player_id)))names.add(norm(p.player||p.web_name))});const tx=d?.current_squad_transfers||[];tx.forEach(t=>{const incoming=t.in||t.player_in||t.element_in||t.incoming||null;if(typeof incoming==='object')names.add(norm(incoming.player||incoming.web_name||incoming.name));});return names}
function apply(){const host=document.getElementById('gp26-rows'),d=window.FPLCoreData;if(!host||!d)return;const actualNames=new Set(currentRows(d).map(p=>norm(p.player||p.web_name)).filter(Boolean)),confirmedIn=confirmedIncomingNames(d),m=plan()?.moves?.[0],workingIn=norm(m?.in?.player),workingOut=norm(m?.out?.player);
 [...host.children].forEach(row=>{const strong=row.querySelector('strong');if(!strong)return;row.querySelectorAll('[data-squad-badge]').forEach(x=>x.remove());let raw=strong.textContent||'';const hadSquad=/\s·\sSQUAD/i.test(raw),hadIn=/\s·\sYOUR IN/i.test(raw),hadOut=/\s·\sYOUR OUT/i.test(raw);raw=raw.replace(/\s·\sSQUAD/gi,'').replace(/\s·\sYOUR IN/gi,'').replace(/\s·\sYOUR OUT/gi,'');strong.textContent=raw;const name=norm(raw.replace(/^\d+\.\s*/,'').trim());const add=(el)=>{el.dataset.squadBadge='1';strong.appendChild(el)};
 if(confirmedIn.has(name)){add(badge('↗','Confirmed transfer in','#86efac','#123326','#34d399'));}
 else if(workingIn&&name===workingIn){add(badge('↗','Working transfer in','#fcd34d','#33280f','#fbbf24','','dashed'));}
 else if(actualNames.has(name)||hadSquad){add(badge('✓','Current squad','#93c5fd','#142a44','#60a5fa'));}
 if(workingOut&&name===workingOut||hadOut)add(badge('↘','Working transfer out','#fda4af','#36151d','#fb7185'));
 if(!actualNames.has(name)&&!confirmedIn.has(name)&&!workingIn&&hadIn)add(badge('↗','Working transfer in','#fcd34d','#33280f','#fbbf24','dashed'));
 });document.documentElement.dataset.playerExplorerSquadBadgesBuild=BUILD}
function settle(){[40,180,500].forEach(ms=>setTimeout(apply,ms))}
function bind(){document.querySelector('#decision-nav button[data-view="pool"]')?.addEventListener('click',settle,{passive:true});window.addEventListener('fplSafePlanUpdated',settle);window.addEventListener('fplCoreDataReady',settle,{passive:true});['gp26-q','gp26-pos','gp26-sort'].forEach(id=>document.addEventListener(id==='gp26-q'?'input':'change',e=>{if(e.target?.id===id)settle()},{passive:true}));if(document.querySelector('.dashboard-view.active')?.id==='view-pool')settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();