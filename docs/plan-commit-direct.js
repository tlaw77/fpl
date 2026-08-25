(()=>{
  function diag(message,ok=true){
    const el=document.getElementById('ui-build-status');
    if(!el)return;
    const base=(el.textContent||'').replace(/ · COMMIT .*/, '');
    el.textContent=`${base} · COMMIT ${message}`;
    el.style.borderColor=ok?'rgba(94,234,212,.5)':'rgba(251,113,133,.65)';
    el.style.color=ok?'#9ff4df':'#fda4af';
  }
  function directCommit(button,e){
    if(e){if(e.cancelable)e.preventDefault();e.stopPropagation();}
    diag('TAP RECEIVED');
    try{
      if(!window.FPLCommitFallback?.commit){diag('CTRL MISSING',false);return false;}
      window.FPLCommitFallback.commit(button);
      setTimeout(()=>{
        try{
          const p=window.FPLPlan?.read?.()||JSON.parse(localStorage.getItem('fplWorkingPlanV1')||'null');
          if(p?.moves?.length)diag(`SAVED ${p.moves.length} MOVE${p.moves.length>1?'S':''}`);
          else diag('NOT SAVED',false);
        }catch(err){diag('STORAGE ERROR',false)}
      },180);
    }catch(err){
      console.warn('Direct commit failed',err);
      diag(`ERROR ${err?.message||'UNKNOWN'}`,false);
    }
    return false;
  }
  function wire(button){
    if(!button||button.dataset.directCommitWired==='1')return;
    button.dataset.directCommitWired='1';
    button.ontouchstart=function(e){return directCommit(button,e)};
    button.onpointerdown=function(e){if(e.pointerType==='touch')return;return directCommit(button,e)};
    button.style.webkitTapHighlightColor='transparent';
  }
  function wireAll(root=document){root.querySelectorAll?.('.commit-plan-route').forEach(wire)}
  const observer=new MutationObserver(records=>{for(const r of records)for(const n of r.addedNodes){if(n.nodeType===1){if(n.matches?.('.commit-plan-route'))wire(n);wireAll(n)}}});
  observer.observe(document.documentElement,{subtree:true,childList:true});
  wireAll();
  window.FPLDirectCommit={wireAll,directCommit};
  setTimeout(()=>{wireAll();diag('DIRECT CTRL READY')},700);
})();
