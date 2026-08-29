(()=>{
const BUILD='tab-state-stage37-20260829-1004';
const KEY='fplActiveDecisionTab';
const VALID=new Set(['transfer','team','shape','pool','intel']);
function save(key){if(!VALID.has(key))return;try{sessionStorage.setItem(KEY,key)}catch{}}
function restore(){let key='transfer';try{key=sessionStorage.getItem(KEY)||'transfer'}catch{}if(!VALID.has(key))key='transfer';const b=document.querySelector(`#decision-nav button[data-view="${key}"]`);if(b&&!b.classList.contains('active'))b.click();}
function bind(){document.querySelectorAll('#decision-nav button[data-view]').forEach(b=>{if(b.dataset.tabStateBound)return;b.dataset.tabStateBound='1';b.addEventListener('click',()=>save(b.dataset.view),{passive:true})});setTimeout(restore,40);setTimeout(restore,220);document.documentElement.dataset.tabStateBuild=BUILD}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();