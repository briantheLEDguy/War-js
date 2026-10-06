"""Read-only native mesh, material, lighting and collision-owner diagnostics.

Root executes this with native writers serialized. Optional unavailable Python
properties are reported explicitly; no settings, actors or packages are saved.
"""
import json
import os
import re
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT,sha
from shared_city_sources import package_file
from world_actor_state import snapshot,value_repr

revision=os.environ.get('WAR_CITADEL_INSPECT_REVISION')
if revision and not re.fullmatch('[a-f0-9]{12}',revision):raise RuntimeError('Invalid explicit citadel inspection revision')
current=dict(revision=revision) if revision else json.loads((OUT/'current.json').read_text())
RUN=OUT/current['revision']
candidate=json.loads((RUN/'candidate.json').read_text());source=json.loads((RUN/'assets-source.json').read_text())
expected={**candidate['sourceHashes'],**candidate['packageHashes']}
before={p:sha(package_file(ROOT,p)) for p in expected}
if before!=expected:raise RuntimeError('Preserve independently edited candidate/source packages')
assets=unreal.EditorAssetLibrary;lib=unreal.MaterialEditingLibrary
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh_tools=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
unavailable=[]

def serial(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if hasattr(value,'get_path_name'):return value.get_path_name()
    if isinstance(value,(list,tuple,unreal.Array)):return [serial(v) for v in value]
    return value_repr(value)

def read(obj,names):
    result={}
    for name in names:
        try:result[name]=serial(obj.get_editor_property(name))
        except Exception as error:
            unavailable.append(dict(object=serial(obj),property=name,error=str(error)))
    return result

def call(obj,name,*args):
    try:return getattr(obj,name)(*args)
    except Exception as error:
        unavailable.append(dict(object=serial(obj),method=name,error=str(error)));return None

meshes=[]
for binding in candidate['bindings']:
    mesh=assets.load_asset(binding['mesh'])
    if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing source-bound native static mesh')
    materials=mesh.get_editor_property('static_materials');lods=[]
    for lod in range(mesh.get_num_lods()):
        settings=call(mesh_tools,'get_lod_build_settings',mesh,lod)
        sections=[]
        for section in range(mesh.get_num_sections(lod)):
            slot=call(mesh_tools,'get_lod_material_slot',mesh,lod,section)
            sections.append(dict(section=section,slot=slot,material=serial(mesh.get_material(slot)) if slot is not None and slot>=0 else None))
        lods.append(dict(lod=lod,triangles=mesh.get_num_triangles(lod),sectionCount=len(sections),sections=sections,
            uvChannels=call(mesh_tools,'get_num_uv_channels',mesh,lod),
            build=read(settings,('recompute_normals','recompute_tangents','use_mikk_t_space','compute_weighted_normals',
                'remove_degenerates','generate_lightmap_u_vs','src_lightmap_index','dst_lightmap_index',
                'min_lightmap_resolution','use_full_precision_u_vs','use_high_precision_tangent_basis',
                'build_scale3d','distance_field_resolution_scale','generate_distance_field_as_if_two_sided',
                'max_lumen_mesh_cards')) if settings else None))
    meshes.append(dict(id=binding['id'],path=binding['mesh'],owner=assets.get_metadata_tag(mesh,'WarCapitalTerrain'),
        renderDataAudit=json.loads(unreal.WarImportLibrary.describe_static_mesh_render_data(mesh)),
        materialSlots=[read(slot,('material_interface','material_slot_name','imported_material_slot_name')) for slot in materials],
        properties=read(mesh,('light_map_coordinate_index','light_map_resolution','allow_cpu_access','support_ray_tracing')),
        lods=lods))

material_rows=[];textures={}
for role in source['materialSpecs']:
    material=assets.load_asset('/Game/WorldRebuild/AegisCitadel_'+current['revision']+'/Materials/M_'+role)
    if not isinstance(material,unreal.Material):raise RuntimeError('Missing native material role')
    inputs={}
    for name in ('BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION','EMISSIVE_COLOR'):
        prop=getattr(unreal.MaterialProperty,'MP_'+name)
        node=call(lib,'get_material_property_input_node',material,prop)
        inputs[name]=dict(node=serial(node),output=call(lib,'get_material_property_input_node_output_name',material,prop))
    expressions=[]
    for node in call(lib,'get_material_expressions',material) or []:
        row=dict(node=serial(node),type=node.get_class().get_name(),
            inputs=call(lib,'get_material_expression_input_names',node),
            outputs=call(lib,'get_material_expression_output_names',node),
            upstream=[serial(n) for n in call(lib,'get_inputs_for_material_expression',material,node) or []])
        if isinstance(node,unreal.MaterialExpressionTextureSample):
            row['values']=read(node,('texture','sampler_type','const_coordinate','mip_value_mode'))
            texture=node.texture
            if texture:textures[texture.get_path_name()]=texture
        elif isinstance(node,unreal.MaterialExpressionConstant3Vector):row['values']=read(node,('constant',))
        elif isinstance(node,unreal.MaterialExpressionConstant):row['values']=read(node,('r',))
        expressions.append(row)
    material_rows.append(dict(role=role,path=material.get_path_name(),
        properties=read(material,('two_sided','blend_mode','shading_model','tangent_space_normal','use_material_attributes')),
        expectedSource=source['materialSpecs'][role],propertyInputs=inputs,expressions=expressions))
texture_rows=[]
for path,texture in textures.items():
    data=read(texture,('srgb','compression_settings','mip_gen_settings','power_of_two_mode','lod_group',
        'lod_bias','never_stream','filter','address_x','address_y','virtual_texture_streaming','asset_import_data'))
    import_data=texture.get_editor_property('asset_import_data')
    texture_rows.append(dict(path=path,properties=data,sourceFiles=call(import_data,'extract_filenames') if import_data else [],
        sizeX=call(texture,'blueprint_get_size_x'),sizeY=call(texture,'blueprint_get_size_y'),
        mipCount=call(texture,'get_num_mips')))

if not levels.load_level(candidate['siegeMap']):raise RuntimeError('Cannot load exact private siege map')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
lighting=[];collision_owners=[];recast=[];starts=[];battlefields=[]
requested={'StaticMeshActor_1','StaticMeshActor_2','StaticMeshActor_4','StaticMeshActor_1125','StaticMeshActor_1144'}
for actor in actors.get_all_level_actors():
    class_name=actor.get_class().get_name();package=actor.get_outer().get_path_name().split('.')[0]
    if actor.get_name() in requested:
        origin,extent=actor.get_actor_bounds(False)
        components=[]
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            center,size,_=unreal.SystemLibrary.get_component_bounds(component)
            components.append(dict(name=component.get_name(),mesh=serial(component.static_mesh),
                boundsCm=[[center.x-size.x,center.y-size.y,center.z-size.z],[center.x+size.x,center.y+size.y,center.z+size.z]],
                properties=read(component,('can_ever_affect_navigation','cast_shadow','cast_dynamic_shadow','cast_static_shadow',
                    'affect_distance_field_lighting','force_mip_streaming','lightmap_type'))))
        collision_owners.append(dict(path=actor.get_path_name(),package=package,state=snapshot(actor),components=components,
            boundsCm=[[origin.x-extent.x,origin.y-extent.y,origin.z-extent.z],[origin.x+extent.x,origin.y+extent.y,origin.z+extent.z]]))
    if isinstance(actor,unreal.PlayerStart):starts.append(dict(path=actor.get_path_name(),state=snapshot(actor)))
    if isinstance(actor,unreal.WarSiegeBattlefield):
        battlefields.append(dict(path=actor.get_path_name(),stageGates=[serial(a) for a in actor.get_editor_property('stage_gates')],
            mechanismPads=[serial(a) for a in actor.get_editor_property('gate_mechanisms')]))
    if isinstance(actor,unreal.RecastNavMesh):
        try:resolution=actor.get_editor_property('nav_mesh_resolution_params')
        except Exception as error:
            unavailable.append(dict(object=actor.get_path_name(),property='nav_mesh_resolution_params',error=str(error)))
            resolution=[]
        recast.append(dict(path=actor.get_path_name(),properties=read(actor,('agent_radius','agent_height','agent_max_slope',
            'agent_max_step_height','cell_size','cell_height','tile_size_uu','max_simplification_error','runtime_generation')),
            resolutions=[read(s,('cell_size','cell_height','agent_max_step_height')) for s in resolution]))
    if isinstance(actor,(unreal.Light,unreal.SkyLight,unreal.SkyAtmosphere,unreal.ExponentialHeightFog,unreal.PostProcessVolume)):
        row=dict(path=actor.get_path_name(),package=package,state=snapshot(actor))
        for component in actor.get_components_by_class(unreal.ActorComponent):
            if isinstance(component,(unreal.LightComponent,unreal.SkyLightComponent)):
                row.setdefault('lights',[]).append(dict(name=component.get_name(),values=read(component,('mobility','visible',
                    'intensity','light_color','cast_shadows','use_temperature','temperature','indirect_lighting_intensity',
                    'volumetric_scattering_intensity','affect_translucent_lighting'))))
            if isinstance(component,unreal.SkyLightComponent):
                row['skyFill']=read(component,('source_type','cubemap','real_time_capture','lower_hemisphere_is_black',
                    'lower_hemisphere_color','intensity','mobility','visible','cast_shadows','indirect_lighting_intensity'))
            if isinstance(component,unreal.DirectionalLightComponent):
                row.setdefault('directional',[]).append(read(component,('atmosphere_sun_light','atmosphere_sun_light_index',
                    'forward_shading_priority','light_source_angle','light_source_soft_angle','dynamic_shadow_distance_movable_light',
                    'dynamic_shadow_distance_stationary_light','intensity','light_color','mobility','visible')))
            if isinstance(component,unreal.ExponentialHeightFogComponent):
                row['fog']=read(component,('fog_density','fog_height_falloff','fog_inscattering_luminance','start_distance',
                    'fog_max_opacity','enable_volumetric_fog','volumetric_fog_scattering_distribution'))
        if isinstance(actor,unreal.PostProcessVolume):
            settings=actor.get_editor_property('settings')
            keys=('auto_exposure_method','auto_exposure_bias','auto_exposure_apply_physical_camera_exposure',
                'auto_exposure_min_brightness','auto_exposure_max_brightness','camera_iso','camera_shutter_speed',
                'depth_of_field_fstop','color_saturation','color_gamma','color_gamma_shadows','white_temp','white_tint',
                'indirect_lighting_color','indirect_lighting_intensity','dynamic_global_illumination_method','reflection_method')
            keys=(*keys,'auto_exposure_speed_up','auto_exposure_speed_down','bloom_intensity','lens_flare_intensity')
            row['exposure']=read(settings,[*keys,*['override_'+k for k in keys]])
        lighting.append(row)
after={p:sha(package_file(ROOT,p)) for p in expected}
if before!=after:raise RuntimeError('A native package changed during read-only inspection')
report=dict(schemaVersion=1,readOnly=True,revision=current['revision'],signature=candidate['signature'],
    cityRevision=candidate['city']['revision'],geometrySignature=candidate['geometrySignature'],
    meshes=meshes,materials=material_rows,textures=texture_rows,lighting=lighting,recast=recast,
    collisionOwners=collision_owners,battlefields=battlefields,playerStarts=starts,
    missingCollisionOwnerNames=sorted(requested-{r['path'].rsplit('.',1)[-1] for r in collision_owners}),
    lightingProfiles=call(unreal.WarZoneLightingSubsystem,'describe_profiles'),unavailableProperties=unavailable,
    sourceAndCandidateHashesUnchanged=True,packageHashes=before,visualApproved=False,physicalTraversalApproved=False)
output=RUN/'native-inspection.json';output.write_text(json.dumps(report,indent=2,default=serial)+'\n')
unreal.log('WAR_CITADEL_NATIVE_INSPECTED='+str(output))
