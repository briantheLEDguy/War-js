"""Present unmodified native frames with synchronized front/side playback."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/'artifacts/unreal/combat-animation'
receipt=json.loads((OUT/'review.json').read_text())
frames=receipt['frames']
front=[row for row in frames if row['phase'].startswith('motion_')]
side=[row for row in frames if row['phase'].startswith('side_motion_')]
if not front or len(front)!=len(side): raise ValueError('Both native playback views are required')
if any(not (OUT/row['file']).is_file() for row in frames): raise ValueError('Missing native review frame')
data={'front':front,'side':side,'fps':receipt['playbackFps'],
      'stills':[row for row in frames if row not in front and row not in side],
      'revision':receipt['map'].rsplit('_',2)[-1]}
html='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Battle Prelate — heavy hammer revision</title>
<style>body{margin:0;background:#141719;color:#eee;font:16px system-ui}main{max-width:1300px;margin:20px auto;padding:20px}h1{font-size:26px}p{max-width:920px;color:#c4cbcd}.views{display:grid;grid-template-columns:1fr 1fr;gap:12px}img{width:100%;display:block}figure{margin:0;background:#080b0c}figcaption{padding:10px}button,select{font:inherit;padding:8px;margin:4px;background:#30373c;color:white;border:1px solid #627078;border-radius:4px}input{width:min(80%,700px)}#still{max-width:720px}label{margin:10px} @media(max-width:700px){.views{grid-template-columns:1fr}}</style>
<main><h1>Battle Prelate: rear wind-up and forward strike</h1>
<p>Native Unreal capture of the revised 2.4-second study: staggered support, rear shoulder load, overhead delivery, knee compression, and deliberate recovery. The same frame is shown from both cameras.</p>
<button id="play" disabled>Loading playback…</button><label>Speed <select id="speed"><option value="1">Normal</option><option value="0.5">Half speed</option><option value="0.25">Quarter speed</option></select></label>
<input id="scrub" type="range" min="0" value="0" aria-label="Animation frame"><output id="time"></output>
<div class="views"><figure><img id="front" alt="Front view of hammer strike"><figcaption>Front three-quarter</figcaption></figure><figure><img id="side" alt="Side view of hammer strike"><figcaption>Side — rear load and clearance</figcaption></figure></div>
<p>This is a review animation, not a live ability. Pose and intersection checks are engineering checks; they do not replace judging the motion.</p>
<details><summary>Other poses and casting studies</summary><select id="stills" aria-label="Review pose"></select><img id="still" alt="Selected native review pose"></details>
</main><script>const data=DATA;const el=id=>document.getElementById(id);let running=false,index=0,last=0,accum=0;
const url=file=>file+'?revision='+data.revision;el('scrub').max=data.front.length-1;
function show(i){index=i;el('front').src=url(data.front[i].file);el('side').src=url(data.side[i].file);el('scrub').value=i;el('time').textContent=data.front[i].seconds.toFixed(2)+' s'}
el('scrub').oninput=()=>{running=false;el('play').textContent='Play';show(Number(el('scrub').value))};
el('play').onclick=()=>{running=!running;last=performance.now();accum=0;el('play').textContent=running?'Pause':'Play'};
function tick(now){if(running){accum+=(now-last)*Number(el('speed').value);const step=Math.floor(accum*data.fps/1000);if(step){show((index+step)%data.front.length);accum-=step*1000/data.fps}}last=now;requestAnimationFrame(tick)}requestAnimationFrame(tick);
for(let i=0;i<data.stills.length;i++){let o=document.createElement('option');o.value=i;o.textContent=data.stills[i].motion+' / '+data.stills[i].phase;el('stills').append(o)}
el('stills').onchange=()=>el('still').src=url(data.stills[el('stills').value].file);el('stills').onchange();show(0);
Promise.all([...data.front,...data.side].map(row=>new Promise((resolve,reject)=>{const image=new Image();image.onload=resolve;image.onerror=reject;image.src=url(row.file)}))).then(()=>{el('play').disabled=false;el('play').textContent='Play'}).catch(()=>{el('play').textContent='Frame load failed — reload preview'});
</script></html>'''.replace('DATA',json.dumps(data))
for name in ('preview.html','preview-heavy-hammer.html'):
    (OUT/name).write_text(html,encoding='utf-8')
print(OUT/'preview-heavy-hammer.html')
