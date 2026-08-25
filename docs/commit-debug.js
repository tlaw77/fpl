(()=>{
  const BUILD='29';
  const MAX=24;
  const logs=[];
  let panel,logEl,statusEl,testBtn;
  const ts=()=>new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  function short(el){
    if(!el)return 'null';
    const id=el.id?`#${el.id}`:'';
    const cls=el.classList&&el.classList.length?'.'+[...el.classList].slice(0,3).join('.'):'';
    return `${el.tagName||el.nodeName}${id}${cls}`;
  }
  function push(msg){
    logs.push(`${ts()} ${msg}`); if(logs.length>MAX)logs.shift();
    if(logEl)logEl.textContent=logs.join('\n');
  }
  function storageProbe(){
    try{const k='__fpl_debug29__';localStorage.setItem(k,'ok');const v=localStorage.getItem(k);localStorage.removeItem(k);return v==='ok'?'OK':'READBACK_FAIL'}catch(e){return `ERR:${e.name}`}
  }
  function inspectButton(){
    const b=document.querySelector('.commit-plan-route');
    if(!b)return 'button:missing';
    const r=b.getBoundingClientRect(); const cs=getComputedStyle(b);
    const cx=Math.max(0,Math.min(innerWidth-1,r.left+r.width/2));
    const cy=Math.max(0,Math.min(innerHeight-1,r.top+r.height/2));
    const hit=(cy>=0&&cy<innerHeight)?document.elementFromPoint(cx,cy):null;
    return `button:${short(b)} rect=${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)}x${Math.round(r.height)} pe=${cs.pointerEvents} z=${cs.zIndex} vis=${cs.visibility}/${cs.display} hitCenter=${short(hit)} key=${b.dataset.key||'none'}`;
  }
  function renderPanel(){
    panel=document.createElement('section');
    panel.id='fpl-commit-debug';
    panel.innerHTML=`<div class="dbg-head"><strong>COMMIT DEBUG ${BUILD}</strong><button id="dbg-close" type="button">×</button></div><div id="dbg-status"></div><div class="dbg-actions"><button id="dbg-test" type="button">DEBUG TAP TEST</button><button id="dbg-inspect" type="button">INSPECT COMMIT</button><button id="dbg-storage" type="button">TEST STORAGE</button><button id="dbg-clear" type="button">CLEAR LOG</button></div><pre id="dbg-log"></pre>`;
    document.body.appendChild(panel);
    const st=document.createElement('style');
    st.textContent=`#fpl-commit-debug{position:fixed;left:8px;right:8px;bottom:8px;z-index:2147483646;background:#07111f;color:#d9f5ff;border:1px solid #35d0ba;border-radius:12px;padding:9px;font:11px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;box-shadow:0 8px 30px rgba(0,0,0,.45);max-height:44vh;overflow:auto}#fpl-commit-debug .dbg-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}#fpl-commit-debug button{appearance:none;-webkit-appearance:none;border:1px solid rgba(255,255,255,.25);background:#13243a;color:#fff;border-radius:8px;padding:8px 10px;font-weight:800;touch-action:manipulation;pointer-events:auto;position:relative;z-index:2147483647}#fpl-commit-debug .dbg-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0}#dbg-log{white-space:pre-wrap;word-break:break-word;margin:6px 0 0;max-height:21vh;overflow:auto;background:#030913;padding:6px;border-radius:8px}#dbg-status{color:#9ff4df}.commit-plan-route{pointer-events:auto!important;touch-action:manipulation!important;position:relative!important;z-index:9999!important}`;
    document.head.appendChild(st);
    statusEl=panel.querySelector('#dbg-status');logEl=panel.querySelector('#dbg-log');testBtn=panel.querySelector('#dbg-test');
    panel.querySelector('#dbg-close').onclick=()=>panel.remove();
    panel.querySelector('#dbg-clear').onclick=()=>{logs.length=0;push('log cleared')};
    panel.querySelector('#dbg-storage').onclick=()=>push(`storage ${storageProbe()}`);
    panel.querySelector('#dbg-inspect').onclick=()=>push(inspectButton());
    testBtn.addEventListener('pointerdown',e=>push(`DEBUG BTN pointerdown ${e.pointerType}`));
    testBtn.addEventListener('touchstart',()=>push('DEBUG BTN touchstart'),{passive:true});
    testBtn.addEventListener('touchend',()=>push('DEBUG BTN touchend'),{passive:true});
    testBtn.addEventListener('click',()=>push('DEBUG BTN click'));
    statusEl.textContent=`storage ${storageProbe()} · FPLPlan ${window.FPLPlan?'READY':'MISSING'} · routeIndex ${window.__planRouteIndex?'READY':'MISSING'}`;
    push('debug panel ready'); push(inspectButton());
  }
  function eventPoint(e){
    const t=e.changedTouches&&e.changedTouches[0]||e.touches&&e.touches[0];
    return t?{x:t.clientX,y:t.clientY}:{x:e.clientX,y:e.clientY};
  }
  ['pointerdown','pointerup','touchstart','touchend','click'].forEach(type=>{
    document.addEventListener(type,e=>{
      const b=e.target&&e.target.closest?e.target.closest('.commit-plan-route'):null;
      if(!b)return;
      const p=eventPoint(e); const hit=(p&&Number.isFinite(p.x)&&Number.isFinite(p.y))?document.elementFromPoint(p.x,p.y):null;
      push(`COMMIT ${type} target=${short(e.target)} hit=${short(hit)} key=${b.dataset.key||'none'}`);
    },true);
  });
  window.addEventListener('error',e=>push(`ERROR ${e.message||'unknown'} @${e.filename||''}:${e.lineno||''}`));
  window.addEventListener('unhandledrejection',e=>push(`REJECTION ${e.reason&&e.reason.message||String(e.reason)}`));
  window.addEventListener('fplPlanChanged',e=>push(`fplPlanChanged moves=${e.detail&&e.detail.moves?e.detail.moves.length:0}`));
  const oldSet=Storage.prototype.setItem;
  Storage.prototype.setItem=function(k,v){if(k==='fplWorkingPlanV2')push(`localStorage.setItem ${k} bytes=${String(v).length}`);return oldSet.call(this,k,v)};
  window.FPLCommitDebug={push,inspectButton,storageProbe};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',renderPanel);else renderPanel();
})();
