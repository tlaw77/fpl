(()=>{
const BUILD='transfer-choice-toggle-20260829-1048';
const KEY='fplWorkingPlanV2';
function isSelected(btn){return btn?.matches?.('[data-transfer-choice]')&&(btn.dataset.selected==='1'||/your choice/i.test(btn.textContent||''));}
function clearChoice(btn){try{
 localStorage.removeItem(KEY);
 btn.dataset.selected='0';
 btn.textContent='Choose this route';
 btn.style.background='#172033';
 btn.style.color='#cbd5e1';
 btn.style.borderColor='#475569';
 window.dispatchEvent(new CustomEvent('fplSafePlanUpdated',{detail:{version:'safe-manual-v3',updated_at:new Date().toISOString(),moves:[]}}));
 document.documentElement.dataset.transferChoiceToggleBuild=BUILD;
}catch{btn.textContent='Could not clear';}}
function onClick(e){const btn=e.target?.closest?.('[data-transfer-choice]');if(!isSelected(btn))return;e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();clearChoice(btn);}
document.addEventListener('click',onClick,true);
document.documentElement.dataset.transferChoiceToggleBuild=BUILD;
})();
