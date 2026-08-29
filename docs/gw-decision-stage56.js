(()=>{
const BUILD='gw-decision-20260829-1950';
const q=(s,r=document)=>r.querySelector(s);
const qa=(s,r=document)=>[...r.querySelectorAll(s)];
const text=el=>String(el?.textContent||'').replace(/\s+/g,' ').trim();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function transferState(){
 const view=q('#view-transfer');
 const hero=q('.transfer-hero,.dc-recommendation',view);
 const full=text(view);
 const title=text(q('h2',hero));
 const tag=text(q('.transfer-hero-tag',hero));
 const evidence=text(q('.transfer-evidence h3,[data-stage9-evidence] h3',view));
 const roll=/hold\s*\/\s*roll|\broll\b/i.test(title)||/your choice[^.]*roll/i.test(full);
 const route=!roll&&/→|->/.test(title)?title:'';
 const model=(full.match(/model uplift\s*(\d+)% of best/i)||full.match(/model[^%]{0,30}(\d+)% of best/i)||[])[1];
 let confidence=58;
 if(/strong leading case/i.test(tag)) confidence=86;
 else if(/supported leader/i.test(tag)) confidence=76;
 else if(/tentative leader/i.test(tag)) confidence=61;
 else if(/model leader/i.test(tag)) confidence=68;
 if(/strong/i.test(evidence)) confidence+=4;
 if(/cautious|limited/i.test(evidence)) confidence-=7;
 if(model){const m=Number(model);if(m>=90)confidence+=3;else if(m<75)confidence-=4;}
 confidence=Math.max(45,Math.min(92,confidence));
 return {action:roll?'ROLL':route?'TRANSFER':'HOLD',route,title,tag,evidence,confidence,full};
}

function teamState(){
 const view=q('#view-team');
 const full=text(view);
 const h2=qa('h2,h3',view).map(text).find(t=>/\d-\d-\d formation/i.test(t))||'';
 const cap=(full.match(/Captain\s+([^·|]+?)(?:\s*·|Vice|$)/i)||[])[1]?.trim()||'';
 const vice=(full.match(/Vice\s+([^·|]+?)(?:\s*·|$)/i)||[])[1]?.trim()||'';
 return {formation:h2.replace(/\s*formation/i,''),cap,vice,full};
}

function rivalState(){
 const full=text(q('#view-intel'));
 const posture=(full.match(/\b(PROTECT|BALANCED|CONTROLLED CHASE|CHASE)\b/i)||[])[1]||'';
 const target=(full.match(/nearest target[^A-Za-z0-9]+([^·|]{2,45})/i)||[])[1]?.trim()||'';
 return {posture:posture.toUpperCase(),target,full};
}

function shapeState(){
 const full=text(q('#view-shape'));
 const watch=(full.match(/\b(\d+)\s+(?:players?\s+)?(?:on\s+)?watch\b/i)||[])[1];
 const plan=(full.match(/\b(\d+)\s+(?:players?\s+)?(?:to\s+)?plan\b/i)||[])[1];
 return {watch:Number(watch||0),plan:Number(plan||0),full};
}

function why(t,r,s){
 const bits=[];
 if(t.action==='ROLL') bits.push('Current squad does not show enough proven transfer edge to spend flexibility now.');
 else if(t.action==='TRANSFER') bits.push(`${t.route||'The leading route'} is the strongest current move after model and evidence calibration.`);
 else bits.push('No transfer route currently clears the bar strongly enough to force action.');
 if(r.posture==='PROTECT') bits.push('League position favours protecting strong shared assets rather than manufacturing variance.');
 else if(r.posture==='CONTROLLED CHASE') bits.push('League position supports selective leverage, but only where the underlying move is already strong.');
 else if(r.posture==='CHASE') bits.push('League position allows more variance, while still avoiding weak differentials for their own sake.');
 if(s.plan>0) bits.push(`${s.plan} squad-structure flag${s.plan===1?'':'s'} remain for forward planning.`);
 return bits.slice(0,2).join(' ');
}

function triggerText(t){
 const full=t.full.toLowerCase();
 const triggers=[];
 if(/availability|minutes|injur|doubt/.test(full)) triggers.push('availability / minutes news');
 if(/rise pressure|fall pressure|market|price/.test(full)) triggers.push('price movement');
 if(/scout|evidence/.test(full)) triggers.push('Scout evidence');
 if(/rival ownership|ownership/.test(full)) triggers.push('rival exposure');
 return triggers.slice(0,3).join(' · ')||'late team news or a material model change';
}

function render(){
 const shell=q('main.shell'); const nav=q('#decision-nav');
 if(!shell||!nav)return;
 let host=q('#gw-decision-brief');
 if(!host){host=document.createElement('section');host.id='gw-decision-brief';host.className='gw-decision-brief';nav.insertAdjacentElement('beforebegin',host);}
 const t=transferState(),tm=teamState(),r=rivalState(),s=shapeState();
 const gw=text(q('#gw-pill'))||'GW';
 const action=t.action==='TRANSFER'?(t.route||'TRANSFER'):t.action;
 const tone=t.confidence>=80?'strong':t.confidence>=68?'good':'watch';
 const teamBits=[tm.formation?`${tm.formation} XI`:'',tm.cap?`C ${tm.cap}`:'',tm.vice?`VC ${tm.vice}`:''].filter(Boolean).join(' · ');
 host.dataset.tone=tone;
 host.innerHTML=`
  <div class="gwd-top">
    <div><p class="eyebrow">${esc(gw)} DECISION</p><div class="gwd-action">${esc(action)}</div></div>
    <div class="gwd-confidence"><strong>${t.confidence}%</strong><span>confidence</span></div>
  </div>
  <p class="gwd-why">${esc(why(t,r,s))}</p>
  <div class="gwd-strip">
    <span><b>TEAM</b>${esc(teamBits||'Open Pick Team for XI')}</span>
    <span><b>LEAGUE</b>${esc(r.posture||'BALANCED')}</span>
  </div>
  <div class="gwd-watch"><b>REASSESS IF</b> ${esc(triggerText(t))}</div>`;
 document.documentElement.dataset.gwDecisionBuild=BUILD;
}

function run(){[250,700,1400,2400].forEach(ms=>setTimeout(render,ms));}
function bind(){
 run();
 ['fplCoreDataReady','fplSafePlanUpdated'].forEach(ev=>window.addEventListener(ev,run,{passive:true}));
 qa('#decision-nav button').forEach(b=>b.addEventListener('click',()=>setTimeout(render,450),{passive:true}));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
