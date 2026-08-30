(()=>{
const BUILD='plain-language-stage69-20260830-1045';
const RULES=[
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
 [/season maturity/gi,'amount of season evidence'],
 [/squad churn/gi,'number of player changes'],
 [/budget confidence/gi,'budget certainty'],
 [/Wildcard-squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/Wildcard squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/squad persistence/gi,'how often the same Wildcard squad stays best'],
 [/simulation points/gi,'modelled points'],
 [/sim pts/gi,'modelled pts'],
 [/gain-place chance/gi,'chance of moving up'],
 [/expected league position/gi,'average projected league position'],
 [/reassess chip window/gi,'check again for the best chip week']
];
function plain(s){let out=String(s??'');for(const [re,to] of RULES)out=out.replace(re,to);return out}
function cleanText(root){
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){const p=node.parentElement;if(!p||/^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/.test(p.tagName))return NodeFilter.FILTER_REJECT;return NodeFilter.FILTER_ACCEPT}});
 const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
 for(const node of nodes){const next=plain(node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next}
 for(const el of root.querySelectorAll('[title]')){const next=plain(el.getAttribute('title'));if(next!==el.getAttribute('title'))el.setAttribute('title',next)}
 document.documentElement.dataset.plainLanguageBuild=BUILD;
}
let timer=null,observer=null;
function run(){const root=document.querySelector('.shell')||document.body;if(root)cleanText(root)}
function watch(){const root=document.querySelector('.shell')||document.body;if(!root||observer)return;observer=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(run,60)});observer.observe(root,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['title']})}
function bind(){run();watch();[120,350,900,1800].forEach(ms=>setTimeout(run,ms));['fplCoreDataReady','fplSafePlanUpdated'].forEach(ev=>window.addEventListener(ev,()=>setTimeout(run,80),{passive:true}))}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
