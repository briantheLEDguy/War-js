"""Add authored street details to the owner's official capital without rebuilding it."""
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_geography import source_map
spec = importlib.util.spec_from_file_location('detail_layout', Path(__file__).with_name('capital-detail-layout.py'))
planning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planning)
output = ROOT / 'artifacts/unreal/licensed-kits'
config = (ROOT/'unreal/AegisWar/Config/DefaultEngine.ini').read_text()
target = re.search(r'^GameDefaultMap=(.+)$', config, re.M).group(1).strip()
if not target.startswith('/Game/Capitals/crownward/FinalAppearance_'):
    raise RuntimeError('Preserve unexpected official map; reconcile before detail edits')
source_file = ROOT/'unreal/AegisWar/Content'/(target.removeprefix('/Game/')+'.umap')
before = hashlib.sha256(source_file.read_bytes()).hexdigest()
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(target):
    raise RuntimeError('Official capital did not load')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = list(actors.get_all_level_actors())
if any('WarCapitalDetailV1' in [str(t) for t in a.tags] for a in existing):
    raise RuntimeError('Detail pass already exists; preserve owner edits instead of duplicating')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
destination = '/Game/LicensedKits/Crownward/Detail_' + stamp
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = unreal.MaterialEditingLibrary
staged = json.loads((output/'capital-detail-staged.json').read_text())
for row in staged['files']:
    if hashlib.sha256((ROOT/'unreal/AegisWar/Content'/row['path']).read_bytes()).hexdigest() != row['sha256']:
        raise RuntimeError('Staged fixture changed: ' + row['path'])
mesh_paths = {'post':'/Game/Medieval_Mod_Town/Meshes/SM_Wood_Plank_Pillar',
    'sconce':'/Game/Medieval_Mod_Town/Meshes/SM_Torch',
    'bench':'/Game/LicensedKits/Crownward/SM_Bench',
    'barrel':'/Game/LicensedKits/Crownward/SM_Barrel',
    'crate':'/Game/LicensedKits/Crownward/SM_Crate'}
meshes={}
for name,path in mesh_paths.items():
    mesh=unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError('Required authored mesh missing: '+path)
    meshes[name]=mesh

def tag(actor, identity):
    actor.set_actor_label('Crownward detail '+identity)
    actor.tags=['WarCapitalDetailV1','WarCapitalDetail_'+identity]
    actor.set_folder_path('Crownward/Street details')

def place(kind, identity, center, yaw=0, scale=(1,1,1)):
    mesh=meshes[kind]
    bounds=mesh.get_bounds()
    o,e=bounds.origin,bounds.box_extent
    rad=math.radians(yaw)
    ox,oy=o.x*scale[0],o.y*scale[1]
    position=unreal.Vector(center[0]-ox*math.cos(rad)+oy*math.sin(rad),
        center[1]-ox*math.sin(rad)-oy*math.cos(rad),center[2]-(o.z-e.z)*scale[2])
    actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,position,unreal.Rotator(yaw=yaw))
    actor.set_actor_scale3d(unreal.Vector(*scale))
    tag(actor,identity)
    actor.static_mesh_component.set_static_mesh(mesh)
    # This additive cosmetic pass cannot introduce new invisible movement blockers.
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    return actor

blockers=[]
for actor in existing:
    if isinstance(actor,unreal.StaticMeshActor) and 'WarCrownward' in [str(t) for t in actor.tags]:
        center,extent=actor.get_actor_bounds(False)
        blockers.append((center,extent))
placed=[]
skipped=[]
for row in planning.layout():
    p=row['position']
    if any(abs(p[0]-c.x)<e.x+110 and abs(p[1]-c.y)<e.y+110 and abs(p[2]-c.z)<e.z+300
           for c,e in blockers):
        skipped.append(row['id'])
        continue
    identity=row['id']
    yaw=row['yaw']
    place('post',identity+'_post',p,yaw,(.22,.14,1.35))
    place('sconce',identity+'_sconce',[p[0],p[1],p[2]+185],yaw,(1.2,1.2,1.2))
    light=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(p[0],p[1],p[2]+267))
    tag(light,identity+'_light')
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_editor_property('intensity',650.0)
    light.light_component.set_editor_property('attenuation_radius',600.0)
    light.light_component.set_editor_property('use_temperature',True)
    light.light_component.set_editor_property('temperature',2350.0)
    light.light_component.set_editor_property('cast_shadows',False)
    placed.append(row)

# Add small supply groupings at the outer market edge, clear of its passage.
supplies=[]
for index,x in enumerate([-11200,-9600,-8000]):
    for side in [-1,1]:
        y=side*2950
        for kind,dx,dy in [('barrel',0,0),('crate',85,40),('crate',170,-25)]:
            identity=f'market_{index}_{side}_{kind}_{dx}'
            place(kind,identity,[x+dx,y+dy,5],index*23+side*12)
            supplies.append(identity)

# District-specific instances retain each inherited texture, normal and roughness map.
palette=[(.43,.40,.35),(.34,.39,.40),(.41,.35,.31),(.34,.38,.32),(.44,.43,.40)]
districts=source_map()['cityDistricts']
instances={}
overrides=[]
for actor in existing:
    tags=[str(t) for t in actor.tags]
    identity=next((t for t in tags if t.startswith('WarWorldObject_')),'')
    if not isinstance(actor,unreal.StaticMeshActor) or 'house' not in identity.lower():
        continue
    position=actor.get_actor_location()
    district=min(districts,key=lambda d:(d['z']*100-position.x)**2+(d['x']*100-position.y)**2)
    color=palette[int(hashlib.sha256(district['id'].encode()).hexdigest()[:8],16)%len(palette)]
    component=actor.static_mesh_component
    for slot in range(component.get_num_materials()):
        original=component.get_material(slot)
        if not original or 'Base_Color_Tint' not in [str(n) for n in materials.get_vector_parameter_names(original)]:
            continue
        key=(original.get_path_name(),district['id'])
        if key not in instances:
            name='MI_District_'+hashlib.sha256(repr(key).encode()).hexdigest()[:12]
            material=tools.create_asset(name,destination,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
            materials.set_material_instance_parent(material,original)
            materials.set_material_instance_vector_parameter_value(material,'Base_Color_Tint',unreal.LinearColor(*color,1))
            if not assets.save_loaded_asset(material,only_if_is_dirty=False):
                raise RuntimeError('Could not save district material')
            instances[key]=material
        component.set_material(slot,instances[key])
        overrides.append({'actor':actor.get_path_name(),'slot':slot,'source':original.get_path_name(),
                          'material':instances[key].get_path_name(),'district':district['id']})
if hashlib.sha256(source_file.read_bytes()).hexdigest()!=before:
    raise RuntimeError('Concurrent owner save detected; do not overwrite it')
if not level.save_current_level():
    raise RuntimeError('Official capital save failed')
receipt={'schemaVersion':1,'map':target,'sourceSha256':before,
    'mapSha256':hashlib.sha256(source_file.read_bytes()).hexdigest(),
    'preservedActorCount':len(existing),'addedActorCount':len(placed)*3+len(supplies),
    'fixtures':placed,'skippedObstructedFixtures':skipped,'supplyProps':supplies,
    'materialOverrides':overrides,'materialCount':len(instances),'tag':'WarCapitalDetailV1',
    'visualApproved':False,'fullCapitalAcceptance':False}
(output/'capital-detail-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_CAPITAL_DETAIL_SAVED='+target)
