(()=>{
const BUILD='production-copy-cleanup-stage27-20260828-1750';
const replacements=[
  [/\bRival picture restored\b/gi,'Rival picture'],
  [/\bLeague Intel core restored\b/gi,'League Intel'],
  [/\bCore restored\b/gi,'Core view'],
  [/\brestored\b/gi,''],
  [/\blightweight League Intel restore\b/gi,'League Intel snapshot'],
  [/\bMarket enrichment isolated\b/gi,'Market context'],
  [/\bScout \+ Market active\b/gi,'Scout + Market'],
  [/\bremaining high-risk reintroduction\b/gi,'remaining enhancement'],
  [/\breintroduction\b/gi,'enhancement']
];
function cleanText(root){
  if(!root)return;
  root.querySelectorAll('.eyebrow').forEach(el=>{
    el.textContent=el.textContent.replace(/^STAGE\s*\d+\s*·\s*/i,'').replace(/^STAGE\s*\d+\s*/i,'').trim();
  });
  root.querySelectorAll('section').forEach(sec=>{
    const eyebrow=sec.querySelector(':scope > .eyebrow, :scope > div > .eyebrow');
    if(eyebrow&&/stage status/i.test(eyebrow.textContent))sec.remove();
  });
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
  nodes.forEach(node=>{
    let t=node.nodeValue;
    replacements.forEach(([re,to])=>{t=t.replace(re,to)});
    t=t.replace(/\s{2,}/g,' ');
    node.nodeValue=t;
  });
}
function cleanAll(){document.querySelectorAll('.dashboard-view').forEach(cleanText);document.documentElement.dataset.productionCopyCleanupBuild=BUILD}
function schedule(){[0,250,700,1400].forEach(ms=>setTimeout(cleanAll,ms))}
function bind(){schedule();document.querySelectorAll('#decision-nav button').forEach(b=>b.addEventListener('click',schedule,{passive:true}));window.addEventListener('fplSafePlanUpdated',schedule)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();