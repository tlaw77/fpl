(()=>{
const BUILD='mobile-tabs-20260829-0958';
const nav=()=>document.getElementById('decision-nav');
const buttons=()=>[...(nav()?.querySelectorAll('button[data-view]')||[])];
function currentIndex(){const bs=buttons();let i=bs.findIndex(b=>b.classList.contains('active'));if(i<0)i=bs.findIndex(b=>document.getElementById(`view-${b.dataset.view}`)?.classList.contains('active'));return i<0?0:i}
function change(dir){const bs=buttons();if(!bs.length)return;const i=currentIndex(),next=i+dir;if(next<0||next>=bs.length)return;bs[next].click();}
function horizontallyScrollable(el){for(let x=el;x&&x!==document.body;x=x.parentElement){const cs=getComputedStyle(x);if((/auto|scroll/.test(cs.overflowX)||x.hasAttribute('data-no-swipe'))&&x.scrollWidth>x.clientWidth+8)return true;}return false}
function interactive(el){return !!el?.closest?.('input,select,textarea,button,a,summary,[contenteditable="true"]')}
let sx=0,sy=0,st=0,target=null;
function onStart(e){if(e.touches?.length!==1)return;const t=e.touches[0];sx=t.clientX;sy=t.clientY;st=Date.now();target=e.target;}
function onEnd(e){if(!sx||!e.changedTouches?.length)return;const t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy,dt=Date.now()-st,start=sx; sx=sy=st=0;
 if(start<24||start>window.innerWidth-24)return;
 if(interactive(target)||horizontallyScrollable(target))return;
 if(dt>850||Math.abs(dx)<58||Math.abs(dx)<Math.abs(dy)*1.25||Math.abs(dy)>90)return;
 change(dx<0?1:-1);
}
function bind(){const shell=document.querySelector('.shell');if(!shell||shell.dataset.mobileTabsBound)return;shell.dataset.mobileTabsBound='1';shell.addEventListener('touchstart',onStart,{passive:true});shell.addEventListener('touchend',onEnd,{passive:true});document.documentElement.dataset.mobileTabsBuild=BUILD;}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
