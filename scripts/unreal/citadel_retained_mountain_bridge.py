"""Actual Unreal callbacks for the retained MI study; importable without Unreal.

Only the two fresh private material packages may be edited/saved. Fresh native
observations are signature inputs; archival reflection strings are insufficient.
"""
import copy
import json
import math
from pathlib import Path
import re

from citadel_retained_mountain_adapter import SOURCE_INSTANCE, SOURCE_PARENT, digest, package

VECTOR_KEYS={'parameter_name','default_value','group','sort_priority','expression_guid',
    'use_custom_primitive_data','primitive_data_index','channel_names'}


def checked_vector_values(values):
    if not isinstance(values,dict) or set(values)!=VECTOR_KEYS:
        raise RuntimeError('Eight exact native VectorParameter values required')
    for key in ('parameter_name','group'):
        if not isinstance(values[key],str) or len(values[key])>4096:
            raise RuntimeError('Bounded native vector parameter name/group required')
    guid=values['expression_guid']
    if not isinstance(guid,str) or not re.fullmatch('[a-fA-F0-9]{32}',guid) or int(guid,16)==0:
        raise RuntimeError('Meaningful native expression GUID required')
    if (type(values['sort_priority']) is not int or not -(2**31)<=values['sort_priority']<2**31
            or type(values['use_custom_primitive_data']) is not bool
            or type(values['primitive_data_index']) is not int or not 0<=values['primitive_data_index']<=255):
        raise RuntimeError('Typed native vector parameter metadata required')
    color=values['default_value']
    if (not isinstance(color,list) or len(color)!=4
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in color)):
        raise RuntimeError('Finite native parameter default color required')
    channels=values['channel_names']
    if not isinstance(channels,dict) or set(channels)!=set('rgba'):
        raise RuntimeError('All four native channel histories required')
    for value in channels.values():
        if (not isinstance(value,dict) or set(value)!={'display','history'}
                or any(not isinstance(v,str) or len(v)>4096 for v in value.values())):
            raise RuntimeError('Native FText display/history required; reflected struct strings are insufficient')
    digest(values)
    return copy.deepcopy(values)


def vector_readback(unreal,node):
    document=json.loads(unreal.WarImportLibrary.describe_vector_parameter(node))
    if (set(document)!={'schemaVersion','readOnly','available','profile','expression','expressionClass','values'}
            or document['schemaVersion']!=1 or document['readOnly'] is not True or document['available'] is not True
            or document['profile']!='vector_parameter_identity_v1' or document['expression']!=node.get_path_name()
            or document['expressionClass']!='MaterialExpressionVectorParameter'):
        raise RuntimeError('Unavailable or wrong native VectorParameter profile')
    return checked_vector_values(document['values'])


def signed_closure(candidate):
    sources=candidate.get('sourceHashes',{});owned=candidate.get('packageHashes',{})
    if not sources or not owned or any(sources[k]!=owned[k] for k in set(sources)&set(owned)):
        raise RuntimeError('Complete conflict-free signed candidate package closure required')
    hashes={**sources,**owned}
    if any(not re.fullmatch('[a-f0-9]{64}',str(v)) for v in hashes.values()):
        raise RuntimeError('Invalid signed source package hash')
    return hashes


def package_hashes(root,candidate):
    from citadel_performance_evidence import performance_package_file
    from citadel_private_surface_study import sha
    return {name:sha(performance_package_file(root,name)) for name in signed_closure(candidate)}


