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
ceiling_review_file=DIRECTORY/'ceiling-review.json'
if ceiling_review_file.exists():
    ceiling_review=json.loads(ceiling_review_file.read_text())
    ceiling_native=json.loads((DIRECTORY/'ceilings-latest.json').read_text())
    ceiling_homes=json.loads((DIRECTORY/'ceiling-home-review.json').read_text())
    if (ceiling_review['signature']!=ceiling_native['signature'] or ceiling_homes['signature']!=ceiling_native['signature']
        or not ceiling_review['overheadClosed'] or not ceiling_review['savedCandidatesUnchanged']
        or not ceiling_homes['capsuleClear'] or not ceiling_homes['savedCandidatesUnchanged']):
        raise RuntimeError('Ceiling gallery requires matching unchanged native witnesses')
    parts.append('<h2>Latest homes — measured timber ceiling bays</h2><p>Fresh private copies retain every existing house, scenery, room and light binding. Reviewed kit plank surfaces face downward in six or nine 3 m bays, with separate source-derived regional tint instances and one bounded, clock-driven interior fill per home. Upward native witnesses close the sampled room grid; normal capsules retain their route clearances. Regional architecture, shading, distant ceiling LODs, performance and appearance approval remain open.</p><div class="grid">')
    schematic=ROOT/ceiling_review['pictureDirectory']/'timber_ceiling_bays.png'
    if schematic.exists(): parts.append(picture(schematic,'Timber bays and measured minimum clearance — labeled authoring schematic'))
    for row in ceiling_review['pictures']:
        file=ROOT/row['file']
        if not file.exists(): raise RuntimeError('Native ceiling detail capture missing')
        parts.append(picture(file,row['home'].replace('_',' ').title()+' / ceiling detail / '+row['phase']+' — unapproved prototype'))
    for home in ceiling_homes['homes']:
        for phase in ('day','dusk','night'):
            for view in ('interior','exterior'):
                file=ROOT/ceiling_homes['pictureDirectory']/(home['id']+'_'+view+'_'+phase+'.png')
                if not file.exists(): raise RuntimeError('Native ceiling home capture missing')
                parts.append(picture(file,home['id'].replace('_',' ').title()+' / '+view+' / '+phase+' — unapproved timber-ceiling prototype'))
    parts.append('</div>')
    ceiling_camera_file=DIRECTORY/'ceiling-traversal-camera-latest.json'
    if ceiling_camera_file.exists():
        ceiling_camera=json.loads(ceiling_camera_file.read_text())
        if ceiling_camera['signature']!=ceiling_native['signature'] or not ceiling_camera['savedCandidatesUnchanged']:
            raise RuntimeError('Ceiling gameplay-camera evidence refers to another candidate')
        parts.append('<h2>Timber ceilings — live home walking cameras</h2><p>Normal character movement, live indoor/follow cameras and local authority-clock shelter observations. Campaign integration, vehicles, GM/network, hardware audio, performance and human approval remain open.</p><div class="grid">')
        for zone in ceiling_camera['zones']:
            for route in zone['routes']:
                for file in sorted((ROOT/ceiling_camera['output']).glob(route['id']+'_*.png')):
                    parts.append(picture(file,route['id'].replace('_',' ').title()+' — live ceiling prototype, waypoint '+file.stem.rsplit('_',1)[-1]))
        parts.append('</div>')
