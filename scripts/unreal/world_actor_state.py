"""Compare authored component state when moving content between level packages."""
import re
import unreal


def value_repr(value):
    # Unreal's struct repr includes its temporary Python wrapper address, which is not content.
    return re.sub(r'\(0x[0-9a-fA-F]+\)', '(address)', str(value))


def transform(value):
    t, r, s = value.translation, value.rotation, value.scale3d
    return [round(v, 6) for v in (t.x,t.y,t.z,r.x,r.y,r.z,r.w,s.x,s.y,s.z)]


def snapshot(actor):
    components=[]
    for component in actor.get_components_by_class(unreal.ActorComponent):
        # Native transient gear is reconstructed from its catalog, never authored into this level.
        if unreal.WarNpcEquipmentLibrary.is_generated_attachment(component): continue
        # The optional dummy component has no authored content on skeletal enemies.
        if (isinstance(component,unreal.StaticMeshComponent) and component.get_name()=='TrainingMesh'
                and not component.static_mesh): continue
        row={'name':component.get_name(),'class':component.get_class().get_name(),
             'tags':sorted(str(t) for t in component.component_tags)}
        if isinstance(component,unreal.SceneComponent):
            row.update(transform=transform(component.get_relative_transform()),
                       visible=component.is_visible(),mobility=str(component.mobility))
        if isinstance(component,unreal.PrimitiveComponent):
            row.update(collision=str(component.get_collision_profile_name()),
                       collisionEnabled=str(component.get_collision_enabled()))
        if isinstance(component,unreal.MeshComponent):
            mesh=component.static_mesh if isinstance(component,unreal.StaticMeshComponent) else (
                component.get_skeletal_mesh_asset() if isinstance(component,unreal.SkeletalMeshComponent) else None)
            row.update(mesh=mesh.get_path_name() if mesh else None,
                       materials=[component.get_material(i).get_path_name() if component.get_material(i) else None
                                  for i in range(component.get_num_materials())])
        if isinstance(component,unreal.BoxComponent): row['extent']=value_repr(component.get_unscaled_box_extent())
        if isinstance(component,unreal.LightComponent):
            row['light']={key:value_repr(component.get_editor_property(key)) for key in
                          ('intensity','light_color','cast_shadows','use_temperature','temperature')}
        if isinstance(component,unreal.PointLightComponent):
            row['point']={key:value_repr(component.get_editor_property(key)) for key in
                          ('attenuation_radius','source_radius','soft_source_radius','source_length','intensity_units')}
        if isinstance(component,unreal.ExponentialHeightFogComponent):
            row['fog']={key:value_repr(component.get_editor_property(key)) for key in
                        ('fog_density','fog_height_falloff','fog_inscattering_luminance','start_distance','enable_volumetric_fog')}
        if isinstance(component,unreal.SkyLightComponent):
            row['sky']={key:value_repr(component.get_editor_property(key)) for key in
                        ('intensity','light_color','source_type','cubemap','real_time_capture')}
        if isinstance(component,unreal.AudioComponent):
            row['audio']={key:value_repr(component.get_editor_property(key)) for key in
                          ('sound','volume_multiplier','pitch_multiplier','auto_activate','allow_spatialization')}
        components.append(row)
    state={'class':actor.get_class().get_name(),'label':actor.get_actor_label(),
           'transform':transform(actor.get_actor_transform()),'tags':sorted(str(t) for t in actor.tags),
           'components':sorted(components,key=lambda row:row['name'])}
    if isinstance(actor,unreal.PostProcessVolume):
        state['postProcess']={key:value_repr(actor.get_editor_property(key)) for key in
                              ('settings','unbound','enabled','priority','blend_weight','blend_radius')}
    if isinstance(actor,(unreal.WarCityNpc,unreal.WarQuestNpc)):
        state['npc']=str(actor.get_editor_property('npc_id'))
    if isinstance(actor,unreal.WarResourceNode):
        state['node']=str(actor.get_editor_property('node_id'))
    return state
