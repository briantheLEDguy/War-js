"""Opt-in cosmetic meadow batches in isolated T1 candidates; staged source packages remain unchanged."""
from pathlib import Path
import unreal
from t1_meadow_patches import meadow_layout
from t1_nature_canopy_native import nature_sources
from t1_understorey_native import installed_detail_inventory

TAG='WarT1PrivateMeadowPatch'
NAMES=('SM_Grass_01','SM_Grass_Long_01')


def spawn_meadows(assets,actors,source,height_cm,patches,visible_widths=None):
    if not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_') or source.get('id')!='sunmeadow_march':
        raise ValueError('Meadows require isolated first-batch Sunmeadow candidates')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    package=world.get_path_name().split('.')[0]
    if not package.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_') or '/sunmeadow_march/' not in package:
        raise ValueError('Preserve owner maps; meadows require an isolated Sunmeadow scene')
    labels={name:source['id']+'_meadow_'+name for name in NAMES}
    if any(actor.get_actor_label() in labels.values() for actor in actors.get_all_level_actors()):
        raise RuntimeError('Preserve existing meadow actors; author into a fresh candidate')
    sources,inputs=nature_sources(Path(__file__).resolve().parents[2])
    layout=meadow_layout(source,height_cm,patches,visible_widths)
    # WarLandscapeDetail admits at most 12000 instances per native actor.
    if any(sum(row['mesh']==name for row in layout['rows'])>12000 for name in NAMES):
        raise ValueError('Meadow species exceeds native batch limit')
    prepared=[]
    for name in NAMES:
        rows=[row for row in layout['rows'] if row['mesh']==name]
        if not rows:continue
        mesh=unreal.load_asset(sources[name]['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing exact installed meadow mesh')
        inventory=installed_detail_inventory(mesh);bounds=mesh.get_bounds();minimum=bounds.origin.z-bounds.box_extent.z
        transforms=[unreal.Transform(location=unreal.Vector(row['z']*100,row['x']*100,row['y']-minimum*row['scale']-1),rotation=unreal.Rotator(yaw=row['yaw']),scale=unreal.Vector(row['scale'],row['scale'],row['scale'])) for row in rows]
        prepared.append((name,mesh,transforms,inventory))
    spawned=[];bindings=[]
    try:
        for name,mesh,transforms,inventory in prepared:
            actor=actors.spawn_actor_from_class(unreal.WarLandscapeDetail,unreal.Vector())
            if actor is None:raise RuntimeError('Unable to spawn meadow batch')
            spawned.append(actor);actor.set_actor_label(labels[name]);actor.tags=[TAG]
            if not actor.configure(mesh,transforms) or actor.details.get_instance_count()!=len(transforms):
                raise RuntimeError('Native meadow rejects bounded source transforms')
            if actor.details.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION:
                raise RuntimeError('Cosmetic meadow must remain nonblocking')
            actor.details.set_cull_distances(8000,18000)
            if actor.details.get_editor_property('instance_start_cull_distance')!=8000 or actor.details.get_editor_property('instance_end_cull_distance')!=18000:
                raise RuntimeError('Native meadow culling differs from authoring contract')
            bindings.append(dict(id=labels[name],mesh=mesh.get_path_name(),instances=len(transforms),inventory=inventory))
    except Exception:
        for actor in reversed(spawned):actors.destroy_actor(actor)
        raise
    return spawned,dict(map=package,layout={k:v for k,v in layout.items() if k!='rows'},bindings=bindings,sourceInputs=inputs,collision='NoCollision',cullMetres=[80,180],localCosmetic=True,nativeIntegrated=False,ordinaryPersistenceAccepted=False,appearanceApproved=False,performanceAccepted=False)