shell_review_file=DIRECTORY/'shell-home-review.json'
if shell_review_file.exists():
    shell_review=json.loads(shell_review_file.read_text())
    shell_native=json.loads((DIRECTORY/'shells-latest.json').read_text())
    seam_review=json.loads((DIRECTORY/'shell-seam-review.json').read_text())
    if (shell_review['signature']!=shell_native['signature'] or seam_review['signature']!=shell_native['signature']
        or not shell_review['savedCandidatesUnchanged'] or not seam_review['savedCandidatesUnchanged'] or not seam_review['seamRaysClosed']):
        raise RuntimeError('Home shell gallery requires matching unchanged native witnesses')
    parts.append('<h2>Latest furnished homes — roof attachment repair</h2><p>Fresh private copies correct the kit eave pivot while retaining wall, doorway, floor, furniture, material and room-lighting state. Native eave rays: '+str(seam_review['openParentRays'])+' open in the parent, '+str(seam_review['openRefitRays'])+' open after the repair. Regional architecture, dark shading, distant roof LODs and visual approval remain unfinished. Earlier pictures below retain the old gaps as historical studies.</p><div class="grid">')
    schematic=ROOT/shell_review['pictureDirectory']/'roof_attachment_schematic.png'
    if schematic.exists(): parts.append(picture(schematic,'Measured roof attachment datum — schematic, offsets exaggerated'))
    for home in shell_review['homes']:
        for phase in ('day','dusk','night'):
            for view in ('interior','exterior'):
                file=ROOT/shell_review['pictureDirectory']/(home['id']+'_'+view+'_'+phase+'.png')
                if not file.exists(): raise RuntimeError('Native shell capture missing')
                parts.append(picture(file,home['id'].replace('_',' ').title()+' / '+view+' / '+phase+' — unapproved roof-refit prototype'))
    parts.append('</div>')
    shell_camera_file=DIRECTORY/'shell-traversal-camera-latest.json'
    if shell_camera_file.exists():
        shell_camera=json.loads(shell_camera_file.read_text())
        if shell_camera['signature']!=shell_native['signature'] or not shell_camera['savedCandidatesUnchanged']:
            raise RuntimeError('Shell gameplay-camera evidence refers to another candidate')
        parts.append('<h2>Repaired homes — live walking cameras</h2><p>Normal character movement and live follow/indoor cameras using the authority clock. Vehicle, campaign, GM, network, performance and human visual acceptance remain open.</p><div class="grid">')
        for zone in shell_camera['zones']:
            for route in zone['routes']:
                for file in sorted((ROOT/shell_camera['output']).glob(route['id']+'_*.png')):
                    parts.append(picture(file,route['id'].replace('_',' ').title()+' — live roof-refit prototype, waypoint '+file.stem.rsplit('_',1)[-1]))
        parts.append('</div>')
atmosphere_review_file=DIRECTORY/'atmosphere-review.json'
if atmosphere_review_file.exists():
    atmosphere_review=json.loads(atmosphere_review_file.read_text())
    atmosphere_native=json.loads((DIRECTORY/'atmosphere-latest.json').read_text())
    if atmosphere_review['signature']!=atmosphere_native['signature'] or not atmosphere_review['savedCandidatesUnchanged']:
        raise RuntimeError('Atmosphere gallery requires matching unchanged private studies')
    parts.append('<h2>Regional weather and activity audio prototypes</h2><p>Actual native dawn/day/dusk/night and stronger-weather views. Local rain/steam geometry has no collision or navigation influence. These studies retain sparse scenery, dark shading and house roof gaps. Vent cameras now reject terrain occlusion and positions inside scenery bounds; steam visibility still needs correction. Appearance and audio remain unapproved.</p><div class="grid">')
    for row in atmosphere_review['pictures']:
        file=ROOT/row['file']
        if not file.exists():raise RuntimeError('Native atmosphere capture missing')
        caption=row['zone'].replace('_',' ').title()+' / '+row['view'].replace('_',' ')+' / '+row['phase'].replace('_',' ')
        caption+=' — unapproved weather study; '+str(row['particles'])+' effect quads'
        parts.append(picture(file,caption))
    parts.append('</div><p>Original native synthesized sound beds, eight seconds each. These are data previews, not hardware playback recordings. Listening, spatial mix and sound-design approval remain open.</p>')
    for row in atmosphere_review['audioStudies']:
        relative=(ROOT/row['file']).relative_to(DIRECTORY).as_posix()
        label=row['zone'].replace('_',' ').title()+' / '+row['study'].replace('_',' ')
        parts.append('<p>'+html.escape(label)+' <audio controls preload="none" src="'+html.escape(relative)+'"></audio></p>')
    atmosphere_camera_file=DIRECTORY/'atmosphere-traversal-camera-latest.json'
    if atmosphere_camera_file.exists():
        atmosphere_camera=json.loads(atmosphere_camera_file.read_text())
        if atmosphere_camera['signature']!=atmosphere_native['signature'] or not atmosphere_camera['savedCandidatesUnchanged']:
            raise RuntimeError('Atmosphere gameplay-camera evidence refers to another candidate')
        parts.append('<h2>Atmosphere — live home walking cameras</h2><p>Normal walking and follow/indoor cameras using the authoritative local world clock. Reached-waypoint reports verify active cosmetic weather and indoor shelter. This isolated fixture does not prove network synchronization, hardware audio, campaign integration or appearance approval.</p><div class="grid">')
        for zone in atmosphere_camera['zones']:
            for route in zone['routes']:
                for file in sorted((ROOT/atmosphere_camera['output']).glob(route['id']+'_*.png')):
                    parts.append(picture(file,route['id'].replace('_',' ').title()+' — live atmosphere prototype, waypoint '+file.stem.rsplit('_',1)[-1]))
        parts.append('</div>')
