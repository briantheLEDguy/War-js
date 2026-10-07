"""Portable tests use explicitly synthetic Unreal callbacks, not native evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'package.json').exists())
SOURCE=Path(__file__).resolve().parents[1]/'scripts/unreal'
sys.path[:0]=[str(SOURCE),str(ROOT/'scripts/unreal')]
import citadel_retained_mountain_bridge as bridge
import citadel_retained_mountain_adapter as adapter
import citadel_private_surface_study as study
from aegis_citadel_mountain_material import MOUNTAIN_SHADER

def vector():
    return dict(parameter_name='Base_Color_Tint',default_value=[1.,1.,1.,1.],group='Mountain',sort_priority=32,
        expression_guid='00000001000000020000000300000004',use_custom_primitive_data=False,primitive_data_index=0,
        channel_names={k:dict(display='',history='INVTEXT("")') for k in 'rgba'})

class Asset:
    def __init__(self,path,klass,properties=None):self.path=path;self.klass=klass;self.properties=properties or {};self.nodes=[]
    def get_path_name(self):return self.path
    def get_name(self):return self.path.rsplit(':',1)[-1].rsplit('.',1)[-1]
    def get_class(self):return types.SimpleNamespace(get_name=lambda:self.klass)
    def get_editor_property(self,name):return self.properties[name]
    def set_editor_property(self,name,value):self.properties[name]=value

def synthetic_fixture():
    root='/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa'
    level=root+'/Layers/RetainedCity_0';mesh=root+'/Meshes/SM_HallCarvedMountain.SM_HallCarvedMountain'
    state=dict(class_='fixture',components=[dict(name='StaticMeshComponent0',mesh=mesh,materials=[adapter.SOURCE_INSTANCE])])
    candidate=dict(revision='aaaaaaaaaaaa',signature='a'*64,siegeMap=root+'/SiegeCandidate',city=dict(revision='b'*64),
        sceneryLevels=[level],terrainCarves=[dict(actor='StaticMeshActor_306',component='StaticMeshComponent0',package=level,mesh=mesh,actualActorState=state)],
        sourceHashes={adapter.package(adapter.SOURCE_INSTANCE):'1'*64,adapter.package(adapter.SOURCE_PARENT):'2'*64,
            '/Game/Capitals/crownward/Textures/MountainBaseColor':'5'*64,'/Game/Capitals/crownward/Textures/MountainNormal':'6'*64},
        packageHashes={level:'3'*64,mesh.split('.')[0]:'4'*64})
    classes={'MaterialExpressionTextureSample_0':'MaterialExpressionTextureSample','MaterialExpressionTextureSample_1':'MaterialExpressionTextureSample',
        'MaterialExpressionMultiply_0':'MaterialExpressionMultiply','MaterialExpressionVectorParameter_0':'MaterialExpressionVectorParameter',
        'MaterialExpressionConstant_0':'MaterialExpressionConstant'}
    mask=dict.fromkeys(adapter.MASK_KEYS,0)
    roots={k:dict(node=None,output_index=0,**mask) for k in study.ROOT_PROPERTIES}
    roots['MP_BASE_COLOR']['node']='MaterialExpressionMultiply_0';roots['MP_NORMAL']['node']='MaterialExpressionTextureSample_1'
    roots['MP_ROUGHNESS']['node']='MaterialExpressionConstant_0'
    nodes={}
    for name,klass in classes.items():
        values=vector() if klass=='MaterialExpressionVectorParameter' else dict(r=.9) if klass=='MaterialExpressionConstant' else dict(const_a=0.,const_b=0.)
        if klass=='MaterialExpressionTextureSample':values=dict(texture='/Game/Capitals/crownward/Textures/'+('MountainBaseColor.MountainBaseColor' if name.endswith('_0') else 'MountainNormal.MountainNormal'),const_coordinate=0)
        nodes[name]=dict(klass=klass,values=values,pins={},outputs=[dict(output_name='',**mask)])
    graph=dict(nodes=nodes,roots=roots,materialProperties={k:False for k in study.MATERIAL_PROPERTIES},
        materialProfile=dict(name='retained_mountain_material_properties_v1',complete=True,keys=list(study.MATERIAL_PROPERTIES)))
    overrides={k:False for k in adapter.BASE_OVERRIDE_FLAGS};overrides['bOverride_UsageFlags']=0
    overrides.update({k:False if k in adapter.BASE_OVERRIDE_VALUES[:9] else 0 for k in adapter.BASE_OVERRIDE_VALUES})
    overrides.update(DisplacementScaling=dict(Magnitude=0.,Center=0.),DisplacementFadeRange=dict(StartSizePixels=64.,EndSizePixels=32.))
    local={k:[] for k in adapter.FAMILIES};local['vector']=[dict(parameterInfo=dict(name='Base_Color_Tint',association='GlobalParameter',index=-1),
        expressionGuid='00000001000000020000000300000004',value=adapter.TINT[:])]
    instance=dict(schemaVersion=1,readOnly=True,available=True,material=adapter.SOURCE_INSTANCE,materialClass='MaterialInstanceConstant',parent=adapter.SOURCE_PARENT,
        overrideInventoryComplete=True,settingsInventoryComplete=True,hasStaticPermutationResource=False,localOverrides=local,
        effectiveGlobalParameters=dict(scalar={},vector={'Base_Color_Tint':adapter.TINT[:]},texture={},static_switch={}),instanceProperties=dict(basePropertyOverrides=overrides))
    pins=lambda name,row:dict(schemaVersion=1,readOnly=True,available=True,expression=adapter.SOURCE_PARENT+':'+name,
        inputs=[],outputs=row['outputs'])
    inspection=dict(schemaVersion=1,readOnly=True,sourceBytesPreserved=True,inspectionKind='fresh_native_retained_mountain_v1',map=level,
        candidateMap=candidate['siegeMap'],candidateSha256=adapter.digest(candidate),candidateCityRevision=candidate['city']['revision'],
        sourcePackageHashes=bridge.signed_closure(candidate),actorReadback=dict(level=level,actor='StaticMeshActor_306',state=copy.deepcopy(state)),
        materials=[adapter.SOURCE_INSTANCE],instanceReadback=instance,parentGraphReadback=graph,
        chain=[{k:instance[k] for k in ('material','materialClass','parent','effectiveGlobalParameters')},
            dict(material=adapter.SOURCE_PARENT,materialClass='Material',nativeRoots=dict(schemaVersion=1,readOnly=True,available=True,material=adapter.SOURCE_PARENT,roots=roots),
                nodes=[dict(name=n,expressionClass=r['klass'],pins=pins(n,r)) for n,r in nodes.items()])])
    return candidate,inspection

class BridgeTests(unittest.TestCase):
    def setUp(self):self.candidate,self.inspection=synthetic_fixture()
    def plan(self):return adapter.plan_adapter(self.candidate,self.inspection,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)
    def test_fresh_source_level_city_candidate_and_closure_are_required(self):
        plan=self.plan();self.assertTrue(plan['currentInspectionSufficientForExecution'])
        for key,value in [('map',self.candidate['siegeMap']),('candidateCityRevision','0'*64),('candidateSha256','0'*64),
            ('inspectionKind','archival'),('sourcePackageHashes',{}),('actorReadback',{})]:
            changed=copy.deepcopy(self.inspection);changed[key]=value
            with self.assertRaises(ValueError):adapter.plan_adapter(self.candidate,changed,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)
    def test_six_property_profile_is_exact_and_does_not_claim_total_inventory(self):
        graph=self.inspection['parentGraphReadback'];adapter.checked_graph(graph,self.plan())
        for action in (lambda g:g.pop('materialProfile'),lambda g:g['materialProperties'].pop('blend_mode'),
            lambda g:g['materialProperties'].update(unknown_authoring_cache=False),lambda g:g['materialProfile'].update(complete=False)):
            changed=copy.deepcopy(graph);action(changed)
            with self.assertRaises(ValueError):adapter.checked_graph(changed,self.plan())
    def test_vector_native_profile_preserves_guid_and_text_history(self):
        value=vector();value['channel_names']['r']=dict(display='Tint',history='NSLOCTEXT("A","Red","Tint")')
        value['channel_names']['g']=dict(display='Tint',history='NSLOCTEXT("A","Green","Tint")')
        self.assertNotEqual(bridge.checked_vector_values(value)['channel_names']['r']['history'],value['channel_names']['g']['history'])
        node=Asset('/Game/Fixture.M:Vector','MaterialExpressionVectorParameter')
        native=dict(schemaVersion=1,readOnly=True,available=True,profile='vector_parameter_identity_v1',expression=node.path,expressionClass=node.klass,values=value)
        u=types.SimpleNamespace(WarImportLibrary=types.SimpleNamespace(describe_vector_parameter=lambda n:json.dumps(native)))
        self.assertEqual(bridge.vector_readback(u,node),value)
        for key,bad in [('available',False),('expression','/Wrong'),('profile','unknown')]:
            changed=copy.deepcopy(native);changed[key]=bad;u.WarImportLibrary.describe_vector_parameter=lambda n:json.dumps(changed)
            with self.assertRaises(RuntimeError):bridge.vector_readback(u,node)
    def test_vector_missing_guid_history_nonfinite_extra_or_wrong_types_fail(self):
        for key,bad in [('expression_guid','fixture-guid'),('expression_guid','0'*32),('default_value',[float('nan'),1,1,1]),
            ('sort_priority',True),('primitive_data_index',256),('use_custom_primitive_data',0),('channel_names',dict.fromkeys('rgba','struct text'))]:
            value=vector();value[key]=bad
            with self.assertRaises(RuntimeError):bridge.checked_vector_values(value)
        value=vector();value['unknown']=True
        with self.assertRaises(RuntimeError):bridge.checked_vector_values(value)
    def test_ops_native_reader_and_ownership_guards_use_actual_assets(self):
        actual=copy.deepcopy(self.inspection['instanceReadback']);assets={adapter.SOURCE_INSTANCE:Asset(adapter.SOURCE_INSTANCE,'MaterialInstanceConstant')}
        u=types.SimpleNamespace(load_asset=lambda p:assets.get(p),WarImportLibrary=types.SimpleNamespace(describe_material_instance=lambda asset:json.dumps(actual)),
            EditorAssetLibrary=types.SimpleNamespace(does_asset_exist=lambda p:False))
        ops=bridge.UnrealMountainOperations(u,ROOT,self.candidate,'/Game/WorldRebuild/AegisCitadel_abcdef123456',lambda a,b:None)
        self.assertEqual(ops.read_instance(adapter.SOURCE_INSTANCE),actual)
        for call in (lambda:ops._owned(adapter.SOURCE_INSTANCE),lambda:ops.set_parent(adapter.SOURCE_INSTANCE,adapter.SOURCE_PARENT),
            lambda:ops.duplicate(adapter.package(adapter.SOURCE_INSTANCE),'/Game/Unowned'),lambda:ops.exists('/Game/Unowned')):
            with self.assertRaises(RuntimeError):call()
    def test_actual_source_actor_world_namespace_duplicate_and_state_are_checked(self):
        level=self.candidate['terrainCarves'][0]['package'];calls=[]
        actor=types.SimpleNamespace(get_name=lambda:'StaticMeshActor_306',get_outer=lambda:Asset(level+'.PersistentLevel','Level'),state={'actual':'separate observation'})
        world=Asset(level+'.RetainedCity_0','World');actors=[actor]
        u=types.SimpleNamespace(LevelEditorSubsystem='levels',UnrealEditorSubsystem='editor',EditorActorSubsystem='actors',
            GameplayStatics=types.SimpleNamespace(flush_level_streaming=lambda w:calls.append('flush')))
        subs={'levels':types.SimpleNamespace(load_level=lambda p:calls.append(p) or True),
            'editor':types.SimpleNamespace(get_editor_world=lambda:world),'actors':types.SimpleNamespace(get_all_level_actors=lambda:actors)}
        u.get_editor_subsystem=lambda name:subs[name]
        ops=bridge.UnrealMountainOperations(u,ROOT,self.candidate)
        with patch.dict(sys.modules,world_actor_state=types.SimpleNamespace(snapshot=lambda a:copy.deepcopy(a.state))):
            self.assertEqual(ops.read_actor_binding(dict(level=level,actor='StaticMeshActor_306')),actor.state)
            self.assertNotEqual(actor.state,self.candidate['terrainCarves'][0]['actualActorState'])
            actors.append(actor)
            with self.assertRaises(RuntimeError):ops.read_actor_binding(dict(level=level,actor='StaticMeshActor_306'))
            actors.pop();world.path='/Game/Wrong.Wrong'
            with self.assertRaises(RuntimeError):ops.read_actor_binding(dict(level=level,actor='StaticMeshActor_306'))
        self.assertIn('flush',calls)
    def test_source_closure_conflicts_fail(self):
        changed=copy.deepcopy(self.candidate);changed['packageHashes'][adapter.package(adapter.SOURCE_INSTANCE)]='f'*64
        with self.assertRaises(RuntimeError):bridge.signed_closure(changed)
    def test_plan_rejects_missing_native_profiles_before_execution_is_claimed(self):
        for key in ('instanceReadback','parentGraphReadback'):
            changed=copy.deepcopy(self.inspection);changed.pop(key)
            with self.assertRaises(ValueError):
                adapter.plan_adapter(self.candidate,changed,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)
    def test_fresh_inspector_rejects_package_drift_before_reading_assets(self):
        changed=bridge.signed_closure(self.candidate);changed[adapter.package(adapter.SOURCE_PARENT)]='0'*64
        with patch.object(bridge,'package_hashes',return_value=changed):
            with self.assertRaisesRegex(RuntimeError,'package bytes changed'):
                bridge.inspect_current_mountain(None,ROOT,self.candidate)
    def test_save_failure_is_reported_without_saving_sources(self):
        destination='/Game/WorldRebuild/AegisCitadel_abcdef123456'
        parent=destination+'/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain'
        instance=destination+'/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain'
        assets={p:Asset(p,k) for p,k in ((parent,'Material'),(instance,'MaterialInstanceConstant'))};saved=[]
        u=types.SimpleNamespace(load_asset=lambda p:assets.get(p),
            MaterialEditingLibrary=types.SimpleNamespace(recompile_material=lambda base:[],update_material_instance=lambda mi:None),
            EditorAssetLibrary=types.SimpleNamespace(save_loaded_asset=lambda obj,**unused:saved.append(obj.path) or False))
        operations=bridge.UnrealMountainOperations(u,ROOT,self.candidate,destination)
        with self.assertRaisesRegex(RuntimeError,'Cannot save'):
            operations.compile_and_save(parent,instance)
        self.assertEqual(saved,[parent])
    def test_actual_callback_bridge_copies_retargets_adds_and_saves_only_owned_pair(self):
        candidate,inspection=synthetic_fixture();source_graph=inspection['parentGraphReadback'];events=[]
        parent=Asset(adapter.SOURCE_PARENT,'Material',copy.deepcopy(source_graph['materialProperties']));parent.roots=copy.deepcopy(source_graph['roots'])
        instance=Asset(adapter.SOURCE_INSTANCE,'MaterialInstanceConstant');instance.descriptor=copy.deepcopy(inspection['instanceReadback'])
        assets={parent.path:parent,instance.path:instance};mask=dict.fromkeys(adapter.MASK_KEYS,0)
        for name,row in source_graph['nodes'].items():
            props={key:0 for key in study.NODE_VALUES.get(row['klass'],())};props.update(row['values'])
            if row['klass']=='MaterialExpressionTextureSample':props['texture']=Asset(props['texture'],'Texture')
            node=Asset(parent.path+':'+name,row['klass'],props);node.outputs=copy.deepcopy(row['outputs']);parent.nodes.append(node)
        def pins(node):
            inputs=[]
            if node.klass=='MaterialExpressionCustom':
                inputs=[dict(inputIndex=i,input_name=x.get_editor_property('input_name'),node=x.properties['source'].get_name(),output_index=0,
                    **dict(zip(adapter.MASK_KEYS,(1,1,1,1,0))) if x.properties['source'].klass=='MaterialExpressionWorldPosition' else mask)
                    for i,x in enumerate(node.properties['inputs'])]
            return dict(schemaVersion=1,readOnly=True,available=True,expression=node.path,inputs=inputs,outputs=node.outputs)
        def roots(mat):return dict(schemaVersion=1,readOnly=True,available=True,material=mat.path,roots=mat.roots)
        def vector_descriptor(node):return dict(schemaVersion=1,readOnly=True,available=True,profile='vector_parameter_identity_v1',expression=node.path,expressionClass=node.klass,values=node.properties)
        def create(mat,klass):
            name=klass+'_'+str(len(mat.nodes));props=dict(world_position_shader_offset=0) if klass=='MaterialExpressionWorldPosition' else {}
            node=Asset(mat.path+':'+name,klass,props)
            node.outputs=([dict(output_name='XYZ',**dict(zip(adapter.MASK_KEYS,(1,1,1,1,0)))),
                dict(output_name='XY',**dict(zip(adapter.MASK_KEYS,(1,1,1,0,0)))),
                dict(output_name='Z',**dict(zip(adapter.MASK_KEYS,(1,0,0,1,0))))]
                if klass=='MaterialExpressionWorldPosition' else [dict(output_name='',**mask)])
            mat.nodes.append(node);return node
        def connect(source,output,shader,name):
            next(x for x in shader.properties['inputs'] if x.properties['input_name']==name).properties['source']=source
            return True
        def connect_root(shader,output,prop):
            mat=assets[shader.path.split(':')[0]];mat.roots[prop]=dict(node=shader.get_name(),output_index=0,**mask);return True
        def retarget(mi,base):events.append(('parent',mi.path,base.path));mi.descriptor['parent']=base.path
        lib=types.SimpleNamespace(get_material_expressions=lambda mat:mat.nodes,
            get_material_property_input_node=lambda mat,p:next(n for n in mat.nodes if n.get_name()==mat.roots[p]['node']),
            create_material_expression=create,connect_material_expressions=connect,connect_material_property=connect_root,
            set_material_instance_parent=retarget,recompile_material=lambda mat:events.append(('compile',mat.path)),
            update_material_instance=lambda mi:events.append(('update',mi.path)))
        u=types.SimpleNamespace(load_asset=lambda p:assets.get(p),MaterialEditingLibrary=lib,
            WarImportLibrary=types.SimpleNamespace(describe_material_instance=lambda mi:json.dumps(mi.descriptor),
                describe_material_roots=lambda mat:json.dumps(roots(mat)),describe_material_expression_pins=lambda n:json.dumps(pins(n)),
                describe_vector_parameter=lambda n:json.dumps(vector_descriptor(n))),
            MaterialProperty=types.SimpleNamespace(MP_BASE_COLOR='MP_BASE_COLOR'),CustomInput=lambda:Asset('input','CustomInput'),
            CustomMaterialOutputType=types.SimpleNamespace(CMOT_FLOAT3='CMOT_FLOAT3'),
            MaterialExpressionWorldPosition='MaterialExpressionWorldPosition',MaterialExpressionVertexNormalWS='MaterialExpressionVertexNormalWS',
            MaterialExpressionCustom='MaterialExpressionCustom')
        u.EditorAssetLibrary=types.SimpleNamespace(does_asset_exist=lambda p:any(adapter.package(n)==p for n in assets),
            save_loaded_asset=lambda obj,**kwargs:events.append(('save',obj.path)) or True)
        def duplicate(source,target):
            original=assets[source+'.'+source.rsplit('/',1)[-1]];clone=copy.deepcopy(original);clone.path=target+'.'+target.rsplit('/',1)[-1]
            if clone.klass=='Material':
                for n in clone.nodes:n.path=clone.path+':'+n.get_name()
            else:clone.descriptor['material']=clone.path
            assets[clone.path]=clone;events.append(('duplicate',source,target))
        measured=candidate['terrainCarves'][0]
        # Only package IO/actor observation and the large saved-face scan are mocked; real bridge callbacks edit the synthetic Unreal objects.
        with patch.object(bridge,'package_hashes',return_value=bridge.signed_closure(candidate)),\
             patch.object(bridge.UnrealMountainOperations,'read_actor_binding',return_value=copy.deepcopy(measured['actualActorState'])) as actor_read,\
             patch.object(study,'verify_bindings') as source_verify,\
             patch('aegis_citadel_mountain_material.mountain_render_normal_convention',return_value={'source':'actual_saved_native_rendered_faces','slopeMaskNormalZSign':-1}) as convention:
            # Inspector's observed world is supplied by the mocked real-actor boundary, explicitly synthetic in this test.
            original_read=bridge.UnrealMountainOperations.read_actor_binding
            def observed(ops,binding):ops.observed_world=binding['level'];return original_read(binding)
            with patch.object(bridge.UnrealMountainOperations,'read_actor_binding',observed):
                fresh=bridge.inspect_current_mountain(u,ROOT,candidate)
            spec=dict(sourceRevision=candidate['revision'],sourcePackageHashes=bridge.signed_closure(candidate),
                mountainShader=MOUNTAIN_SHADER,retainedMountainInspection=fresh,sourceBindings={name:'a'*64 for name in (
                    'scripts/unreal/citadel_retained_mountain_bridge.py','scripts/unreal/citadel_retained_mountain_adapter.py',
                    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarMaterialInstanceReadback.cpp',
                    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarVectorParameterReadback.cpp')})
            changed=copy.deepcopy(spec)
            changed['retainedMountainInspection']['parentGraphReadback']['nodes']['MaterialExpressionVectorParameter_0']['values']['group']='drift'
            with self.assertRaisesRegex(RuntimeError,'signed fresh inspection'):
                bridge.create_mountain(u,'/Game/WorldRebuild/AegisCitadel_abcdef123456',ROOT/'artifacts/unreal/aegis-citadel/aaaaaaaaaaaa',candidate,changed,duplicate)
            self.assertFalse(events)
            material,audit=bridge.create_mountain(u,'/Game/WorldRebuild/AegisCitadel_abcdef123456',ROOT/'artifacts/unreal/aegis-citadel/aaaaaaaaaaaa',candidate,spec,duplicate)
        self.assertEqual(material.path,audit['material']);self.assertEqual(audit['sourcePbrGraph'],adapter.SOURCE_PARENT)
        self.assertEqual(audit['afterInstance']['localOverrides'],inspection['instanceReadback']['localOverrides'])
        self.assertEqual([event[1] for event in events if event[0]=='save'],[audit['graphMaterial'],audit['material']])
        self.assertEqual(instance.descriptor,inspection['instanceReadback']);self.assertEqual(parent.roots,source_graph['roots'])
        self.assertFalse(audit['coldProcessVerified']);self.assertFalse(audit['visualApproved'])
        self.assertEqual(source_verify.call_count,2);self.assertEqual(convention.call_count,2)

if __name__=='__main__':unittest.main()
