(()=>{
const q=(s,r=document)=>r.querySelector(s);
const MODES={decision:['Current decision','The active recommendation and your saved confirmation.'],compare:['Compare plans','Compare timing and transfer quantity, then select a working plan. Selecting a plan does not make a transfer in FPL.'],evidence:['Evidence','News, price timing, player reports and the reasoning behind the current decision.'],history:['History','Previous gameweek decisions and outcomes.']};
let mode='decision',queued=false,observer;
function group(el,hasSignal,hasPortfolio){
 if(el.matches('[data-transfer-layout]'))return 'navigation';
 if(el.matches('[data-executed-plan],[data-working-plan-banner]'))return 'decision';
 if(el.matches('[data-decision-signal]'))return 'decision';
 if(el.matches('#decision-history-panel,.history-panel,[data-tx-label="history"]'))return 'history';
 if(el.matches('[data-ft-portfolio]'))return 'compare';
 if(el.matches('[data-safe-routes],[data-tx-label="routes"]'))return hasPortfolio?'obsolete':'compare';
 // These older surfaces issue independent verdicts from different snapshots or heuristic scores.
 // Keep the authoritative signal as the single decision surface, without mutating model state.
 if(hasSignal&&el.matches('#gw-decision-brief,#decision-twin-card,.transfer-hero,.decision-lens,[data-tx-summary],[data-monitor="pressure"],[data-phase-mode-strip]'))return 'obsolete';
 return 'evidence';
}
function setGroup(el,value){if(el.dataset.transferGroup!==value)el.dataset.transferGroup=value}
function render(){
 const view=q('#view-transfer'),host=q('#dc-transfer-view',view);if(!view||!host)return;
 const signal=q('[data-decision-signal]',view),portfolio=q('[data-ft-portfolio]',view);
 // Do not suppress the existing fallback until a current decision has rendered.
 if(!signal)return;
 let nav=q('[data-transfer-layout]',view);
 if(!nav){nav=document.createElement('section');nav.dataset.transferLayout='1';nav.className='transfer-layout';nav.innerHTML='<div class="transfer-layout-heading"><p class="eyebrow" data-transfer-week></p><h2>Transfer planner</h2></div><nav aria-label="Transfer planner sections">'+Object.entries(MODES).map(([key,value])=>`<button type="button" data-transfer-mode="${key}" aria-pressed="${key===mode}">${value[0]}</button>`).join('')+'</nav><p data-transfer-help></p><p data-transfer-budget></p>';nav.addEventListener('click',e=>{const b=e.target.closest('[data-transfer-mode]');if(!b)return;mode=b.dataset.transferMode;render()});view.prepend(nav)}
 if(view.firstElementChild!==nav)view.prepend(nav);
 if(view.dataset.transferMode!==mode)view.dataset.transferMode=mode;
 const d=window.FPLCoreData||{},a=d.decision_synthesis?.current_action||{},gw=d.next_gw||d.decision_synthesis?.next_gw;
 const text=(selector,value)=>{const el=q(selector,nav);if(el.textContent!==value)el.textContent=value};
 text('[data-transfer-week]',gw?`PLANNING FOR GW${gw}`:'TRANSFER PLANNING');
 text('[data-transfer-help]',MODES[mode][1]);
 const ft=d.free_transfers_remaining_next_gw??a.free_transfers_remaining,bank=d.current_bank??d.me?.bank;
 text('[data-transfer-budget]',[ft!=null?`${ft} free transfer${Number(ft)===1?'':'s'} available`:null,bank!=null?`£${Number(bank).toFixed(1)}m in bank`:null].filter(Boolean).join(' · '));
 nav.querySelectorAll('[data-transfer-mode]').forEach(b=>{const value=String(b.dataset.transferMode===mode);if(b.getAttribute('aria-pressed')!==value)b.setAttribute('aria-pressed',value)});
 [...view.children].filter(el=>el!==host).forEach(el=>setGroup(el,group(el,!!signal,!!portfolio)));
 [...host.children].forEach(el=>setGroup(el,group(el,!!signal,!!portfolio)));
 // The brief's legacy metrics duplicate the heuristic leader and otherwise lack a stable selector.
 if(signal)[...host.children].filter(el=>/IMPACT OF RECOMMENDED TRANSFER|WHAT THE MODEL IMPROVES/.test(q('.eyebrow',el)?.textContent||'')).forEach(el=>setGroup(el,'obsolete'));
}
function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;render()})}
function bind(){const view=q('#view-transfer');if(!view)return;observer=new MutationObserver(schedule);observer.observe(view,{childList:true,subtree:true});['fplCoreDataReady','fplSafePlanUpdated','fplViewSettled'].forEach(ev=>window.addEventListener(ev,schedule));render()}
window.FPLTransferLayout={group,render};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
