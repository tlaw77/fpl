(()=>{
const BUILD='post-render-stabilizer-stage27-20260828-1438';
function bindOne(view,delay){const b=document.querySelector(`#decision-nav button[data-view="${view}"]`);if(!b)return;b.addEventListener('click',e=>{if(!e.isTrusted)return;setTimeout(()=>{if(document.getElementById(`view-${view}`)?.classList.contains('active'))b.click()},delay)},{passive:true})}
function bind(){bindOne('pool',2300);bindOne('shape',1100);bindOne('intel',1200);document.documentElement.dataset.postRenderStabilizerBuild=BUILD}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();