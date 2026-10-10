"""Fresh private collision rock clones; original kit, shelters and gameplay assemblies stay intact."""
import copy,hashlib,json,struct
import unreal
from t1_rock_clusters import NAMES,rock_clusters
from t1_rock_contact import rock_contact
from t1_habitat_palette import installed_rock_palette

TAG='WarT1PrivateInstalledRockCluster'
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]

def geometry(mesh):
    data=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0))
    if not data.get('valid'):raise RuntimeError('Missing committed rock source geometry')
    return hashlib.sha256(json.dumps(data['data'],sort_keys=True).encode()).hexdigest()


def surface_vertices(mesh):
    policy=json.loads(unreal.WarImportLibrary.describe_static_mesh_native_policy(mesh))
    if not policy.get('valid') or policy['policy']['mesh']['lod_for_collision']!=0:raise RuntimeError('Rock contact requires native LOD0 collision')
    data=json.loads(unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh,0))
    if not data.get('valid'):raise RuntimeError('Missing actual rendered rock surface')
    # Expanded triangle corners must not bias the vertex contact surrogate.
    points=sorted({tuple(p) for face in data['triangles'] for p in face['positions']})
    if not 4<=len(points)<=20000:raise RuntimeError('Rock surface vertex budget exceeded')
    return points


def adapt_rock_clusters(assets,identity,states,placements,sources,height_cm):
    if not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'):raise RuntimeError('Rock clusters require a fresh private atmosphere candidate')
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    meshes={};native={};materials={};proofs=[]
    for name in NAMES:
        source=sources[name];mesh=unreal.load_asset(source['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing exact installed rock')
        bounds=mesh.get_bounds();observed=[[bounds.origin.x,bounds.origin.y,bounds.origin.z],[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z]]
        bindings=[slot.material_interface.get_path_name() for slot in mesh.get_editor_property('static_materials')]
        if observed!=[source['boundsOrigin'],source['boundsExtent']] or bindings!=source['materials'] or mesh.get_num_lods()!=4:raise RuntimeError('Installed rock bounds/material/LOD inventory differs')
        clone=assets.tools.duplicate_asset(identity+'_'+name+'_Collision',assets.folder+'/RockClusters',mesh)
        if not isinstance(clone,unreal.StaticMesh):raise RuntimeError('Cannot clone private installed rock')
        clone.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        # Pixel-depth offsets would make the drawn boundary disagree with the triangle collision.
        for i,path in enumerate(bindings):
            if path not in materials:
                original=unreal.load_asset(path)
                if not isinstance(original,unreal.MaterialInstanceConstant):raise RuntimeError('Rock adaptation requires an inspected material instance')
                adapted=assets.tools.duplicate_asset(identity+'_'+name+'_Material_'+str(i),assets.folder+'/RockClusters',original)
                names=set(map(str,unreal.MaterialEditingLibrary.get_scalar_parameter_names(original)))
                for parameter in ('Pixel_Depth_Offset_Zone','Pixel_Depth_Offset_Randomness'):
                    if parameter not in names:raise RuntimeError('Missing inspected rock depth-offset parameter')
                    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(adapted,parameter,0)
                    if unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(adapted,parameter)!=0:raise RuntimeError('Cannot align rendered rock and triangle collision')
                if identity=='cinderfen_outskirts':
                    lib=unreal.MaterialEditingLibrary
                    if 'Base_Color_Tint' not in set(map(str,lib.get_vector_parameter_names(original))) or 'Base_Color_Desaturation' not in names:raise RuntimeError('Missing inspected regional rock colour parameters')
                    old=lib.get_material_instance_vector_parameter_value(original,'Base_Color_Tint');palette=installed_rock_palette(identity,[old.r,old.g,old.b,old.a])
                    lib.set_material_instance_vector_parameter_value(adapted,'Base_Color_Tint',unreal.LinearColor(*palette['tint']));lib.set_material_instance_scalar_parameter_value(adapted,'Base_Color_Desaturation',palette['desaturation'])
                    observed=lib.get_material_instance_vector_parameter_value(adapted,'Base_Color_Tint')
                    if any(abs(a-b)>1e-6 for a,b in zip([observed.r,observed.g,observed.b,observed.a],palette['tint'])) or abs(lib.get_material_instance_scalar_parameter_value(adapted,'Base_Color_Desaturation')-palette['desaturation'])>1e-6:raise RuntimeError('Regional rock colour differs from bounded palette')
                if not unreal.EditorAssetLibrary.save_loaded_asset(adapted,only_if_is_dirty=False):raise RuntimeError('Cannot save fresh rock material')
                materials[path]=adapted
            clone.set_material(i,materials[path])
        if not unreal.EditorAssetLibrary.save_loaded_asset(clone,only_if_is_dirty=False):raise RuntimeError('Cannot save fresh collision rock')
        unreal.WarImportLibrary.prepare_world_preview_frame(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
        # Cached commandlet render data can initialise duplicated screen sizes to zero; retain source thresholds explicitly.
        if not editor.set_lod_screen_sizes(clone,list(editor.get_lod_screen_sizes(mesh))):raise RuntimeError('Cannot retain exact source rock LOD thresholds')
        original_geometry,adapted_geometry=geometry(mesh),geometry(clone)
        original_screens,adapted_screens=list(editor.get_lod_screen_sizes(mesh)),list(editor.get_lod_screen_sizes(clone))
        if original_geometry!=adapted_geometry or clone.get_num_lods()!=4 or original_screens!=adapted_screens:raise RuntimeError('Rock adaptation differs: '+json.dumps(dict(name=name,originalGeometry=original_geometry,adaptedGeometry=adapted_geometry,lods=clone.get_num_lods(),originalScreens=original_screens,adaptedScreens=adapted_screens)))
        native[name]=clone;meshes[name]=dict(boundsOrigin=source['boundsOrigin'],boundsExtent=source['boundsExtent'],positions=surface_vertices(clone))
        proofs.append(dict(source=mesh.get_path_name(),adapted=clone.get_path_name(),geometrySha256=geometry(clone),lods=4,lodScreenSizes=original_screens,collisionTraceFlag='CTF_USE_COMPLEX_AS_SIMPLE',pixelDepthOffsetCm=0,regionalTintFactor=.35 if identity=='cinderfen_outskirts' else 1,regionalDesaturation=.35 if identity=='cinderfen_outskirts' else None))
    result=copy.deepcopy(states);layout=rock_clusters(placements,meshes,height_cm)
    for label in layout['replacedIds']:
        if label not in result:raise RuntimeError('Rock parent identity missing')
        del result[label]
    for body in layout['bodies']:
        label=body['id'];mesh=native[body['meshName']]
        if label in result:raise RuntimeError('Duplicate rock body identity')
        scale=f32(body['scale']);result[label]=dict(kind='mesh',location=body['location'],rotation=[0,f32(body['yawDegrees']),0],scale=[scale]*3,tags=['WarT1BattlefieldSceneCell',TAG],mesh=mesh.get_path_name(),materials=[mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property('static_materials')))],collision='BlockAll')
    return result,dict(**layout,meshes=proofs,sourcePackagesPreserved=True,licenseReviewed=False,distributionApproved=False,walkingAccepted=False,drivingAccepted=False,navigationAccepted=False,appearanceApproved=False,performanceAccepted=False)


