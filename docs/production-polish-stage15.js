(()=>{
const BUILD='production-polish-stage15-20260827-2115';
function stripStage(root=document){root.querySelectorAll('.eyebrow').forEach(el=>{el.textContent=el.textContent.replace(/^STAGE\s+\d+\s*·\s*/i,'').replace(/^STAGE\s+\d+$/i,'')});}
function polish(){stripStage();const foot=document.querySelector('footer');if(foot)foot.textContent='FPL Decision Centre · lightweight mobile-first build';const sub=document.getElementById('last-updated');if(sub&&/Stage\s+\d+/i.test(sub.textContent))sub.textContent='Latest decision snapshot';document.documentElement.dataset.productionPolishBuild=BUILD;}
function bind(){document.querySelectorAll('#decision-nav button').forEach(b=>b.addEventListener('click',()=>setTimeout(polish,500),{passive:true}));polish();setTimeout(polish,900);setTimeout(polish,2200)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();