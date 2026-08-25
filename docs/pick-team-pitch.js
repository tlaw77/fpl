const PITCH_DATA='https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json';
const pEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function pScore(p){const f=(p.fixtures||[])[0];const ease=f?6-Number(f.difficulty||3):3;const avail=p.availability==null?1:Number(p.availability);return Number(p.decision_score||0)+ease*.55+avail*.8}
function pChooseXI(rows){const gk=rows.filter(p=>p.position==='GKP').sort((a,b)=>pScore(b)-pScore(a))[0];const out=rows.filter(p=>p.position!=='GKP').sort((a,b)=>pScore(b)-pScore(a));let xi=gk?[gk]:[];for(const [pos,min] of Object.entries({DEF:3,MID:2,FWD:1}))xi.push(...out.filter(p=>p.position===pos).slice(0,min));for(const p of out){if(xi.includes(p))continue;const c={DEF:xi.filter(x=>x.position==='DEF').length,MID:xi.filter(x=>x.position==='MID').length,FWD:xi.filter(x=>x.position==='FWD').length};if((p.position==='DEF'&&c.DEF>=5)||(p.position==='MID'&&c.MID>=5)||(p.position==='FWD'&&c.FWD>=3))continue;if(xi.length<11)xi.push(p)}return xi.slice(0,11)}
function pFormation(players){const c={DEF:0,MID:0,FWD:0};players.forEach(p=>{if(c[p.position]!=null)c[p.position]++});return `${c.DEF}-${c.MID}-${c.FWD}`}
function fdrClass(n){const x=Number(n||3);return `fdr-${Math.max(1,Math.min(5,x))}`}
function fixtureChips(p){const fs=(p.fixtures||[]).slice(0,3);return `<div class="pitch-fdrs">${[0,1,2].map(i=>{const f=fs[i];return f?`<span class="pitch-fdr ${fdrClass(f.difficulty)}" title="GW${f.gw}: ${pEsc(f.opponent)} ${f.venue}, FDR ${f.difficulty}"><b>GW${f.gw}</b> ${pEsc((f.opponent||'').slice(0,3).toUpperCase())} ${f.venue}<em>${f.difficulty}</em></span>`:`<span class="pitch-fdr empty">—</span>`}).join('')}</div>`}
const KIT_MAP={
  'Arsenal':['solid','#e30613','#ffffff','ARS'],
  'Aston Villa':['sleeves','#6a1538','#95c8e8','AVL'],
  'Bournemouth':['stripes','#d71920','#111111','BOU'],
  'Brentford':['stripes','#e30613','#ffffff','BRE'],
  'Brighton':['stripes','#0057b8','#ffffff','BHA'],
  'Chelsea':['solid','#034694','#ffffff','CHE'],
  'Coventry City':['solid','#6ec6e8','#ffffff','COV'],
  'Crystal Palace':['stripes','#1b458f','#c4122e','CRY'],
  'Everton':['solid','#003399','#ffffff','EVE'],
  'Fulham':['solid','#ffffff','#111111','FUL'],
  'Hull':['stripes','#f5a623','#111111','HUL'],
  'Ipswich Town':['solid','#0054a6','#ffffff','IPS'],
  'Leeds':['solid','#ffffff','#1d428a','LEE'],
  'Liverpool':['solid','#c8102e','#ffffff','LIV'],
  'Man City':['solid','#6cabdd','#ffffff','MCI'],
  'Man Utd':['solid','#da291c','#111111','MUN'],
  'Newcastle':['stripes','#ffffff','#111111','NEW'],
  "Nott'm Forest":['solid','#dd0000','#ffffff','NFO'],
  'Sunderland':['stripes','#eb172b','#ffffff','SUN'],
  'Spurs':['sleeves','#ffffff','#132257','TOT'],
  'Tottenham':['sleeves','#ffffff','#132257','TOT'],
  'Tottenham Hotspur':['sleeves','#ffffff','#132257','TOT'],
  'West Ham':['sleeves','#7a263a','#1bb1e7','WHU'],
  'Wolves':['solid','#fdb913','#111111','WOL']
};
function kitInfo(club){return KIT_MAP[club]||['solid','#cbd5e1','#475569',(club||'CLB').replace(/[^A-Za-z]/g,'').slice(0,3).toUpperCase()]}
function kitShirt(p){const [pattern,c1,c2,code]=kitInfo(p.club);return `<div class="pitch-shirt kit-${pattern}" style="--kit1:${c1};--kit2:${c2}" title="${pEsc(p.club)}"><span>${pEsc(code)}</span></div>`}
function pitchPlayer(p,tag=''){return `<div class="pitch-player-card">${kitShirt(p)}<div class="pitch-name">${p.captain?'<i class="cap">C</i>':''}${p.vice_captain?'<i class="vice">V</i>':''}${pEsc(p.player)}</div>${tag?`<div class="pitch-tag">${pEsc(tag)}</div>`:''}${fixtureChips(p)}</div>`}
function pitchRow(players,pos){return `<div class="pitch-row pitch-${pos.toLowerCase()}">${players.map(p=>pitchPlayer(p)).join('')}</div>`}
async function renderPitchTeam(){try{const r=await fetch(`${PITCH_DATA}?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)return;const d=await r.json();const rows=[...(d.squad_next5||[])];if(!rows.length)return;const xi=pChooseXI(rows);const ids=new Set(xi.map(p=>p.player_id));const bench=rows.filter(p=>!ids.has(p.player_id));const benchOut=bench.filter(p=>p.position!=='GKP').sort((a,b)=>pScore(b)-pScore(a));const benchGk=bench.filter(p=>p.position==='GKP');const ordered=[...benchOut,...benchGk];const by={GKP:[],DEF:[],MID:[],FWD:[]};xi.forEach(p=>by[p.position]?.push(p));const benchValue=bench.reduce((s,p)=>s+Number(p.price||0),0);const el=document.querySelector('#dc-team-view');if(!el)return;el.innerHTML=`<section class="pitch-panel"><div class="pitch-head"><div><p class="eyebrow">RECOMMENDED XI</p><h2>${pFormation(xi)} · next GW</h2></div><div class="pitch-legend"><span class="pitch-fdr fdr-2">Easy</span><span class="pitch-fdr fdr-3">Mid</span><span class="pitch-fdr fdr-4">Hard</span></div></div><div class="fpl-pitch">${pitchRow(by.GKP,'GKP')}${pitchRow(by.DEF,'DEF')}${pitchRow(by.MID,'MID')}${pitchRow(by.FWD,'FWD')}</div></section><section class="pitch-bench-panel"><div class="pitch-head"><div><p class="eyebrow">BENCH</p><h3>Recommended order</h3></div><div class="subtle">£${benchValue.toFixed(1)}m bench value</div></div><div class="pitch-bench">${ordered.map((p,i)=>pitchPlayer(p,p.position==='GKP'?'GK':`#${i+1}`)).join('')}</div></section><section class="pitch-note"><strong>How to read it:</strong> club-coloured shirts make the squad easier to scan. Each player also shows the next three fixtures; FDR is 1 easiest → 5 hardest. Bench order prioritises the strongest likely usable substitute, not price.</section>`;}catch(e){console.warn('pitch team view',e)}}
setTimeout(renderPitchTeam,350);
window.addEventListener('load',()=>setTimeout(renderPitchTeam,250));