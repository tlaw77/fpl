(()=>{
const BUILD='league-matrix-mobile-compact-stage67-20260830-0018';
function matrixSection(){return [...document.querySelectorAll('#view-intel .dc-card')].find(s=>/MANAGER MATRIX/i.test(s.querySelector('.eyebrow')?.textContent||''));}
function compact(){
  const sec=matrixSection();
  if(!sec||window.innerWidth>760)return;
  const scoreMode=/SCORE BUILD-UP/i.test(sec.querySelector('.eyebrow')?.textContent||'');
  const left=28, manager=112, gap=2, cell=scoreMode?46:23;
  const grids=[...sec.querySelectorAll('div')].filter(el=>el.style?.gridTemplateColumns&&/32px\s+146px/.test(el.style.gridTemplateColumns));
  grids.forEach(grid=>{
    let g=grid.style.gridTemplateColumns;
    g=g.replace(/^32px\s+146px\s+/,`${left}px ${manager}px `);
    g=g.replace(/repeat\(([^,]+),\s*52px\)/,`repeat($1, ${cell}px)`);
    g=g.replace(/repeat\(([^,]+),\s*24px\)/,`repeat($1, ${cell}px)`);
    grid.style.gridTemplateColumns=g;
    grid.style.gap=`${gap}px`;
    const kids=[...grid.children];
    if(kids[1]){
      kids[1].style.left=`${left+gap}px`;
      kids[1].style.paddingLeft='2px';
      kids[1].style.paddingRight='2px';
      kids[1].style.maxWidth=`${manager}px`;
      kids[1].style.boxSizing='border-box';
      kids[1].setAttribute('title',kids[1].innerText.replace(/\n+/g,' · ').trim());
      const team=kids[1].querySelector('strong');
      const mgr=kids[1].querySelector('span');
      if(team){team.style.fontSize='7.5px';team.style.maxWidth='106px';}
      if(mgr){mgr.style.fontSize='6px';mgr.style.maxWidth='106px';}
    }
    if(kids[0])kids[0].style.width='26px';
    if(scoreMode){
      kids.slice(2).forEach(cellEl=>{
        cellEl.style.width='44px';
        cellEl.style.maxWidth='44px';
        const nm=cellEl.querySelector('span');
        if(nm){nm.style.maxWidth='40px';nm.style.fontSize='5.5px';}
      });
    }
  });
  const scroller=sec.querySelector('div[style*="overflow-x: auto"],div[style*="overflow-x:auto"]');
  if(scroller){scroller.style.marginLeft='-2px';scroller.style.paddingRight='0';}
  document.documentElement.dataset.leagueMatrixCompactBuild=BUILD;
}
function schedule(){[0,120,350,800,1500].forEach(ms=>setTimeout(compact,ms));}
function bind(){schedule();window.addEventListener('resize',schedule,{passive:true});window.addEventListener('fplCoreDataReady',schedule,{passive:true});document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',schedule,{passive:true});const root=document.getElementById('view-intel');if(root)new MutationObserver(schedule).observe(root,{childList:true,subtree:true});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();