(()=>{
  const ORDER=['transfer','team','shape','pool','intel'];
  const MIN_X=64, MAX_Y_RATIO=0.72, MAX_MS=900;
  let start=null;

  function ensurePlayerPool(){
    const nav=document.getElementById('decision-nav');
    if(nav&&!nav.querySelector('[data-view="pool"]')){
      const b=document.createElement('button');b.dataset.view='pool';b.textContent='Player Pool';
      const intel=nav.querySelector('[data-view="intel"]');nav.insertBefore(b,intel||null);
    }
    if(!document.getElementById('view-pool')){
      const s=document.createElement('section');s.className='dashboard-view';s.id='view-pool';s.style.display='none';s.innerHTML='<div id="player-pool"><div class="panel subtle">Loading six-GW player pool…</div></div>';
      const intel=document.getElementById('view-intel');intel?.parentNode?.insertBefore(s,intel);
    }
    if(!document.querySelector('link[data-player-pool]')){const l=document.createElement('link');l.rel='stylesheet';l.href='player-pool.css?v=20260825-1631';l.dataset.playerPool='1';document.head.appendChild(l)}
    if(!document.querySelector('script[data-player-pool]')){const s=document.createElement('script');s.src='player-pool.js?v=20260825-1631';s.dataset.playerPool='1';document.body.appendChild(s)}
  }
  ensurePlayerPool();

  function interactive(el){return !!el?.closest?.('button,a,input,select,textarea,label,[contenteditable="true"],.decision-nav,.table-wrap,.matrix-wrap,.fixture-table,.chip-table,.pp-controls,[data-no-swipe]')}
  function activeView(){const a=document.querySelector('#decision-nav button.active,#decision-nav button[aria-selected="true"]');if(a?.dataset?.view)return a.dataset.view;for(const key of ORDER){const el=document.getElementById(`view-${key}`);if(!el)continue;const cs=getComputedStyle(el);if(cs.display!=='none'&&cs.visibility!=='hidden')return key}return ORDER[0]}
  function go(delta){const i=ORDER.indexOf(activeView()),next=i+delta;if(i<0||next<0||next>=ORDER.length)return;const btn=document.querySelector(`#decision-nav button[data-view="${ORDER[next]}"]`);if(!btn)return;btn.click();try{btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch{}}
  document.addEventListener('touchstart',e=>{if(e.touches.length!==1||interactive(e.target)){start=null;return}const t=e.touches[0];start={x:t.clientX,y:t.clientY,time:Date.now()}},{passive:true});
  document.addEventListener('touchend',e=>{if(!start||!e.changedTouches?.length){start=null;return}const t=e.changedTouches[0],dx=t.clientX-start.x,dy=t.clientY-start.y,dt=Date.now()-start.time;start=null;if(dt>MAX_MS||Math.abs(dx)<MIN_X||Math.abs(dy)>Math.abs(dx)*MAX_Y_RATIO)return;go(dx<0?1:-1)},{passive:true});
  document.addEventListener('touchcancel',()=>{start=null},{passive:true});
})();
