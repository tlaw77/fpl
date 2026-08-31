(()=>{
const BUILD='transfer-phase-stage76-20260831-2356';
const q=(s,r=document)=>r.querySelector(s);
const DATA='https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json';
const SYN='https://raw.githubusercontent.com/tlaw77/fpl/main/data/decision_synthesis.json';
let latest=null,syn=null,loading=false;
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#039;'}[c]))}
function fixturePhase(d){
 const fs=Array.isArray(d?.current_gw_fixtures)?d.current_gw_fixtures:[];
 if(!fs.length)return{key:'unknown',label:'STATUS',title:`GW${d?.current_gw||'—'} status`,body:'Waiting for current fixture status.'};
 const live=fs.filter(f=>f.started&&!f.finished&&Number(f.minutes||0)>0&&Number(f.minutes||0)<90);
 const notStarted=fs.filter(f=>!f.started&&!f.finished);
 const awaitingFinal=fs.filter(f=>f.started&&!f.finished&&Number(f.minutes||0)>=90);
 if(live.length){const bits=[`${live.length} fixture${live.length===1?' is':'s are'} live`];if(notStarted.length)bits.push(`${notStarted.length} still to start`);if(awaitingFinal.length)bits.push(`${awaitingFinal.length} awaiting final status`);return{key:'live',label:`GW${d.current_gw} LIVE`,title:'Tracking live gameweek',body:`${bits.join(' · ')}. Scores, minutes and availability can still change the next decision.`}}
 if(notStarted.length||awaitingFinal.length){const bits=[];if(notStarted.length)bits.push(`${notStarted.length} fixture${notStarted.length===1?' is':'s are'} still to start`);if(awaitingFinal.length)bits.push(`${awaitingFinal.length} awaiting final confirmation`);return{key:'active',label:`GW${d.current_gw} ACTIVE`,title:'Observe until the gameweek completes',body:`No fixture is live right now. ${bits.join(' · ')}. Keep the GW${d.next_gw} plan provisional until the round is complete.`}}
 return{key:'between',label:`GW${d.current_gw} COMPLETE`,title:`GW${d.current_gw} → GW${d.next_gw} decision window`,body:`GW${d.current_gw} is complete. Reassess the GW${d.next_gw} plan against final outcomes, team news, market movement and the deadline.`}
}
function action(){return syn?.current_action||latest?.decision_synthesis?.current_action||null}
function routeMarkup(route){const parts=String(route||'').split('→').map(x=>x.trim());if(parts.length!==2)return `<strong>${esc(route||'Plan complete')}</strong>`;return `<strong class="txp-route"><span>${esc(parts[0])}</span><b>→</b><span>${esc(parts[1])}</span></strong>`}
function forceTop(view,sec){if(!view||!sec)return;if(view.firstElementChild!==sec)view.insertBefore(sec,view.firstElementChild||null)}
function doneState(){const act=action();return !!(act?.completed_transfer&&Number(act.completed_transfer.event)===Number(latest?.next_gw))}
function ensurePhase(view){
 const p=fixturePhase(latest||{}),act=action(),done=doneState();let sec=q('[data-transfer-phase]',view);
 if(!sec){sec=document.createElement('section');sec.className='tx-phase-card';sec.dataset.transferPhase='1'}
 forceTop(view,sec);
 let planLine='';
 if(done)planLine=`<div class="txp-plan"><span>GW${esc(latest.next_gw)} plan · completed</span>${routeMarkup(act.completed_transfer.route)}<em>Recommendation applied ✓</em></div>`;
 else if(latest?.next_gw)planLine=`<div class="txp-plan"><span>GW${esc(latest.next_gw)} plan</span><strong>Still forming</strong><em>Reassess after current results</em></div>`;
 const current=done&&act?.action==='HOLD'?`<div class="txp-now"><span>Current action</span><div class="txp-now-line"><strong>HOLD</strong>${act.confidence?`<b>${esc(act.confidence)}% confidence</b>`:''}</div><small>No further transfer. Another move costs -${esc(act.next_transfer_hit_cost||4)} unless materially new information clears the threshold.</small></div>`:'';
 sec.className=`tx-phase-card tx-phase-${p.key}`;
 sec.innerHTML=`<div class="txp-head"><div><p class="eyebrow">${esc(p.label)}</p><h2>${esc(p.title)}</h2></div><span class="txp-pill">${p.key==='live'?'OBSERVE':p.key==='between'?(done?'PLAN COMPLETE':'DECIDE'):'TRACK'}</span></div><p class="txp-body">${esc(p.body)}</p>${planLine}${current}`;
 view.classList.toggle('tx-plan-complete',done);forceTop(view,sec)
}
function suppressDuplicates(view){
 const done=doneState(),brief=q('#gw-decision-brief',view),hero=q('.transfer-hero',view);
 if(brief)brief.classList.toggle('tx-completed-duplicate',done);
 if(hero)hero.classList.toggle('tx-completed-duplicate',done);
}
function relabelDecision(view){const act=action(),lens=q('.decision-lens',view);if(!lens)return;const done=doneState(),eye=q('.eyebrow',lens),h=q('h3',lens),status=q('.decision-status',lens);if(done&&act?.action==='HOLD'){if(eye)eye.textContent='WHY HOLD';if(h)h.textContent='Why no second transfer';if(status)status.textContent='HOLD';const btn=q('#choose-roll',lens);if(btn)btn.style.display='none'}else{if(eye)eye.textContent='CURRENT ACTION'}}
function render(){const view=q('#view-transfer');if(!view||!latest)return;ensurePhase(view);suppressDuplicates(view);relabelDecision(view);forceTop(view,q('[data-transfer-phase]',view));document.documentElement.dataset.transferPhaseBuild=BUILD}
async function fetchJson(url,tag){const r=await fetch(`${url}?${tag}=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(String(r.status));return r.json()}
async function load(){if(loading)return;loading=true;try{latest=window.FPLCoreData||await fetchJson(DATA,'phase76');try{syn=await fetchJson(SYN,'phase76s')}catch{};render()}catch{}finally{loading=false}}
function burst(){[60,180,400,800,1500,3000].forEach(ms=>setTimeout(render,ms))}
function bind(){load();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',()=>{load();burst()},{passive:true});window.addEventListener('fplCoreDataReady',e=>{latest=e.detail||window.FPLCoreData||latest;burst()},{passive:true});window.addEventListener('fplSafePlanUpdated',()=>{load();burst()},{passive:true});const v=q('#view-transfer');if(v)new MutationObserver(()=>setTimeout(render,25)).observe(v,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();