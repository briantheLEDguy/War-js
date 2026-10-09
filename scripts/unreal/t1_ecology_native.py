"""Native cosmetic detail construction and exact saved-instance verification."""
import math
import unreal
from t1_water_surface import water_surface


def ground_cover(actors,assets,identity,data,layout):
    mesh=assets.composite(identity+'_regional_ground_cover',data,False)
    for i in range(mesh.get_num_sections(0)):
        material=mesh.get_material(i); material.set_editor_property('used_with_instanced_static_meshes',True)
        unreal.MaterialEditingLibrary.recompile_material(material); unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    actor=actors.spawn_actor_from_class(unreal.WarLandscapeDetail,unreal.Vector()); actor.set_actor_label(identity+'_landscape_ground_cover')
    transforms=[unreal.Transform(location=unreal.Vector(*r['location']),rotation=unreal.Rotator(yaw=r['yaw']),scale=unreal.Vector(r['scale'],r['scale'],r['scale'])) for r in layout]
    if not actor.configure(mesh,transforms): raise RuntimeError('Native ground cover rejected trusted batch')
    actual=cover_inventory(actors); return actual[identity+'_landscape_ground_cover']


def cover_inventory(actors):
    result={}
    for actor in actors.get_all_level_actors():
        if not isinstance(actor,unreal.WarLandscapeDetail): continue
        label=actor.get_actor_label()
        if label in result:raise RuntimeError('Duplicate saved ground-cover identity')
        if any(abs(v)>1e-6 for v in (actor.get_actor_location().x,actor.get_actor_location().y,actor.get_actor_location().z,
            actor.get_actor_rotation().pitch,actor.get_actor_rotation().yaw,actor.get_actor_rotation().roll)) or any(abs(v-1)>1e-6 for v in (actor.get_actor_scale3d().x,actor.get_actor_scale3d().y,actor.get_actor_scale3d().z)):
            raise RuntimeError('Ground-cover instance frame must remain native identity')
        c=actor.details; rows=[]
        if actor.get_editor_property('replicates') or c.get_editor_property('cast_shadow') or c.instance_start_cull_distance!=3500 or c.instance_end_cull_distance!=12000:
            raise RuntimeError('Saved ground-cover cosmetic/culling policy differs')
        if c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION or c.get_editor_property('generate_overlap_events'): raise RuntimeError('Ground cover must remain nonblocking')
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,world_space=False)
            if t is None: raise RuntimeError('Missing saved cover instance')
            p=t.translation; q=t.rotation; s=t.scale3d
            rows.append(dict(location=[p.x,p.y,p.z],quaternion=[q.x,q.y,q.z,q.w],scale=[s.x,s.y,s.z]))
        result[actor.get_actor_label()]=dict(mesh=c.static_mesh.get_path_name(),materials=[c.get_material(i).get_path_name() for i in range(c.get_num_materials())],
            instances=rows,count=len(rows),collision='NoCollision',localCosmetic=True,appearanceApproved=False)
    return result


def water_material(assets,identity,noise_channel):
    recipe=water_surface(identity)
    material=assets.tools.create_asset('M_'+identity+'_shallow_water',assets.folder+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if not material: raise RuntimeError('Cannot create native shallow water')
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    lib=unreal.MaterialEditingLibrary
    def constant(value):
        if isinstance(value,list):
            n=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector);n.set_editor_property('constant',unreal.LinearColor(*value,1))
        else:
            n=lib.create_material_expression(material,unreal.MaterialExpressionConstant);n.set_editor_property('r',value)
        return n
    for value,pin in [(recipe['color'],unreal.MaterialProperty.MP_BASE_COLOR),(recipe['roughness'],unreal.MaterialProperty.MP_ROUGHNESS),(recipe['specular'],unreal.MaterialProperty.MP_SPECULAR),(recipe['opacity'],unreal.MaterialProperty.MP_OPACITY)]:
        if not lib.connect_material_property(constant(value),'',pin): raise RuntimeError('Cannot bind shallow water surface')
    def expr(kind,**properties):
        n=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for k,v in properties.items():n.set_editor_property(k,v)
        return n
    def binary(kind,a,b):
        n=expr(kind)
        if not lib.connect_material_expressions(a,'',n,'A') or not lib.connect_material_expressions(b,'',n,'B'):raise RuntimeError('Cannot bind ripple arithmetic')
        return n
    world=expr('WorldPosition');time=expr('Time');components=[]
    for axis in ('r','g'):
        component=expr('ComponentMask',r=axis=='r',g=axis=='g',b=False,a=False)
        if not lib.connect_material_expressions(world,'',component,''):raise RuntimeError('Cannot bind water coordinates')
        components.append(component)
    uv=binary('Divide',binary('AppendVector',*components),constant(recipe['noiseMetres']*100))
    noise=expr('TextureSample',texture=assets.texture(noise_channel,False),sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    if not lib.connect_material_expressions(uv,'',noise,'UVs'):raise RuntimeError('Cannot bind reviewed water phase channel')
    channel=expr('ComponentMask',r=True,g=False,b=False,a=False)
    if not lib.connect_material_expressions(noise,'',channel,''):raise RuntimeError('Cannot select water phase channel')
    # Reviewed terrain colour is dark; normalize its range before gently perturbing wave phase.
    remap=binary('Divide',channel,constant(.18));clamped=expr('Clamp',min_default=0,max_default=1)
    lib.connect_material_expressions(remap,'',clamped,'')
    warp=binary('Multiply',clamped,constant(recipe['phaseWarp']))
    slopes=[constant(0),constant(0)]
    for w in recipe['waves']:
        direction=[math.cos(w['angle']),math.sin(w['angle'])]
        projection=binary('Add',*[binary('Multiply',c,constant(d)) for c,d in zip(components,direction)])
        phase=binary('Add',binary('Divide',projection,constant(w['wavelengthMetres']*100)),
            binary('Add',binary('Multiply',time,constant(w['cyclesPerSecond'])),binary('Add',constant(w['phase']),warp)))
        wave=expr('Sine',period=1);lib.connect_material_expressions(phase,'',wave,'')
        for i,d in enumerate(direction):slopes[i]=binary('Add',slopes[i],binary('Multiply',wave,constant(w['slope']*d)))
    normal=binary('AppendVector',binary('AppendVector',*slopes),constant(1))
    normalized=expr('Normalize');lib.connect_material_expressions(normal,'',normalized,'VectorInput')
    if not lib.connect_material_property(normalized,'',unreal.MaterialProperty.MP_NORMAL):raise RuntimeError('Cannot bind water ripple normal')
    output=lib.create_material_expression(material,unreal.MaterialExpressionSingleLayerWaterMaterialOutput)
    for value,pin in [(recipe['scattering'],'ScatteringCoefficients'),(recipe['absorption'],'AbsorptionCoefficients'),(.2,'PhaseG'),([1,1,1],'ColorScaleBehindWater')]:
        if not lib.connect_material_expressions(constant(value),'',output,pin): raise RuntimeError('Cannot bind water volume: '+pin)
    lib.recompile_material(material);unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    return material
