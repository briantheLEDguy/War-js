"""Fresh private distant scenery uses exact installed meshes and seam-matched nonblocking terrain."""
import copy,json,math
import unreal
from t1_distant_scenery import qualify_distant_skirt
from t1_materials import sha

POLICY=dict(cast_shadow=False,can_ever_affect_navigation=False,generate_overlap_events=False,affect_distance_field_lighting=False)
TAG='WarT1DistantScenery'


def add_distant_scenery(assets,source,terrain,states,receipt_file):
    if not receipt_file:return states,dict(actors=0,legacyPreserved=True)
    if source['id']!='sunmeadow_march' or not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'):
        raise RuntimeError('Distant scenery requires a fresh isolated Sunmeadow candidate')
    recipe=json.loads((assets.root/receipt_file).read_text());mesh_data=json.loads((assets.root/recipe['file']).read_text())
    if recipe['licensedDerivative'] is not True or recipe['distributionApproved'] is not False or recipe['collisionEnabled'] is not False:
        raise RuntimeError('Distant scenery admission differs')
    for file,digest in recipe['inputs'].items():
        if sha(assets.root/file)!=digest:raise RuntimeError('Distant source changed: '+file)
    proof=qualify_distant_skirt(source,terrain,mesh_data);result=copy.deepcopy(states);placements=[]
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    for i,row in enumerate(recipe['mountains']):
        original=row['source'];mesh=unreal.load_asset(original['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing exact installed distant mountain')
        bounds=mesh.get_bounds();observed=[[bounds.origin.x,bounds.origin.y,bounds.origin.z],[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z]]
        if observed!=[original['boundsOrigin'],original['boundsExtent']] or mesh.get_num_lods()!=original['lodCount']:
            raise RuntimeError('Installed distant mountain bounds or LODs differ')
        screens=list(editor.get_lod_screen_sizes(mesh))
        materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.get_editor_property('static_materials')]
        if screens!=original['lodScreenSizes'] or materials!=original['materials']:raise RuntimeError('Distant mountain source material or LOD screen inventory differs')
        label=source['id']+'_distant_mountain_'+str(i+1).zfill(2)
        result[label]=dict(kind='mesh',mesh=mesh.get_path_name(),location=row['location'],scale=row['scale'],rotation=[0,0,0],
            materials=materials,tags=[TAG,'PrototypeScenery'],collision='NoCollision',distantPolicy=POLICY.copy())
        placements.append(dict(id=label,source=mesh.get_path_name(),sourceGeometryPreserved=True,lods=original['lodCount'],lodScreenSizes=screens))
    material=unreal.load_asset(result[source['id']+'_terrain']['materials'][0])
    skirt=assets.mesh(source['id']+'_distant_ground_skirt',mesh_data,material,False)
    label=source['id']+'_distant_ground_skirt';result[label]=dict(kind='mesh',mesh=skirt.get_path_name(),location=[0,0,0],scale=[1,1,1],rotation=[0,0,0],
        materials=[material.get_path_name()],tags=[TAG,'PrototypeScenery'],collision='NoCollision',distantPolicy=POLICY.copy())
    return result,dict(actors=len(placements)+1,placements=placements,skirt=proof,recipeFile=receipt_file,recipeSha256=sha(assets.root/receipt_file),
        sourcePackagesPreserved=True,licensedDerivative=True,distributionApproved=False,appearanceApproved=False,performanceAccepted=False)


def verify_distant_scenery(actors,source,proof):
    if not proof['actors']:return []
    bounds=source['spatial']['bounds'];rows=[]
    for actor in actors.get_all_level_actors():
        if TAG not in list(map(str,actor.tags)):continue
        c=actor.static_mesh_component
        if c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION or str(c.get_collision_profile_name())!='NoCollision' or c.get_editor_property('use_default_collision'):
            raise RuntimeError('Distant scenery has blocking/default collision')
        if any(c.get_editor_property(k)!=v for k,v in POLICY.items()):raise RuntimeError('Distant component policy differs')
        origin,extent=actor.get_actor_bounds(False)
        box=dict(minX=(origin.y-extent.y)/100,maxX=(origin.y+extent.y)/100,minZ=(origin.x-extent.x)/100,maxZ=(origin.x+extent.x)/100)
        if box['minX']<bounds['minX']-.02 or box['maxX']>bounds['maxX']+.02 or box['minZ']<bounds['minZ']-.02 or box['maxZ']>bounds['maxZ']+.02:
            raise RuntimeError('Native distant component escapes zone content envelope')
        rows.append(dict(id=actor.get_actor_label(),componentBounds=box,collision='NoCollision',policy=POLICY.copy()))
    if len(rows)!=proof['actors']:raise RuntimeError('Native distant scenery inventory differs')
    return rows
