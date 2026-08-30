(()=>{
const BUILD='plain-language-stage69-20260830-1735';
const RULES=[
 [/\bRival picture restored\b/gi,'Rival picture'],
 [/\bLeague Intel core restored\b/gi,'League Intel'],
 [/\bCore restored\b/gi,'Core view'],
 [/\blightweight League Intel restore\b/gi,'League Intel snapshot'],
 [/\bMarket enrichment isolated\b/gi,'Market context'],
 [/\bScout \+ Market active\b/gi,'Scout + Market'],
 [/\bremaining high-risk reintroduction\b/gi,'remaining enhancement'],
 [/\breintroduction\b/gi,'enhancement'],
 [/\bMODEL ROBUSTNESS\b/gi,'HOW STRONG IS THE ADVICE?'],
 [/\bNo extra move clears the (?:decision )?gate\b/gi,'No extra transfer looks worth making'],
 [/\bcleared the action gate\b/gi,'was strong enough to act on'],
 [/\bclears the gate\b/gi,'is strong enough to act on'],
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
 [/activation-adjusted uplift/gi,'realistic current estimate'],
 [/activation-adjusted/gi,'realistic current'],
 [/activation evidence/gi,'current evidence'],
 [/raw scout/gi,'best-case model view'],
 [/raw optimiser uplift/gi,'best-case model uplift'],
 [/raw optimizer uplift/gi,'best-case model uplift'],
 [/counterfactual/gi,'what-if view'],
 [/robustness hurdle/gi,'minimum edge needed'],
 [/portfolio inflection/gi,'latest safe chip start'],
 [/portfolio pressure/gi,'chip timing pressure'],
 [/adaptive scenario/gi,'scenario allowing for rival moves'],
 [/adaptive model/gi,'rival-move model'],
 [/rank drag from rival reactions/gi,'effect of rivals making good moves'],
 [/league leverage/gi,'mini-league context'],
 [/season maturity/gi,'season data strength'],
 [/squad churn/gi,'number of player changes'],
 [/budget confidence/gi,'budget certainty'],
 [/Wildcard-squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/Wildcard squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/simulation points/gi,'modelled points'],
 [/simulation pts/gi,'modelled points'],
 [/sim pts/gi,'modelled points'],
 [/modelled pts/gi,'modelled points'],
 [/extra TC modelled pts/gi,'extra TC modelled points'],
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
 [/\bdeep model\b/gi,'full simulation'],
 [/\bScout consensus\b/gi,'Scout view'],
 [/gain-place chance/gi,'chance of moving up'],
 [/expected league position/gi,'average projected league position'],
 [/reassess chip window/gi,'check again for the best chip week']
];
function plain(s){let out=String(s??'');for(const [re,to] of RULES)out=out.replace(re,to);return out}
function contextual(root){
 root.querySelectorAll('.outlook-card').forEach(card=>{
  const h=card.querySelector('h3');
  if(h){const m=h.textContent.trim().match(/^(HOLD|TRANSFER) has stayed the same in (\d+)%$/i);if(m)h.textContent=`The advice has stayed the same: ${m[1].toUpperCase()} (${m[2]}% of checks)`}
  card.querySelectorAll('p').forEach(p=>{const t=p.textContent.trim();const m=t.match(/^Immediate action (?:persisted|stayed the same) (\d+)%\. The (?:measured transfer leader|best alternative transfer) (?:persisted|stayed the same) (\d+)%, but (?:cleared the action gate|was strong enough to act on) in only (\d+)%\.?$/i);if(m)p.textContent=`The recommended action stayed the same in ${m[1]}% of checks. The best alternative transfer kept appearing in ${m[2]}%, but was only worth acting on in ${m[3]}%.`})
 })
}
function cleanText(root){
 if(!root)return;
 root.querySelectorAll('.eyebrow').forEach(el=>{el.textContent=el.textContent.replace(/^STAGE\s*\d+\s*·\s*/i,'').replace(/^STAGE\s*\d+\s*/i,'').trim()});
 root.querySelectorAll('section').forEach(sec=>{const eyebrow=sec.querySelector(':scope > .eyebrow, :scope > div > .eyebrow');if(eyebrow&&/stage status/i.test(eyebrow.textContent))sec.remove()});
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){const p=node.parentElement;if(!p||/^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/.test(p.tagName))return NodeFilter.FILTER_REJECT;return NodeFilter.FILTER_ACCEPT}});
 const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
 for(const node of nodes){const next=plain(node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next}
 for(const el of root.querySelectorAll('[title]')){const cur=el.getAttribute('title');const next=plain(cur);if(next!==cur)el.setAttribute('title',next)}
 contextual(root);document.documentElement.dataset.plainLanguageBuild=BUILD;
}
function run(view){const root=view||document.querySelector('.dashboard-view.active')||document.querySelector('.shell')||document.body;cleanText(root)}
function after(ms,view){setTimeout(()=>run(view),ms)}
function bind(){
 run();after(180);after(520);
 document.querySelectorAll('#decision-nav button[data-view]').forEach(b=>b.addEventListener('click',()=>{const v=document.getElementById(`view-${b.dataset.view}`);after(140,v);after(520,v)},{passive:true}));
 ['fplCoreDataReady','fplSafePlanUpdated'].forEach(ev=>window.addEventListener(ev,()=>{after(80);after(360)},{passive:true}));
 window.addEventListener('fplViewSettled',e=>run(e.detail?.view||document.querySelector('.dashboard-view.active')),{passive:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
