"""Native population snapshots and terrain-only approach witnesses for private T1 copies."""
import math
import unreal
from t1_population import inside_outline


def values(v): return [v.x, v.y, v.z]


def population_actor(actor):
    npc = isinstance(actor, unreal.WarCityNpc)
    if not npc and not isinstance(actor, unreal.WarResourceNode): raise RuntimeError('Unsupported population actor')
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent) if npc else actor.static_mesh_component
    fields = ('npc_id', 'display_name', 'city_role', 'character_profile') if npc else ('zone_id', 'node_id', 'visual_prop_id')
    identity = {key: str(actor.get_editor_property(key)) for key in fields}
    rotation = actor.get_actor_rotation()
    result = dict(kind='npc' if npc else 'resource', id=identity['npc_id' if npc else 'node_id'], identity=identity,
        label=actor.get_actor_label(), location=values(actor.get_actor_location()), rotation=[rotation.pitch, rotation.yaw, rotation.roll],
        scale=values(actor.get_actor_scale3d()), tags=list(map(str, actor.tags)),
        mesh=(component.get_skeletal_mesh_asset() if npc else component.static_mesh).get_path_name(),
        materials=[component.get_material(i).get_path_name() for i in range(component.get_num_materials())],
        collision=str(component.get_collision_profile_name()), visible=component.is_visible())
    if npc:
        data = component.get_editor_property('animation_data')
        result['animation'] = dict(asset=data.anim_to_play.get_path_name() if data.anim_to_play else None,
            looping=data.saved_looping, playing=data.saved_playing, position=data.saved_position, rate=data.saved_play_rate)
        result['weapons'] = [dict(mesh=c.static_mesh.get_path_name(), materials=[c.get_material(i).get_path_name() for i in range(c.get_num_materials())],
            bone=str(c.get_attach_socket_name())) for c in actor.get_components_by_class(unreal.StaticMeshComponent) if unreal.WarNpcEquipmentLibrary.is_generated_attachment(c)]
    return result


def spawn_population(actors, row):
    source = row['source']; pitch, yaw, roll = source['rotation']
    # Preserve the admitted body correction; only author-facing yaw may change.
    delta = math.degrees(row['definition'].get('rotY', 0)-row.get('canonical', row.get('prop', {})).get('rotY', 0)) if row['kind'] == 'npc' else 0
    npc = row['kind'] == 'npc'
    actor = actors.spawn_actor_from_class(unreal.WarCityNpc if npc else unreal.WarResourceNode,
        unreal.Vector(*row['point']), unreal.Rotator(pitch=pitch, yaw=yaw+delta, roll=roll))
    actor.set_actor_label(row['id']); actor.set_actor_scale3d(unreal.Vector(*source['scale']))
    actor.tags = source['tags']+['WarT1CandidatePopulation']
    for key, value in source['identity'].items(): actor.set_editor_property(key, value)
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent) if npc else actor.static_mesh_component
    mesh = unreal.load_asset(source['mesh'])
    if npc: component.set_skeletal_mesh_asset(mesh)
    else: component.set_static_mesh(mesh)
    for i, material in enumerate(source['materials']): component.set_material(i, unreal.load_asset(material))
    component.set_collision_profile_name(source['collision'])
    if npc:
        data = source['animation']; animation = unreal.load_asset(data['asset'])
        component.override_animation_data(animation, data['looping'], data['playing'], data['position'], data['rate'])
        unreal.WarImportLibrary.prepare_preview_frame(component)
        identity = source['identity']
        if unreal.WarNpcEquipmentLibrary.apply(component, identity['character_profile'], identity['npc_id'], identity['city_role']) != '':
            raise RuntimeError('Retained population equipment failed to restore')
    return actor


class GroundReview:
    def __init__(self, world, actors, zone, outline):
        self.world, self.outline = world, outline
        self.terrain = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == zone+'_terrain')
        self.ignored = [a for a in actors.get_all_level_actors() if a != self.terrain]
        self.samples = 0; self.failures = []

    def failed(self, reason, point, parts=None):
        if len(self.failures) < 128:
            self.failures.append(dict(reason=reason, point=values(point) if isinstance(point, unreal.Vector) else point,
                blocker=parts[9].get_actor_label() if parts and parts[0] and parts[9] else None))
        return None

    def ground(self, point):
        if not inside_outline(point, self.outline): return self.failed('outside_playable_outline', point)
        hit = unreal.SystemLibrary.line_trace_single(self.world, unreal.Vector(point[0], point[1], 20000),
            unreal.Vector(point[0], point[1], -20000), unreal.TraceTypeQuery.ECC_VISIBILITY, True, self.ignored, unreal.DrawDebugTrace.NONE, True)
        parts = hit.to_tuple() if hit else None
        self.samples += 1
        return values(parts[5]) if parts and parts[0] and parts[9] == self.terrain and parts[7].z >= .71 else self.failed('missing_or_unwalkable_terrain', point, parts)

    def center(self, point):
        ground = self.ground(point)
        if ground is None: return None
        v = unreal.Vector(*ground)
        hit = unreal.SystemLibrary.capsule_trace_single(self.world, v+unreal.Vector(0,0,90), v-unreal.Vector(0,0,45), 42,42,
            unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
        parts = hit.to_tuple() if hit else None
        self.samples += 1
        if not parts or not parts[0] or parts[9] != self.terrain or parts[7].z < .71: return self.failed('foot_supported_by_scenery_or_unwalkable', point, parts)
        center = parts[4]+unreal.Vector(0,0,57)
        obstruction = unreal.SystemLibrary.capsule_trace_single(self.world, center, center+unreal.Vector(0,0,.1),42,96,
            unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
        self.samples += 1
        witness = obstruction.to_tuple() if obstruction else None
        return (ground, center) if not witness or not witness[0] else self.failed('blocked_capsule_position', point, witness)

    def approach(self, start, end):
        count = max(1, math.ceil(math.hypot(end[0]-start[0],end[1]-start[1])/50)); points=[]; previous=None
        if count > 1000: return None
        for i in range(count+1):
            point = [start[k]+(end[k]-start[k])*i/count for k in range(3)]
            supported = self.center(point)
            if not supported: return None
            ground, center = supported
            if previous:
                for a,b in ((previous,center),(center,previous)):
                    hit=unreal.SystemLibrary.capsule_trace_single(self.world,a,b,42,96,unreal.TraceTypeQuery.ECC_VISIBILITY,
                        True,[],unreal.DrawDebugTrace.NONE,True)
                    self.samples += 1
                    parts=hit.to_tuple() if hit else None
                    if parts and parts[0]: return self.failed('blocked_capsule_sweep', a, parts)
            points.append(ground); previous=center
        return points
