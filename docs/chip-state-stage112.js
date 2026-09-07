(()=>{
'use strict';
const BUILD='chip-state-stage112-20260907-0018';
const LIVE_URL='https://raw.githubusercontent.com/tlaw77/fpl/main/data/live_gameweek.json';
const INTEL_URL='https://raw.githubusercontent.com/tlaw77/fpl/main/data/squad_intelligence.json';
const ALL=[
 {key:'wildcard',short:'WC',name:'Wildcard'},
 {key:'freehit',short:'FH',name:'Free Hit'},
 {key:'bboost',short:'BB',name:'Bench Boost'},
 {key:'3xc',short:'TC',name:'Triple Captain'}
];
let live=null,intel=null,observer=null,queued=false;
const key=v=>{const x=String(v||'').toLowerCase().replace(/[\s_-]+/g,'');if(x.includes('wildcard')||x==='wc')return'wildcard';if(x.includes('freehit')||x==='fh')return'freehit';if(x.includes('benchboost')||x.includes('bboost')||x==='bb')return'bboost';if(x.includes('triplecaptain')||x.includes('3xc')||x==='tc')return'3xc';return x};
const meta=v=>ALL.find(c=>c.key===key(v))||null;
function used(){const mine=(intel?.managers||[]).find(m=>Number(m.entry_id)===Number(live?.me?.entry_id)||m.is_me),rows=(mine?.chips?.used||[]).map(x=>({...meta(x.chip),gw:Number(x.gw)||null})).filter(x=>x.key),active=meta(live?.me?.active_chip);if(active&&!rows.some(x=>x.key===active.key&&x.gw===Number(live?.gw)))rows.push({...active,gw:Number(live?.gw)||null,active:true});return rows}
function remaining(){const mine=(intel?.managers||[]).find(m=>Number(m.entry_id)===Number(live?.me?.entry_id)||m.is_me),base=Array.isArray(mine?.chips?.remaining)?mine.chips.remaining.map(meta).filter(Boolean):ALL,active=meta(live?.me?.active_chip);return base.filter(x=>x.key!==active?.key)}
function available(v){return remaining().some(x=>x.key===key(v))}
function api(){return{all:ALL,used:used(),remaining:remaining(),isAvailable:available,live}}
function renderOwn(){const host=document.getElementById('dc-team-view');if(!host||!live?.me)return;let strip=host.querySelector('[data-own-chip-status]');if(!strip){strip=document.createElement('section');strip.dataset.ownChipStatus='1';strip.className='own-chip-status';const sw=host.querySelector('.team-mode-switch');sw?.insertAdjacentElement('afterend',strip)}if(!strip.isConnected)return;const spent=new Map(used().map(x=>[x.key,x])),signature=ALL.map(c=>`${c.key}:${spent.get(c.key)?.gw||'left'}`).join('|');if(strip.dataset.inventory===signature)return;strip.dataset.inventory=signature;strip.innerHTML=`<div class="own-chip-title"><span>YOUR CHIPS</span><strong>${remaining().length} left</strong></div><div class="own-chip-list">${ALL.map(c=>{const u=spent.get(c.key);return `<span class="${u?'used':'available'}" title="${c.name}: ${u?`used in Gameweek ${u.gw}`:'available'}"><b>${c.short}</b><small>${u?`Used GW${u.gw}`:'Available'}</small></span>`}).join('')}</div>`}
function suppressUsedAdvice(){const host=document.getElementById('dc-team-view');if(!host)return;host.querySelectorAll('[data-tc-review],.captain-review-tc').forEach(el=>{if(!available('3xc'))el.style.setProperty('display','none','important');else el.style.removeProperty('display')});host.querySelectorAll('.outlook-radar>div').forEach(tile=>{const c=meta(tile.querySelector('b')?.textContent);if(!c)return;tile.classList.toggle('chip-used',!available(c.key));const span=tile.querySelector('span'),label=`Used GW${used().find(x=>x.key===c.key)?.gw||'—'}`;if(!available(c.key)&&span&&span.textContent!==label)span.textContent=label});const wc=host.querySelector('.outlook-wc-banner');if(wc){if(!available('wildcard'))wc.style.setProperty('display','none','important');else wc.style.removeProperty('display')}}
function apply(){window.FPLChipState=api();document.documentElement.dataset.tcAvailable=available('3xc')?'true':'false';renderOwn();suppressUsedAdvice();document.documentElement.dataset.chipStateBuild=BUILD}
function queue(){if(queued)return;queued=true;setTimeout(()=>{queued=false;apply()},80)}
async function load(){try{const [a,b]=await Promise.all([fetch(`${LIVE_URL}?chips112=${Date.now()}`,{cache:'no-store'}),fetch(`${INTEL_URL}?chips112=${Date.now()}`,{cache:'no-store'}).catch(()=>null)]);if(!a.ok)throw new Error(String(a.status));live=await a.json();if(b?.ok)intel=await b.json();apply();window.dispatchEvent(new CustomEvent('fplChipStateReady',{detail:api()}))}catch(e){console.warn(BUILD,e)}}
function start(){const host=document.getElementById('dc-team-view');if(host&&!observer){observer=new MutationObserver(queue);observer.observe(host,{childList:true,subtree:true})}load()}
window.addEventListener('fplLiveGameweekRendered',e=>{live=e.detail||live;apply();window.dispatchEvent(new CustomEvent('fplChipStateReady',{detail:api()}))},{passive:true});
window.addEventListener('fplCoreDataReady',queue,{passive:true});
document.querySelector('#decision-nav button[data-view="team"]')?.addEventListener('click',queue,{passive:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
