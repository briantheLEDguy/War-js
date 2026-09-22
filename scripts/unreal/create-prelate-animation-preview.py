"""Create a local front/side player from actual Unreal review captures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/unreal/two-handed"
receipt = json.loads((OUT / "retarget.json").read_text())
frames = json.loads((OUT / "frames.json").read_text())
data = {}
for key, clip in receipt["clips"].items():
    rows = [row for row in frames if row["clip"] == key and row["file"].endswith("_front.png")]
    data[key] = dict(label=clip["sourceFile"].removesuffix(".fbx"), duration=clip["duration"],
        full=key in ("idle", "walk", "slash_alternate"),
        frames=[dict(seconds=row["seconds"], front=row["file"], side=row["file"].replace("_front.png", "_side.png")) for row in rows])
html = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Battle Prelate — supplied animations</title>
<style>body{margin:24px;background:#151820;color:#eee;font:16px system-ui}main{max-width:1280px;margin:auto}h1{font-size:24px;color:#e3c684}p{color:#bac1cf}select,button{font:inherit;padding:8px;background:#252c39;color:#fff;border:1px solid #657187;border-radius:5px}nav{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.views{display:flex;gap:12px;margin-top:20px}.views figure{margin:0;width:50%}img{width:100%;background:#090b0e}figcaption{color:#c8ad77}input{width:100%;margin:20px 0}small{color:#bac1cf}output{font-variant-numeric:tabular-nums}@media(max-width:700px){.views{display:block}.views figure{width:100%}}</style>
<main><h1>Battle Prelate · supplied two-handed animations</h1>
<p>Actual Unreal captures of the equipped character. Idle, walk and Great Sword Slash (1) are assigned to gameplay. Other clips are library previews awaiting integration and clearance review.</p>
<nav><select id="clip" aria-label="Animation"></select><button id="play">Pause</button><select id="speed" aria-label="Playback speed"><option value="0.25">¼ speed</option><option value="0.5">½ speed</option><option value="1" selected>Normal speed</option></select><output id="time"></output></nav>
<div class="views"><figure><figcaption>Front / three-quarter</figcaption><img id="front" alt="Native front view"></figure><figure><figcaption>Side</figcaption><img id="side" alt="Native side view"></figure></div>
<input id="scrub" type="range" min="0" max="1000" value="0" aria-label="Animation time"><small id="status"></small>
<p><small>Technical checks do not constitute final visual approval. Original procedural studies are paused.</small></p></main>
<script>const clips=DATA;
const selector=document.querySelector('#clip'),play=document.querySelector('#play'),speed=document.querySelector('#speed'),scrub=document.querySelector('#scrub');
let key='slash_alternate',seconds=0,playing=true,last=0;
for(const [value,clip]of Object.entries(clips)){const option=document.createElement('option');option.value=value;option.textContent=clip.label+(clip.full?' · active':' · library keyframes');selector.append(option)}selector.value=key;
function draw(){const clip=clips[key];let row=clip.frames[0];for(const frame of clip.frames){if(frame.seconds<=seconds+.0001)row=frame;else break}for(const view of ['front','side'])document.getElementById(view).src=row[view];document.querySelector('#time').textContent=seconds.toFixed(2)+' / '+clip.duration.toFixed(2)+' s';scrub.value=Math.round(seconds/clip.duration*1000);document.querySelector('#status').textContent=clip.full?'30 fps native capture. Scrub or slow playback to inspect grip and whole-body motion.':'Four native keyframes only; this clip is not an active gameplay action.'}
selector.onchange=()=>{key=selector.value;seconds=0;draw()};play.onclick=()=>{playing=!playing;play.textContent=playing?'Pause':'Play'};scrub.oninput=()=>{seconds=Number(scrub.value)/1000*clips[key].duration;playing=false;play.textContent='Play';draw()};
function tick(now){if(playing&&last){seconds=(seconds+Math.min((now-last)/1000,.1)*Number(speed.value))%clips[key].duration;draw()}last=now;requestAnimationFrame(tick)}draw();requestAnimationFrame(tick);
</script></html>"""
(OUT / "preview.html").write_text(html.replace("DATA", json.dumps(data)), encoding="utf-8")
print(OUT / "preview.html")
