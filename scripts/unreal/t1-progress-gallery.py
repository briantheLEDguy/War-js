"""Create a local gallery of unchanged native captures and labeled authoring drawings."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
review=json.loads((DIRECTORY/'review.json').read_text())
native=json.loads((DIRECTORY/'native-latest.json').read_text())
if review['planSha256']!=native['planSha256'] or not review['savedCandidatesUnchanged']:
    raise RuntimeError('Gallery requires a matching completed native review')
views=ROOT/review['pictureDirectory']
parts=['''<!doctype html><html lang="en"><meta charset="utf-8"><title>T1 buildout progress</title>
<style>body{margin:0;background:#172227;color:#e9e5d7;font:17px/1.5 system-ui;padding:28px}
h1{margin:0}p{max-width:1050px;color:#c7c9bb}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px}
figure{margin:0;background:#202f35;padding:10px}img{width:100%;height:auto;display:block}figcaption{padding:8px 2px}
a{color:#cbd9e8}h2{margin-top:36px}</style><h1>T1 buildout progress</h1>
<p>Actual native rendering studies and authoring diagrams. Interiors, services/gameplay integration,
landscape materials, vehicle/camera acceptance, 18v18 and visual approval remain unfinished.</p>''']
def picture(file,caption):
    relative=file.relative_to(DIRECTORY).as_posix()
    return f'<figure><a href="{html.escape(relative)}"><img loading="lazy" src="{html.escape(relative)}" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>'
walking_file=DIRECTORY/'traversal-headless-latest.json'
camera_file=DIRECTORY/'traversal-camera-latest.json'
if walking_file.exists():
    walking=json.loads(walking_file.read_text())
    home_native=json.loads((DIRECTORY/'homes-latest.json').read_text())
    if walking['signature']!=home_native['signature'] or not walking['savedCandidatesUnchanged']:
        raise RuntimeError('Walking gallery requires matching unchanged candidates')
    count=sum(z['routesCompleted'] for z in walking['zones'])
    metres=sum(r['distanceCm']/100 for z in walking['zones'] for r in z['routes'])
    parts.append(f'<h2>Native character walking proof</h2><p>{count} configured routes completed, {metres/1000:.2f} km of simulated movement. Both directions of roads and supply itineraries, plus village approaches and furnished interiors. Fixed simulation timestep; vehicle, camera, visual and gameplay acceptance remain open.</p><div class="grid">')
    for zone in walking['zones']:
        drawing=DIRECTORY/(zone['zone']+'_native_walking_coverage.png')
        if drawing.exists():parts.append(picture(drawing,zone['zone'].replace('_',' ').title()+' — completed route coverage (schematic)'))
    if camera_file.exists():
        camera=json.loads(camera_file.read_text())
        if camera['signature']!=home_native['signature'] or not camera['savedCandidatesUnchanged']:
            raise RuntimeError('Camera gallery requires matching unchanged candidates')
        camera_directory=ROOT/camera['output']
        for zone in camera['zones']:
            for route in zone['routes']:
                for file in sorted(camera_directory.glob(route['id']+'_*.png')):
                    parts.append(picture(file,route['id'].replace('_',' ').title()+' — live third person camera, reached waypoint '+file.stem.rsplit('_',1)[-1]+' (unapproved prototype)'))
    parts.append('</div>')
parts.append('<h2>Topology and village reservations</h2><div class="grid">')
for identity in ['sunmeadow_march','cinderfen_outskirts','brightfen_approach','ashen_steppe']:
    for suffix in ['topology','village_plan']:
        file=DIRECTORY/(identity+'_'+suffix+'.png')
        if not file.exists():raise RuntimeError('Progress drawing missing')
        parts.append(picture(file,identity.replace('_',' ').title()+' — '+suffix.replace('_',' ')+' (schematic)'))
parts.append('</div>')
home_review_file=DIRECTORY/'home-review.json'
if home_review_file.exists():
    home_review=json.loads(home_review_file.read_text())
    home_native=json.loads((DIRECTORY/'homes-latest.json').read_text())
    if home_review['signature']!=home_native['signature'] or home_review['parentPlanSha256']!=native['planSha256'] or not home_review['savedCandidatesUnchanged']:
        raise RuntimeError('Home gallery requires matching unchanged native studies')
    home_views=ROOT/home_review['pictureDirectory']
    parts.append('<h2>Furnished home studies — private modular catalog</h2><p>These are room and doorway prototypes. Regional architecture, camera clearance, lighting polish and visual approval remain pending. Live movement evidence is shown separately above.</p><div class="grid">')
    for home in home_review['homes']:
        drawing=DIRECTORY/(home['id']+'_floor_plan.png')
        if drawing.exists():parts.append(picture(drawing,home['id'].replace('_',' ').title()+' — room plan (schematic)'))
        for phase in ['day','night','dusk']:
            for view in ['exterior','interior']:
                file=home_views/(home['id']+'_'+view+'_'+phase+'.png')
                if not file.exists():raise RuntimeError('Native home capture missing')
                parts.append(picture(file,home['id'].replace('_',' ').title()+' / '+view+' / '+phase+' — unapproved study'))
    parts.append('</div>')
for zone in review['zones']:
    identity=zone['zone']
    parts.append('<h2>'+html.escape(identity.replace('_',' ').title())+' — native player-height views</h2><div class="grid">')
    for phase in ['day','night','dawn','dusk','weather']:
        for label in ['village','advance','ridge','working_outskirts','regional_cover']:
            file=views/(identity+'_'+label+'_'+phase+'.png')
            if file.exists():parts.append(picture(file,label.replace('_',' ').title()+' / '+phase+' — unapproved prototype'))
    parts.append('</div>')
parts.append('<p>Saved native maps were unchanged by these captures. Native road sampling is not a walk/drive playtest.</p></html>')
(DIRECTORY/'progress-gallery.html').write_text('\n'.join(parts),encoding='utf-8')
print(json.dumps({'gallery':'artifacts/unreal/t1-redesign/progress-gallery.html','nativePlan':review['planSha256'][:12]}))
