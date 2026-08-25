(()=>{
  const DUP_MS=700;
  function status(msg,ok=true){
    const el=document.getElementById('ui-build-status');
    if(!el)return;
    const base=(el.textContent||'').replace(/ · BIND V28 .*/, '');
    el.textContent=`${base} · BIND V28 ${msg}`;
    el.style.color=ok?'#9ff4df':'#fda4af';
  }
  function activate(button,e){
    if(e&&e.cancelable)e.preventDefault();
    if(e)e.stopPropagation();
    const now=Date.now();
    if(now-Number(button.dataset.v28Last||0)<DUP_MS)return false;
    button.dataset.v28Last=String(now);
    status('TAP RECEIVED');
    if(!window.FPLPlan||typeof window.FPLPlan.commitRoute!=='function'){
      status('PLAN API MISSING',false);
      return false;
    }
    try{
      return window.FPLPlan.commitRoute(button);
    }catch(err){
      status(`ERROR ${err&&err.message?err.message:'UNKNOWN'}`,false);
      return false;
    }
  }
  function bind(button){
    if(!button||button.dataset.v28Bound==='1')return;
    button.dataset.v28Bound='1';
    button.removeAttribute('onclick');
    button.onclick=null;
    button.style.pointerEvents='auto';
    button.style.touchAction='manipulation';
    button.style.position='relative';
    button.style.zIndex='9999';
    button.addEventListener('pointerdown',()=>status('PRESS RECEIVED'),{passive:true});
    button.addEventListener('touchend',e=>activate(button,e),{passive:false});
    button.addEventListener('click',e=>activate(button,e),false);
  }
  function bindAll(root=document){
    if(root.matches&&root.matches('.commit-plan-route'))bind(root);
    if(root.querySelectorAll)root.querySelectorAll('.commit-plan-route').forEach(bind);
  }
  const observer=new MutationObserver(records=>{
    for(const r of records)for(const n of r.addedNodes)if(n&&n.nodeType===1)bindAll(n);
  });
  observer.observe(document.documentElement,{subtree:true,childList:true});
  bindAll();
  setTimeout(()=>{bindAll();status('READY')},500);
  window.FPLButtonBindV28={bindAll};
})();