class UnrealMountainOperations:
    def __init__(self,unreal,root,candidate,destination=None,duplicate=None):
        self.unreal=unreal;self.root=Path(root).resolve();self.candidate=copy.deepcopy(candidate)
        self.destination=destination;self.duplicate_callback=duplicate;self.observed_world=None
        self.targets={}
        if destination is not None:
            if (not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}',destination)
                    or destination=='/Game/WorldRebuild/AegisCitadel_'+candidate['revision']):
                raise RuntimeError('A distinct fresh private study destination is required')
            self.targets={destination+'/Materials/M_PrivateSurface_mountain':package(SOURCE_PARENT),
                destination+'/Materials/MI_PrivateSurface_mountain':package(SOURCE_INSTANCE)}

    def _asset(self,path):
        package(path)
        asset=self.unreal.load_asset(path)
        if not asset or asset.get_path_name()!=path:
            raise RuntimeError('Required exact native material asset is unavailable: '+path)
        return asset

    def _owned(self,path):
        if package(path) not in self.targets:raise RuntimeError('Refuse to edit/save an unowned material')
        return self._asset(path)

    def source_hashes(self):return package_hashes(self.root,self.candidate)

    def read_instance(self,path):
        asset=self._asset(path)
        return json.loads(self.unreal.WarImportLibrary.describe_material_instance(asset))

    def read_graph(self,path):
        from citadel_private_surface_study import graph_readback
        asset=self._asset(path)
        if asset.get_class().get_name()!='Material':raise RuntimeError('Base graph requires an actual Material')
        return graph_readback(self.unreal,asset)

    def read_actor_binding(self,binding):
        from world_actor_state import snapshot
        u=self.unreal;levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not levels.load_level(binding['level']):raise RuntimeError('Cannot load the exact signed retained source level')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        if not world or world.get_path_name().split('.')[0]!=binding['level']:
            raise RuntimeError('Actual inspection world differs from the signed source level')
        u.GameplayStatics.flush_level_streaming(world);self.observed_world=world.get_path_name().split('.')[0]
        actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
        matches=[a for a in actors if a.get_name()==binding['actor'] and a.get_outer().get_path_name().split('.')[0]==binding['level']]
        if len(matches)!=1:raise RuntimeError('Exact retained actor is missing or duplicated')
        return snapshot(matches[0])

    def exists(self,path):
        if path not in self.targets:raise RuntimeError('Unowned private destination query')
        if self.unreal.EditorAssetLibrary.does_asset_exist(path):return True
        base=self.root/'unreal/AegisWar/Content'/path.removeprefix('/Game/')
        return any(base.with_suffix(suffix).exists() for suffix in ('.uasset','.umap'))

    def duplicate(self,source,target):
        if self.targets.get(target)!=source or self.exists(target) or self.duplicate_callback is None:
            raise RuntimeError('Only fresh exact parent/MI copies are permitted')
        self.duplicate_callback(source,target)
        if not self.unreal.EditorAssetLibrary.does_asset_exist(target):raise RuntimeError('Private material duplication failed')

    def set_parent(self,instance,parent):
        if (package(instance)!=self.destination+'/Materials/MI_PrivateSurface_mountain'
                or package(parent)!=self.destination+'/Materials/M_PrivateSurface_mountain'):
            raise RuntimeError('Only the fresh private instance parent can be retargeted')
        self.unreal.MaterialEditingLibrary.set_material_instance_parent(self._owned(instance),self._owned(parent))

    def add_alpine_base_color(self,path,shader_source):
        from citadel_private_surface_study import graph_readback,_new_shader
        u=self.unreal;material=self._owned(path);lib=u.MaterialEditingLibrary
        original=lib.get_material_property_input_node(material,u.MaterialProperty.MP_BASE_COLOR)
        if not original or original.get_class().get_name()!='MaterialExpressionMultiply':
            raise RuntimeError('Original texture-times-instance-tint BaseColor is required')
        position=lib.create_material_expression(material,u.MaterialExpressionWorldPosition)
        normal=lib.create_material_expression(material,u.MaterialExpressionVertexNormalWS)
        shader=_new_shader(u,material,'Bastion retained mountain alpine BaseColor with original UVs',shader_source,
            dict(P=(position,''),N=(normal,''),Rock=(original,'')))
        graph=graph_readback(u,material)
        return dict(graph=graph,additions={n.get_name():graph['nodes'][n.get_name()] for n in (position,normal,shader)},shader=shader.get_name())

    def compile_and_save(self,parent,instance):
        u=self.unreal;base=self._owned(parent);mi=self._owned(instance)
        if u.MaterialEditingLibrary.recompile_material(base):raise RuntimeError('Private material reported compile errors')
        u.MaterialEditingLibrary.update_material_instance(mi)
        for asset in (base,mi):
            if not u.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):
                raise RuntimeError('Cannot save the exact fresh private material')
        # load_asset is an in-process read; cold saved-package verification remains separate.


