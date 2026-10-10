"""Bounded static/room/light cloning for frozen private T1 candidates."""
import unreal

LIGHT_FIELDS = ('attenuation_radius', 'cast_shadows', 'source_radius', 'soft_source_radius', 'source_length',
                'temperature', 'use_temperature', 'specular_scale')


def vector(value): return [value.x, value.y, value.z]
def rotation(value): return [value.pitch, value.yaw, value.roll]


def inventory(actors):
    result = {}
    for actor in actors.get_all_level_actors():
        if not isinstance(actor, (unreal.StaticMeshActor, unreal.WarPracticalLight, unreal.WarInteriorAtmosphere)):
            continue
        label = actor.get_actor_label()
        if label in result:
            raise RuntimeError('Candidate actor labels must be unique')
        state = dict(location=vector(actor.get_actor_location()), rotation=rotation(actor.get_actor_rotation()),
            scale=vector(actor.get_actor_scale3d()), tags=list(map(str, actor.tags)))
        if isinstance(actor, unreal.StaticMeshActor):
            component = actor.static_mesh_component
            state.update(kind='mesh', mesh=component.static_mesh.get_path_name(),
                materials=[component.get_material(i).get_path_name() for i in range(component.get_num_materials())],
                collision=str(component.get_collision_profile_name()))
            if 'WarT1DistantScenery' in state['tags']:
                state['distantPolicy']={k:component.get_editor_property(k) for k in ('cast_shadow','can_ever_affect_navigation','generate_overlap_events','affect_distance_field_lighting')}
        elif isinstance(actor, unreal.WarPracticalLight):
            component = actor.get_component_by_class(unreal.PointLightComponent)
            color = component.get_editor_property('light_color')
            state.update(kind='light', zone=str(actor.get_editor_property('zone_id')),
                day=actor.get_editor_property('day_lumens'), night=actor.get_editor_property('night_lumens'),
                color=[color.r, color.g, color.b, color.a], properties={p: component.get_editor_property(p) for p in LIGHT_FIELDS})
        else:
            state.update(kind='room', zone=str(actor.get_editor_property('zone_id')),
                day=actor.get_editor_property('day_exposure_bias'), night=actor.get_editor_property('night_exposure_bias'),
                extent=vector(actor.room_bounds.get_unscaled_box_extent()),
                exposure={p: actor.exposure.get_editor_property(p) for p in ('priority', 'blend_radius', 'blend_weight', 'enabled', 'unbound')})
        result[label] = state
    return result


def clone(actors, states, overrides):
    classes = dict(mesh=unreal.StaticMeshActor, light=unreal.WarPracticalLight, room=unreal.WarInteriorAtmosphere)
    for label, state in states.items():
        pitch, yaw, roll = state['rotation']
        actor = actors.spawn_actor_from_class(classes[state['kind']], unreal.Vector(*state['location']), unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll))
        actor.set_actor_scale3d(unreal.Vector(*state['scale']))
        actor.set_actor_label(label); actor.tags = state['tags']
        if state['kind'] == 'mesh':
            component = actor.static_mesh_component
            component.set_static_mesh(unreal.load_asset(state['mesh']))
            for index, material in enumerate(state['materials']):
                component.set_material(index, overrides[label] if label in overrides else unreal.load_asset(material))
            component.set_collision_profile_name(state['collision'])
            for name,value in state.get('distantPolicy',{}).items():component.set_editor_property(name,value)
        elif state['kind'] == 'light':
            actor.set_editor_property('zone_id', state['zone'])
            actor.set_editor_property('day_lumens', state['day']); actor.set_editor_property('night_lumens', state['night'])
            component = actor.get_component_by_class(unreal.PointLightComponent)
            red, green, blue, alpha = state['color']
            component.set_editor_property('light_color', unreal.Color(r=red, g=green, b=blue, a=alpha))
            for name, value in state['properties'].items(): component.set_editor_property(name, value)
        else:
            actor.set_editor_property('zone_id', state['zone'])
            actor.set_editor_property('day_exposure_bias', state['day']); actor.set_editor_property('night_exposure_bias', state['night'])
            actor.room_bounds.set_box_extent(unreal.Vector(*state['extent']), False)
            for name, value in state['exposure'].items(): actor.exposure.set_editor_property(name, value)
