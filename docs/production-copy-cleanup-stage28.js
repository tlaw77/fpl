(()=>{
const BUILD='production-copy-cleanup-stage28-20260829-2345';
const replacements=[
  [/\bRival picture restored\b/gi,'Rival picture'],
  [/\bLeague Intel core restored\b/gi,'League Intel'],
  [/\bCore restored\b/gi,'Core view'],
  [/\blightweight League Intel restore\b/gi,'League Intel snapshot'],
  [/\bMarket enrichment isolated\b/gi,'Market context'],
  [/\bScout \+ Market active\b/gi,'Scout + Market'],
  [/\bremaining high-risk reintroduction\b/gi,'remaining enhancement'],
  [/\breintroduction\b/gi,'enhancement'],
  [/\bMODEL ROBUSTNESS\b/gi,'HOW STRONG IS THE ADVICE?'],
  [/\bNo extra move clears the gate\b/gi,'No extra transfer looks worth making'],
  [/\bNo extra move clears the decision gate\b/gi,'No extra transfer looks worth making'],
  [/\bclears the gate\b/gi,'is strong enough to act on'],
  [/\bcleared the action gate\b/gi,'was strong enough to act on'],
  [/\baction gate\b/gi,'recommendation threshold'],
  [/\btransfer gate\b/gi,'transfer threshold'],
  [/\bmeasured transfer leader\b/gi,'best alternative transfer'],
  [/\bmeasured leader\b/gi,'best alternative'],
  [/\bcurrent transfer leader\b/gi,'best alternative transfer'],
  [/\bmodel support\b/gi,'model agreement'],
  [/\bmodels support\b/gi,'models agree with'],
  [/\bsame-route support\b/gi,'agreement on the same move'],
  [/\brequired edge\b/gi,'minimum improvement needed'],
  [/\bPLAN STABILITY\b/gi,'HAS THE ADVICE CHANGED?'],
  [/\bpersisted in\b/gi,'has stayed the same in'],
  [/\bpersisted\b/gi,'stayed the same'],
  [/\bpersistence\b/gi,'consistency'],
  [/\beffective evidence runs\b/gi,'meaningful checks'],
  [/\bevidence runs\b/gi,'meaningful checks'],
  [/\bFORWARD PATH\b/gi,'WHAT COULD HAPPEN NEXT?'],
  [/\bCurrent decision \+ provisional branches\b/gi,'Current advice and possible next moves'],
  [/\bprovisional branches\b/gi,'possible future moves'],
  [/\bfuture branch\b/gi,'possible later move'],
  [/\bauthoritative decision\b/gi,'current recommendation'],
  [/\bCHIP RADAR\b/gi,'CHIP OUTLOOK'],
  [/\bPreserve option value\b/gi,'Keep your options open'],
  [/\bChip scouts\b/gi,'Chip opportunities'],
  [/\bportfolio gates\b/gi,'decision checks'],
  [/\bHard deployment inflection\b/gi,'Latest safe point to start using chips'],
  [/\bWILDCARD LAB\b/gi,'WILDCARD OPTION'],
  [/\bRaw uplift\b/gi,'Projected improvement'],
  [/\braw six-GW uplift\b/gi,'projected six-GW improvement'],
  [/\braw opportunity\b/gi,'projected opportunity'],
  [/\bproxy cost\b/gi,'estimated cost'],
  [/\bproxy bank\b/gi,'estimated money left'],
  [/\bestimated budget\b/gi,'budget estimate'],
  [/\bPlanning candidate only\b/gi,'For planning only'],
  [/\bsim pts\b/gi,'modelled pts'],
  [/\bsimulation pts\b/gi,'modelled pts'],
  [/\bextra TC sim pts\b/gi,'extra modelled TC pts'],
  [/\bscore gap\b/gi,'behind the leader'],
  [/\bEdge to #2\b/gi,'Lead over #2'],
  [/\bUncertainty\b/gi,'Forecast risk'],
  [/\bCV\s*([0-9.]+)/gi,'risk $1'],
  [/\bunderlying model score\b/gi,'overall player rating'],
  [/\bXI-score points\b/gi,'team-selection rating'],
  [/\bXI score\b/gi,'team-selection rating'],
  [/\bstructural weak assets\b/gi,'clear squad problems'],
  [/\bstructural weakness\b/gi,'squad problem'],
  [/\bactivation signal\b/gi,'reason to use it now'],
  [/\bpreservation signal\b/gi,'reason to save it'],
  [/\bactivation condition\b/gi,'reason to use it'],
  [/\bseason maturity\b/gi,'season data strength'],
  [/\bdeep model\b/gi,'full simulation'],
  [/\bScout consensus\b/gi,'Scout view'],
  [/\brestored\b/gi,'']
];
function contextual(root){
  root.querySelectorAll('.outlook-card').forEach(card=>{
    const h=card.querySelector('h3');
    if(h){
      const m=h.textContent.trim().match(/^(HOLD|TRANSFER) has stayed the same in (\d+)%$/i);
      if(m)h.textContent=`The advice has stayed the same: ${m[1].toUpperCase()} (${m[2]}% of checks)`;
    }
    card.querySelectorAll('p').forEach(p=>{
      const t=p.textContent.trim();
      const m=t.match(/^Immediate action (?:persisted|stayed the same) (\d+)%\. The (?:measured transfer leader|best alternative transfer) (?:persisted|stayed the same) (\d+)%, but (?:cleared the action gate|was strong enough to act on) in only (\d+)%\.?$/i);
      if(m)p.textContent=`The recommended action stayed the same in ${m[1]}% of checks. The best alternative transfer kept appearing in ${m[2]}%, but was only worth acting on in ${m[3]}%.`;
    });
  });
}
function cleanText(root){
  if(!root)return;
  root.querySelectorAll('.eyebrow').forEach(el=>{
    el.textContent=el.textContent.replace(/^STAGE\s*\d+\s*·\s*/i,'').replace(/^STAGE\s*\d+\s*/i,'').trim();
  });
  root.querySelectorAll('section').forEach(sec=>{
    const eyebrow=sec.querySelector(':scope > .eyebrow, :scope > div > .eyebrow');
    if(eyebrow&&/stage status/i.test(eyebrow.textContent))sec.remove();
  });
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){const p=node.parentElement;if(!p||['SCRIPT','STYLE','NOSCRIPT','TEXTAREA'].includes(p.tagName))return NodeFilter.FILTER_REJECT;return NodeFilter.FILTER_ACCEPT}});
  const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
  nodes.forEach(node=>{
    let t=node.nodeValue;
    replacements.forEach(([re,to])=>{t=t.replace(re,to)});
    node.nodeValue=t.replace(/\s{2,}/g,' ');
  });
  contextual(root);
}
let cleaning=false,observer=null,timer=null;
function cleanAll(){if(cleaning)return;cleaning=true;document.querySelectorAll('.dashboard-view').forEach(cleanText);document.documentElement.dataset.productionCopyCleanupBuild=BUILD;setTimeout(()=>{cleaning=false},0)}
function schedule(){[0,160,420,900].forEach(ms=>setTimeout(cleanAll,ms))}
function watch(){if(observer)return;observer=new MutationObserver(()=>{if(cleaning)return;clearTimeout(timer);timer=setTimeout(cleanAll,120)});observer.observe(document.body,{childList:true,subtree:true})}
function bind(){schedule();watch();document.querySelectorAll('#decision-nav button').forEach(b=>b.addEventListener('click',schedule,{passive:true}));window.addEventListener('fplSafePlanUpdated',schedule);window.addEventListener('fplCoreDataReady',schedule)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();