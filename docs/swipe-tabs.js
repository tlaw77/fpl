(()=>{
  const ORDER=['transfer','team','shape','intel'];
  const MIN_X=64;
  const MAX_Y_RATIO=0.72;
  const MAX_MS=900;
  let start=null;

  function interactive(el){
    return !!el?.closest?.('button,a,input,select,textarea,label,[contenteditable="true"],.decision-nav,.table-wrap,.matrix-wrap,.fixture-table,.chip-table,[data-no-swipe]');
  }

  function activeView(){
    const activeBtn=document.querySelector('#decision-nav button.active,#decision-nav button[aria-selected="true"]');
    if(activeBtn?.dataset?.view)return activeBtn.dataset.view;
    for(const key of ORDER){
      const el=document.getElementById(`view-${key}`);
      if(!el)continue;
      const cs=getComputedStyle(el);
      if(cs.display!=='none'&&cs.visibility!=='hidden')return key;
    }
    return ORDER[0];
  }

  function go(delta){
    const current=activeView();
    const i=ORDER.indexOf(current);
    if(i<0)return;
    const next=i+delta;
    if(next<0||next>=ORDER.length)return;
    const btn=document.querySelector(`#decision-nav button[data-view="${ORDER[next]}"]`);
    if(!btn)return;
    btn.click();
    try{btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'});}catch{}
  }

  document.addEventListener('touchstart',e=>{
    if(e.touches.length!==1||interactive(e.target)){start=null;return;}
    const t=e.touches[0];
    start={x:t.clientX,y:t.clientY,time:Date.now()};
  },{passive:true});

  document.addEventListener('touchend',e=>{
    if(!start||!e.changedTouches?.length){start=null;return;}
    const t=e.changedTouches[0];
    const dx=t.clientX-start.x;
    const dy=t.clientY-start.y;
    const dt=Date.now()-start.time;
    start=null;
    if(dt>MAX_MS||Math.abs(dx)<MIN_X)return;
    if(Math.abs(dy)>Math.abs(dx)*MAX_Y_RATIO)return;
    // Finger moving left reveals the next tab; moving right returns to the previous tab.
    go(dx<0?1:-1);
  },{passive:true});

  document.addEventListener('touchcancel',()=>{start=null;},{passive:true});
})();
