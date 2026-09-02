(()=>{
const BUILD='league-intel-priority-stage51-20260902-1510';
/* Ordering is now owned by league-intel-phase-stage91.js.
   This compatibility stage deliberately performs no DOM reordering. */
function mark(){document.documentElement.dataset.leagueIntelPriorityBuild=BUILD}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mark,{once:true});else mark();
})();