def inspect_current_mountain(unreal,root,candidate):
    """Return fresh actual readbacks; do not reuse or relabel the old inspection."""
    from citadel_private_surface_study import _pins
    operations=UnrealMountainOperations(unreal,root,candidate)
    closure=signed_closure(candidate);before=operations.source_hashes()
    if before!=closure:raise RuntimeError('Signed candidate package bytes changed before inspection')
    carves=candidate.get('terrainCarves',[])
    if len(carves)!=1:raise RuntimeError('Exactly one signed retained mountain binding required')
    measured=carves[0];binding=dict(level=measured['package'],actor=measured['actor'])
    actor=operations.read_actor_binding(binding)
    if actor!=measured['actualActorState']:raise RuntimeError('Actual retained actor differs from the signed candidate')
    instance=operations.read_instance(SOURCE_INSTANCE);parent=operations._asset(SOURCE_PARENT)
    graph=operations.read_graph(SOURCE_PARENT)
    native_roots=json.loads(unreal.WarImportLibrary.describe_material_roots(parent))
    if graph['roots']!=native_roots.get('roots'):raise RuntimeError('Actual parent root observation changed during inspection')
    nodes=[dict(name=node.get_name(),expressionClass=node.get_class().get_name(),pins=_pins(unreal,node))
        for node in unreal.MaterialEditingLibrary.get_material_expressions(parent)]
    after=operations.source_hashes()
    if after!=before:raise RuntimeError('Native source package bytes changed during inspection')
    observation=dict(schemaVersion=1,readOnly=True,sourceBytesPreserved=True,
        inspectionKind='fresh_native_retained_mountain_v1',map=operations.observed_world,
        candidateMap=candidate['siegeMap'],candidateSha256=digest(candidate),candidateCityRevision=candidate['city']['revision'],
        sourcePackageHashes=closure,actorReadback=dict(level=measured['package'],actor=measured['actor'],state=actor),
        materials=[SOURCE_INSTANCE],chain=[dict(material=instance.get('material'),materialClass=instance.get('materialClass'),
            parent=instance.get('parent'),effectiveGlobalParameters=instance.get('effectiveGlobalParameters')),
            dict(material=parent.get_path_name(),materialClass=parent.get_class().get_name(),nativeRoots=native_roots,nodes=nodes)],
        instanceReadback=instance,parentGraphReadback=graph,visualApproved=False)
    from citadel_retained_mountain_adapter import plan_adapter,checked_instance,checked_graph
    from aegis_citadel_mountain_material import MOUNTAIN_SHADER
    # Validate completeness before the observation can enter a study signature.
    plan=plan_adapter(candidate,observation,'/Game/WorldRebuild/AegisCitadel_000000000001',MOUNTAIN_SHADER)
    checked_instance(instance,SOURCE_INSTANCE,SOURCE_PARENT,plan);checked_graph(graph,plan)
    return observation


def create_mountain(unreal,destination,source_dir,candidate,spec,duplicate):
    from citadel_retained_mountain_adapter import plan_adapter,create_adapter,checked_instance,checked_graph
    from aegis_citadel_mountain_material import mountain_render_normal_convention,MOUNTAIN_SHADER
    from citadel_private_surface_study import verify_bindings
    root=Path(source_dir).resolve().parents[3]
    required={'scripts/unreal/citadel_retained_mountain_bridge.py','scripts/unreal/citadel_retained_mountain_adapter.py',
        'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarMaterialInstanceReadback.cpp',
        'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarVectorParameterReadback.cpp'}
    if (spec.get('sourceRevision')!=candidate.get('revision') or spec.get('sourcePackageHashes')!=signed_closure(candidate)
            or not required<=set(spec.get('sourceBindings',{})) or spec.get('mountainShader')!=MOUNTAIN_SHADER):
        raise RuntimeError('Exact signature-bound helper, candidate, native reader and shader inputs required')
    verify_bindings(root,spec)
    observation=spec.get('retainedMountainInspection')
    if not isinstance(observation,dict):raise RuntimeError('Fresh signature-bound native mountain inspection required')
    plan=plan_adapter(candidate,observation,destination,spec['mountainShader'])
    convention=mountain_render_normal_convention(Path(source_dir),candidate)
    operations=UnrealMountainOperations(unreal,root,candidate,destination,duplicate)
    if (checked_instance(operations.read_instance(SOURCE_INSTANCE),SOURCE_INSTANCE,SOURCE_PARENT,plan)!=observation['instanceReadback']
            or checked_graph(operations.read_graph(SOURCE_PARENT),plan)!=observation['parentGraphReadback']):
        raise RuntimeError('Actual native source differs from its signed fresh inspection')
    audit=create_adapter(plan,operations)
    audit.update(nativeRenderNormalConvention=convention,textureRepeatApplied=False,compileRequested=True,
        candidateSha256=digest(candidate),candidateCityRevision=candidate['city']['revision'],
        freshInspectionSha256=digest(observation),materialProfile=observation['parentGraphReadback']['materialProfile'])
    return operations._asset(plan['targetInstance']),audit
