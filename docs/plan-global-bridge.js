var FPLPlan = window.FPLPlan;
(function(){
  var el=document.getElementById('ui-build-status');
  if(el){
    var storage='OK';
    try{var k='__fpl_bridge__';localStorage.setItem(k,'1');localStorage.removeItem(k)}catch(e){storage='BLOCKED'}
    el.textContent='UI BUILD 27 · PLAN V2 '+(window.FPLPlan?'READY':'MISSING')+' · GLOBAL BRIDGE '+(typeof FPLPlan!=='undefined'&&FPLPlan?'READY':'MISSING')+' · STORAGE '+storage+' · COMMIT WAITING';
    el.style.color=(window.FPLPlan&&typeof FPLPlan!=='undefined'&&FPLPlan&&storage==='OK')?'#9ff4df':'#fda4af';
  }
})();