def verify_rock_surfaces(actors,layout,height_cm):
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    for row in layout['meshes']:
        mesh=unreal.load_asset(row['adapted'])
        if geometry(mesh)!=row['geometrySha256'] or mesh.get_num_lods()!=4 or list(editor.get_lod_screen_sizes(mesh))!=row['lodScreenSizes']:raise RuntimeError('Saved rock geometry or LOD thresholds differ')
    actual={a.get_actor_label():a for a in actors.get_all_level_actors() if TAG in map(str,a.tags)};rows=[];surfaces={}
    if set(actual)!={b['id'] for b in layout['bodies']}:raise RuntimeError('Rock body inventory differs')
    for body in layout['bodies']:
        actor=actual[body['id']];component=actor.static_mesh_component;mesh=component.static_mesh
        if component.get_collision_profile_name()!='BlockAll' or mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')!=unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:raise RuntimeError('Rock collision binding changed')
        bounds=mesh.get_bounds();p=actor.get_actor_location();scale=actor.get_actor_scale3d().x
        key=mesh.get_path_name()
        if key not in surfaces:surfaces[key]=surface_vertices(mesh)
        contact=rock_contact(surfaces[key],[bounds.origin.x,bounds.origin.y,bounds.origin.z],[p.x,p.y,p.z],scale,actor.get_actor_rotation().yaw,height_cm)
        if contact['buriedFraction']<.08 or contact['contactQuadrants']<2:raise RuntimeError('Saved rock lacks bounded native vertex bedding: '+body['id'])
        centre=body['footprintCentre'];hits=0;exposed=0;highest=-1e30
        # Component-only rays avoid accepting the terrain or neighbouring rocks as support.
        for ix in (-1,0,1):
            for iz in (-1,0,1):
                x=centre[0]+ix*min(body['footprintWidth'],body['footprintDepth'])*.12;z=centre[1]+iz*min(body['footprintWidth'],body['footprintDepth'])*.12
                start=unreal.Vector(z*100,x*100,p.z+(bounds.origin.z+bounds.box_extent.z)*scale+10)
                end=unreal.Vector(z*100,x*100,p.z+(bounds.origin.z-bounds.box_extent.z)*scale-10)
                simple=component.line_trace_component(start,end,False,False,False);complex_hit=component.line_trace_component(start,end,True,False,False)
                if bool(simple)!=bool(complex_hit):raise RuntimeError('Simple/complex rock surface mismatch')
                if simple:
                    if abs(simple[0].z-complex_hit[0].z)>.1:raise RuntimeError('Rock trace heights disagree')
                    hits+=1;clearance=simple[0].z-height_cm(x,z);highest=max(highest,clearance)
                    if clearance>1:exposed+=1
        if not hits or not exposed:raise RuntimeError('Rock body lacks exposed native collision surface: '+body['id'])
        rows.append(dict(id=body['id'],traceSamples=9,simpleComplexHits=hits,exposedHits=exposed,maximumExposedCm=highest,vertexBeddingSurrogate=contact))
    return dict(bodies=rows,simpleComplexTraceVerified=True,actualExposedSurfaceVerified=True,walkingAccepted=False,drivingAccepted=False,navigationAccepted=False)