material_review_file=DIRECTORY/'material-review.json'
if material_review_file.exists():
    material_review=json.loads(material_review_file.read_text())
    material_native=json.loads((DIRECTORY/'materials-latest.json').read_text())
    if material_review['signature']!=material_native['signature'] or not material_review['savedCandidatesUnchanged']:
        raise RuntimeError('Material gallery requires matching unchanged private studies')
    parts.append('<h2>Regional terrain material studies</h2><p>Reviewed repository meadow, peat and road textures on fresh private candidates, at physical metre scales. Native compiled shaders and unchanged static geometry/room lighting verified. Regional composition, driving, gameplay and visual approval remain open.</p><div class="grid">')
    for row in material_review['pictures']:
        file=ROOT/row['file']
        if not file.exists():raise RuntimeError('Native material capture missing')
        parts.append(picture(file,row['zone'].replace('_',' ').title()+' / '+row['view'].replace('_',' ')+' / '+row['phase']+' — unapproved material study'))
    parts.append('</div>')
    material_walk_file=DIRECTORY/'material-traversal-headless-latest.json'
    material_camera_file=DIRECTORY/'material-traversal-camera-latest.json'
    if material_walk_file.exists():
        material_walk=json.loads(material_walk_file.read_text())
        if material_walk['signature']!=material_native['signature'] or not material_walk['savedCandidatesUnchanged']:
            raise RuntimeError('Material walking evidence refers to another candidate')
        count=sum(z['routesCompleted'] for z in material_walk['zones'])
        parts.append(f'<p>These material copies separately pass {count} configured normal-character walking routes. Zero airborne time during travel; static movement proof does not grant driving, live gameplay or appearance acceptance.</p>')
    if material_camera_file.exists():
        material_camera=json.loads(material_camera_file.read_text())
        if material_camera['signature']!=material_native['signature'] or not material_camera['savedCandidatesUnchanged']:
            raise RuntimeError('Material gameplay-camera evidence refers to another candidate')
        parts.append('<h2>Material studies — live home walking cameras</h2><p>Normal character, follow camera and indoor mode at reached waypoints. Unapproved prototypes.</p><div class="grid">')
        for zone in material_camera['zones']:
            for route in zone['routes']:
                for file in sorted((ROOT/material_camera['output']).glob(route['id']+'_*.png')):
                    parts.append(picture(file,route['id'].replace('_',' ').title()+' — live material study, reached waypoint '+file.stem.rsplit('_',1)[-1]))
        parts.append('</div>')
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
