"""Positive/negative portable contracts; synthetic native callbacks only."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'package.json').is_file())
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts/unreal'),str(ROOT/'scripts/unreal')]
import citadel_retained_mountain_adapter as adapter
from aegis_citadel_mountain_material import MOUNTAIN_SHADER

INSPECTION=json.loads((ROOT/'artifacts/unreal/citadel-reference/oct7-retained-mountain-chain-inspection.json').read_bytes())
CANDIDATE=json.loads((ROOT/'artifacts/unreal/aegis-citadel/423a3d57fd65/candidate.json').read_bytes())
# Synthetic freshness metadata exercises the portable contract; no native inspection is claimed here.
ARCHIVAL_INSPECTION=copy.deepcopy(INSPECTION)
INSPECTION.update(inspectionKind='fresh_native_retained_mountain_v1',
    map=CANDIDATE['terrainCarves'][0]['package'],candidateMap=CANDIDATE['siegeMap'],
    candidateSha256=adapter.digest(CANDIDATE),candidateCityRevision=CANDIDATE['city']['revision'],
    sourcePackageHashes={**CANDIDATE['sourceHashes'],**CANDIDATE['packageHashes']},
    actorReadback=dict(level=CANDIDATE['terrainCarves'][0]['package'],actor='StaticMeshActor_306',state=CANDIDATE['terrainCarves'][0]['actualActorState']))


def original_graph(plan):
    nodes={}
    for row in plan['sourceGraphObservation']['nodes']:
        pins=row['pins']
        values={'value':1}
        if row['name']=='MaterialExpressionTextureSample_0':
            values=dict(texture='/Game/Capitals/crownward/Textures/MountainBaseColor.MountainBaseColor',const_coordinate=0)
        elif row['name']=='MaterialExpressionTextureSample_1':
            values=dict(texture='/Game/Capitals/crownward/Textures/MountainNormal.MountainNormal',const_coordinate=0)
        elif row['expressionClass']=='MaterialExpressionVectorParameter':
            values=dict(parameter_name='Base_Color_Tint',default_value=[1,1,1,1],group='None',sort_priority=32,
                expression_guid='00000001000000020000000300000004',use_custom_primitive_data=False,primitive_data_index=0,
                channel_names={k:dict(display='',history='INVTEXT("")') for k in 'rgba'})
        nodes[row['name']]=dict(klass=row['expressionClass'],values=values,
            pins={str(p['inputIndex']):{k:v for k,v in p.items() if k!='inputIndex'} for p in pins['inputs']},
            outputs=copy.deepcopy(pins['outputs']))
    return dict(nodes=nodes,roots=copy.deepcopy(plan['sourceGraphObservation']['nativeRoots']['roots']),
        materialProfile=dict(name='retained_mountain_material_properties_v1',complete=True,
            keys=list(__import__('citadel_private_surface_study').MATERIAL_PROPERTIES)),
        materialProperties={k:False for k in __import__('citadel_private_surface_study').MATERIAL_PROPERTIES})


def original_instance(plan):
    local={k:[] for k in adapter.FAMILIES}
    local['vector']=[dict(parameterInfo=dict(name='Base_Color_Tint',association='GlobalParameter',index=-1),
        expressionGuid='fixture-guid',value=adapter.TINT[:])]
    overrides={k:False for k in adapter.BASE_OVERRIDE_FLAGS}
    overrides.update({k:0 for k in adapter.BASE_OVERRIDE_VALUES});overrides['bOverride_UsageFlags']=0
    overrides.update({k:False for k in adapter.BASE_OVERRIDE_VALUES[:9]})
    overrides['DisplacementScaling']={'Magnitude':0,'Center':0}
    overrides['DisplacementFadeRange']={'StartSizePixels':64,'EndSizePixels':32}
    return dict(schemaVersion=1,readOnly=True,available=True,material=plan['sourceInstance'],
        materialClass='MaterialInstanceConstant',parent=plan['sourceParent'],overrideInventoryComplete=True,
        settingsInventoryComplete=True,localOverrides=local,effectiveGlobalParameters=plan['effectiveGlobalParameters'],
        instanceProperties=dict(basePropertyOverrides=overrides,physicalMaterial=None),
        hasStaticPermutationResource=False)


# Explicit synthetic complete profiles for plan validation; archival input stays unchanged.
FIXTURE_PLAN=dict(sourceInstance=adapter.SOURCE_INSTANCE,sourceParent=adapter.SOURCE_PARENT,
    sourceGraphObservation=INSPECTION['chain'][1],effectiveGlobalParameters=INSPECTION['chain'][0]['effectiveGlobalParameters'])
INSPECTION.update(instanceReadback=original_instance(FIXTURE_PLAN),parentGraphReadback=original_graph(FIXTURE_PLAN))


class FakeNativeOperations:
    def __init__(self,plan):
        self.plan=plan;self.graphs={plan['sourceParent']:original_graph(plan)}
        self.instances={plan['sourceInstance']:original_instance(plan)}
        self.hashes=copy.deepcopy(plan['sourcePackageHashes']);self.created=[]
        self.corruption=None
    def read_actor_binding(self,binding):return copy.deepcopy(binding['actorState'])
    def read_instance(self,path):return copy.deepcopy(self.instances[path])
    def read_graph(self,path):return copy.deepcopy(self.graphs[path])
    def source_hashes(self):return copy.deepcopy(self.hashes)
    def exists(self,path):return path in self.created
    def duplicate(self,source,target):
        source_object=source+'.'+source.rsplit('/',1)[-1];target_object=target+'.'+target.rsplit('/',1)[-1]
        self.created.append(target)
        if source_object in self.graphs:self.graphs[target_object]=self.read_graph(source_object)
        else:
            self.instances[target_object]=self.read_instance(source_object)
            self.instances[target_object]['material']=target_object
    def set_parent(self,material,parent):self.instances[material]['parent']=parent
    def add_alpine_base_color(self,path,shader):
        graph=self.read_graph(path)
        def pin(name,node):return dict(input_name=name,node=node,output_index=0,
            **dict(zip(adapter.MASK_KEYS,(1,1,1,1,0) if name=='P' else (0,0,0,0,0))))
        additions={'AlpinePosition':dict(klass='MaterialExpressionWorldPosition',values={},pins={},outputs=[]),
                   'AlpineNormal':dict(klass='MaterialExpressionVertexNormalWS',values={},pins={},outputs=[]),
                   'AlpineColor':dict(klass='MaterialExpressionCustom',values=dict(code=shader,output_type='CMOT_FLOAT3'),
                       pins={'0':pin('P','AlpinePosition'),'1':pin('N','AlpineNormal'),
                             '2':dict(input_name='Rock',**graph['roots']['MP_BASE_COLOR'])},outputs=[])}
        graph['nodes'].update(additions)
        graph['roots']['MP_BASE_COLOR']=dict(node='AlpineColor',output_index=0,**dict.fromkeys(adapter.MASK_KEYS,0))
        self.graphs[path]=graph
        return dict(graph=graph,additions=additions,shader='AlpineColor')
    def compile_and_save(self,base,instance):
        if self.corruption:self.corruption(self,base,instance)


class MountainAdapterTests(unittest.TestCase):
    def setUp(self):
        self.plan=adapter.plan_adapter(CANDIDATE,INSPECTION,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)
        self.operations=FakeNativeOperations(self.plan)

    def test_synthetic_complete_profile_selects_measured_chain_and_rejects_archival_input(self):
        self.assertEqual(self.plan['sourceInstance'],adapter.SOURCE_INSTANCE)
        self.assertEqual(self.plan['sourceParent'],adapter.SOURCE_PARENT)
        self.assertTrue(self.plan['currentInspectionSufficientForExecution'])
        with self.assertRaises(ValueError):
            adapter.plan_adapter(CANDIDATE,ARCHIVAL_INSPECTION,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)
        self.assertTrue(self.plan['completeNativeInstanceReadbackRequired'])
        self.assertNotIn('MountainGranite',self.plan['sourceParent'])

    def test_private_copy_retains_tint_overrides_original_graph_and_false_approval_flags(self):
        audit=adapter.create_adapter(self.plan,self.operations)
        self.assertEqual(audit['material'],self.plan['targetInstance'])
        self.assertEqual(audit['graphMaterial'],self.plan['targetBase'])
        self.assertEqual(audit['expectedResourceOwner'],self.plan['targetBase'])
        self.assertEqual(audit['beforeInstance']['localOverrides'],audit['afterInstance']['localOverrides'])
        for key in audit['beforeGraph']['roots']:
            if key!='MP_BASE_COLOR':self.assertEqual(audit['beforeGraph']['roots'][key],audit['afterGraph']['roots'][key])
        self.assertEqual(audit['beforeGraph']['nodes'],{k:audit['afterGraph']['nodes'][k] for k in audit['beforeGraph']['nodes']})
        self.assertTrue(all(audit[k] is False for k in ('coldProcessVerified','rendererStateVerified',
            'submittedMeshBatchVerified','screenshotPixelBindingVerified','visualApproved','releaseAcceptance')))

    def test_wrong_candidate_binding_is_rejected_even_if_wrong_material_is_in_closure(self):
        candidate=copy.deepcopy(CANDIDATE)
        candidate['terrainCarves'][0]['actualActorState']['components'][0]['materials']=['/Game/Capitals/crownward/MountainGranite.MountainGranite']
        with self.assertRaisesRegex(ValueError,'candidate actor|Inspection differs'):adapter.plan_adapter(candidate,INSPECTION,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)

    def test_cycles_extra_chain_unknown_parameter_and_missing_parent_closure_fail(self):
        for change in ('cycle','extra','parameter','closure'):
            inspection=copy.deepcopy(INSPECTION);candidate=copy.deepcopy(CANDIDATE)
            if change=='cycle':inspection['chain'][0]['parent']=adapter.SOURCE_INSTANCE
            if change=='extra':inspection['chain'].append(copy.deepcopy(inspection['chain'][1]))
            if change=='parameter':inspection['chain'][0]['effectiveGlobalParameters']['scalar']['Unknown']=1
            if change=='closure':candidate['sourceHashes'].pop(adapter.package(adapter.SOURCE_PARENT),None)
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.plan_adapter(candidate,inspection,'/Game/WorldRebuild/AegisCitadel_abcdef123456',MOUNTAIN_SHADER)

    def test_incomplete_overrides_or_static_permutation_cannot_be_assumed_empty(self):
        for key,value in [('overrideInventoryComplete',False),('settingsInventoryComplete',False),('hasStaticPermutationResource',True)]:
            operations=FakeNativeOperations(self.plan);operations.instances[self.plan['sourceInstance']][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Complete native'):adapter.create_adapter(self.plan,operations)
            self.assertEqual(operations.created,[])

    def test_unknown_override_family_parameter_or_association_is_rejected(self):
        for change in ('family','parameter','association'):
            state=original_instance(self.plan)
            if change=='family':state['localOverrides']['unknown']=[]
            if change=='parameter':state['localOverrides']['scalar']=[dict(name='Unknown',value=1)]
            if change=='association':state['localOverrides']['vector'][0]['parameterInfo']['association']='LayerParameter'
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.checked_instance(state,self.plan['sourceInstance'],self.plan['sourceParent'],self.plan)

    def test_material_settings_texture_dependency_and_original_pins_must_be_complete(self):
        for change in ('settings','texture','pins','parameter_metadata'):
            graph=original_graph(self.plan)
            if change=='settings':graph['materialProfile']['complete']=False
            if change=='texture':graph['nodes']['MaterialExpressionTextureSample_0']['values']['texture']='/Game/Unknown.Texture'
            if change=='pins':graph['nodes']['MaterialExpressionMultiply_0']['pins']['0']['output_index']=1
            if change=='parameter_metadata':graph['nodes']['MaterialExpressionVectorParameter_0']['values'].pop('group')
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.checked_graph(graph,self.plan)

    def test_unknown_actor_and_interrupted_private_destination_fail_before_copy(self):
        self.operations.read_actor_binding=lambda binding:{'changed':True}
        with self.assertRaisesRegex(ValueError,'actor/component'):adapter.create_adapter(self.plan,self.operations)
        self.assertEqual(self.operations.created,[])
        operations=FakeNativeOperations(self.plan);operations.created=[adapter.package(self.plan['targetInstance'])]
        with self.assertRaisesRegex(ValueError,'existing/interrupted'):adapter.create_adapter(self.plan,operations)

    def test_save_reload_tint_uv_normal_and_property_drift_are_rejected(self):
        for change in ('tint','uv','normal','property'):
            operations=FakeNativeOperations(self.plan)
            def corrupt(ops,base,instance):
                if change=='tint':ops.instances[instance]['localOverrides']['vector'][0]['value']=[1,1,1,1]
                if change=='uv':ops.graphs[base]['nodes']['MaterialExpressionTextureSample_0']['values']['const_coordinate']=1
                if change=='normal':ops.graphs[base]['roots']['MP_NORMAL']['node']=None
                if change=='property':ops.instances[instance]['instanceProperties']['basePropertyOverrides']['bOverride_BlendMode']=True
            operations.corruption=corrupt
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.create_adapter(self.plan,operations)

    def test_source_package_or_original_parent_mutation_is_rejected(self):
        for change in ('bytes','graph'):
            operations=FakeNativeOperations(self.plan)
            def corrupt(ops,base,instance):
                if change=='bytes':ops.hashes[adapter.package(self.plan['sourceParent'])]='0'*64
                else:ops.graphs[self.plan['sourceParent']]['materialProperties']['two_sided']=True
            operations.corruption=corrupt
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'source'):adapter.create_adapter(self.plan,operations)

    def test_alpine_shader_must_consume_original_tinted_output_and_only_change_basecolor(self):
        graph=original_graph(self.plan)
        result=self.operations.add_alpine_base_color(self.plan['sourceParent'],self.plan['shader'])
        adapter.checked_graph_change(graph,result['graph'],result['additions'],result['shader'],self.plan)
        for change in ('untinted','type','normal','settings','position_mask','normal_mask'):
            bad=copy.deepcopy(result)
            if change=='untinted':
                bad['additions']['AlpineColor']['pins']['2']['node']='MaterialExpressionTextureSample_0'
                bad['graph']['nodes']['AlpineColor']['pins']['2']['node']='MaterialExpressionTextureSample_0'
            if change=='type':bad['additions']['AlpineColor']['values']['output_type']='CMOT_FLOAT1'
            if change=='normal':bad['graph']['roots']['MP_NORMAL']['node']=None
            if change=='settings':bad['graph']['materialProperties']['two_sided']=True
            if change=='position_mask':bad['additions']['AlpineColor']['pins']['0']['mask_b']=0
            if change=='normal_mask':bad['additions']['AlpineColor']['pins']['1']['mask']=1
            with self.subTest(change=change),self.assertRaises(ValueError):
                adapter.checked_graph_change(graph,bad['graph'],bad['additions'],bad['shader'],self.plan)

    def test_readiness_accepts_exact_private_mi_with_base_resource_and_rejects_missing_or_fallback(self):
        component='/Game/WorldRebuild/AegisCitadel_abcdef123456/Layers/Study_0.Study_0:PersistentLevel.StaticMeshActor_306.StaticMeshComponent0'
        binding=dict(component=component,materialSlot=0,material=self.plan['targetInstance'],baseMaterial=self.plan['targetBase'],
            proxyInterface=self.plan['targetInstance'],mesh=self.plan['candidateBinding']['mesh'],hasStaticPermutationResource=False,
            registered=True,visible=True,renderBuffersAvailable=True,rendererAvailable=True,hiddenInGame=False,actorHidden=False,
            submittedMeshBatchVerified=False,screenshotPixelBindingVerified=False,visualApproved=False,
            renderSections=[dict(lod=0,triangles=100)],renderMaterial=dict(available=True,usedFallback=False,
                effectiveInterface=self.plan['targetBase'],materialDomain=0,shaderMapPresent=True,shaderMapValidForRendering=True))
        self.assertTrue(adapter.checked_readiness(binding,self.plan,component)['effectiveProxyReady'])
        with self.assertRaises(ValueError):adapter.checked_readiness(None,self.plan,component)
        for change in ('fallback','wrong_owner','wrong_proxy','zero_sections','static','wrong_component'):
            bad=copy.deepcopy(binding)
            if change=='fallback':bad['renderMaterial']['usedFallback']=True
            if change=='wrong_owner':bad['renderMaterial']['effectiveInterface']=self.plan['targetInstance']
            if change=='wrong_proxy':bad['proxyInterface']=self.plan['targetBase']
            if change=='zero_sections':bad['renderSections']=[]
            if change=='static':bad['hasStaticPermutationResource']=True
            if change=='wrong_component':bad['component']+='Unexpected'
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.checked_readiness(bad,self.plan,component)

    def test_base_override_struct_strings_missing_flags_and_truncated_usage_masks_fail(self):
        for change in ('string','missing_flag','usage'):
            state=original_instance(self.plan)
            if change=='string':state['instanceProperties']['basePropertyOverrides']="<Struct MaterialInstanceBasePropertyOverrides (0x1234) {}>"
            if change=='missing_flag':state['instanceProperties']['basePropertyOverrides'].pop('bOverride_DisplacementScaling')
            if change=='usage':state['instanceProperties']['basePropertyOverrides']['bOverride_UsageFlags']=True
            with self.subTest(change=change),self.assertRaises(ValueError):adapter.checked_instance(state,self.plan['sourceInstance'],self.plan['sourceParent'],self.plan)


if __name__=='__main__':unittest.main()
