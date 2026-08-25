(()=>{
  const KEY='fplWorkingPlanV1';
  function findButton(target){
    let n=target;
    while(n&&n!==document){
      if(n.classList&&n.classList.contains('commit-plan-route'))return n;
      n=n.parentNode;
    }
    return null;
  }
  function readPlan(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
  function savePlan(plan){
    try{
      localStorage.setItem(KEY,JSON.stringify(plan));
      window.dispatchEvent(new CustomEvent('fplPlanChanged',{detail:plan}));
      return true;
    }catch(e){console.warn('Fallback plan save failed',e);return false}
  }
  function commit(button){
    if(!button||button.dataset.commitBusy==='1')return;
    const now=Date.now();
    if(Number(button.dataset.lastCommitTap||0)&&now-Number(button.dataset.lastCommitTap)<700)return;
    button.dataset.lastCommitTap=String(now);
    const d=window.__planRenderData||window.__decisionData;
    const x=window.__planRouteIndex&&window.__planRouteIndex.get(button.dataset.key);
    if(!d||!x){button.textContent='Refresh and try again';return}
    button.dataset.commitBusy='1';
    button.disabled=true;
    const original=button.textContent;
    button.textContent='Saving…';
    try{
      let plan=(window.FPLPlan&&window.FPLPlan.reconcile&&window.FPLPlan.reconcile(d))||readPlan()||{entry_id:d.me&&d.me.entry_id,base_gw:d.current_gw,created_at:new Date().toISOString(),moves:[]};
      const base=(window.FPLPlan&&window.FPLPlan.baseRows)?window.FPLPlan.baseRows(d):(d.current_squad_next5||d.squad_next5||[]);
      const rows=(window.FPLPlan&&window.FPLPlan.apply)?window.FPLPlan.apply(base,plan):base;
      const out=rows.find(p=>p.player_id===x.out.player_id)||rows.find(p=>p.player===x.out.player)||x.out;
      if(!out)throw new Error('Outgoing player unavailable');
      if(rows.some(p=>p.player_id===x.in.player_id))throw new Error('Incoming player already owned');
      const bank=(window.FPLPlan&&window.FPLPlan.bank)?window.FPLPlan.bank(d,plan):Number(d.current_bank??d.me?.bank??0);
      if(Number(x.in.price||0)>bank+Number(out.price||0)+1e-9)throw new Error('Move is no longer affordable');
      plan.moves=Array.isArray(plan.moves)?plan.moves:[];
      plan.moves.push({kind:x.kind,committed_at:new Date().toISOString(),out:{player_id:out.player_id,player:out.player,price:out.price,position:out.position,club:out.club},in:{...x.in}});
      const ok=(window.FPLPlan&&window.FPLPlan.save)?window.FPLPlan.save(plan):savePlan(plan);
      if(ok===false)throw new Error('Browser storage blocked');
      button.textContent='Committed ✓';
      setTimeout(()=>{if(window.FPLEffective&&window.FPLEffective.sync)window.FPLEffective.sync();},50);
    }catch(e){
      console.warn('Fallback commit failed',e);
      button.disabled=false;
      button.dataset.commitBusy='0';
      button.textContent='Could not commit';
      button.title=e&&e.message?e.message:'Unable to commit';
      setTimeout(()=>{if(button.isConnected)button.textContent=original},1800);
    }
  }
  function intercept(e){
    const b=findButton(e.target);
    if(!b)return;
    if(e.cancelable)e.preventDefault();
    e.stopPropagation();
    commit(b);
  }
  document.addEventListener('touchend',intercept,{capture:true,passive:false});
  document.addEventListener('click',intercept,true);
  const style=document.createElement('style');
  style.textContent='.commit-plan-route{display:inline-flex!important;align-items:center!important;justify-content:center!important;margin-top:9px!important;border:1px solid rgba(232,255,93,.35)!important;border-radius:999px!important;padding:10px 14px!important;min-height:40px!important;background:rgba(232,255,93,.14)!important;color:#e8ff5d!important;font:800 12px/1.1 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;-webkit-appearance:none!important;appearance:none!important;touch-action:manipulation!important;pointer-events:auto!important;position:relative!important;z-index:20!important}.commit-plan-route:disabled{opacity:.72!important}';
  document.head.appendChild(style);
  window.FPLCommitFallback={commit};
})();
