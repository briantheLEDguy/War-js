"""Bounded MI/parent copy contract; callers supply verified native readback APIs.

This module does not import Unreal. Inspection alone cannot authorize execution:
complete instance/property readbacks and actual graph observations are required.
"""
import copy
import hashlib
import json
import re

SOURCE_INSTANCE='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/MI_Mountain_365df6bd.MI_Mountain_365df6bd'
SOURCE_PARENT='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/M_Mountain.M_Mountain'
TINT=[.3700000047683716,.4000000059604645,.4399999976158142,1.]
FAMILIES=('scalar','vector','doubleVector','texture','textureCollection','parameterCollection',
    'runtimeVirtualTexture','sparseVolumeTexture','font','staticSwitch','staticComponentMask','terrainLayerWeight','materialLayers')
MASK_KEYS=('mask','mask_r','mask_g','mask_b','mask_a')
BASE_OVERRIDE_FLAGS=('bOverride_OpacityMaskClipValue','bOverride_BlendMode','bOverride_ShadingModel',
    'bOverride_DitheredLODTransition','bOverride_CastDynamicShadowAsMasked','bOverride_TwoSided',
    'bOverride_bIsThinSurface','bOverride_OutputTranslucentVelocity','bOverride_bHasPixelAnimation',
    'bOverride_bEnableTessellation','bOverride_DisplacementScaling','bOverride_bEnableDisplacementFade',
    'bOverride_DisplacementFadeRange','bOverride_MaxWorldPositionOffsetDisplacement',
    'bOverride_CompatibleWithLumenCardSharing','bOverride_UsageFlags')
BASE_OVERRIDE_VALUES=('TwoSided','bIsThinSurface','DitheredLODTransition','bCastDynamicShadowAsMasked',
    'bOutputTranslucentVelocity','bHasPixelAnimation','bEnableTessellation','bEnableDisplacementFade',
    'bCompatibleWithLumenCardSharing','BlendMode','ShadingModel','OpacityMaskClipValue',
    'DisplacementScaling','DisplacementFadeRange','MaxWorldPositionOffsetDisplacement','UsageFlags')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def package(object_path):
    if not isinstance(object_path,str) or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+',object_path):
        raise ValueError('Exact material object path required')
    path,name=object_path.split('.')
    if path.rsplit('/',1)[-1]!=name: raise ValueError('Material package/object identity differs')
    return path


def plan_adapter(candidate,inspection,destination,shader):
    if not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}',destination):
        raise ValueError('Fresh private destination required')
    if (inspection.get('schemaVersion')!=1 or inspection.get('readOnly') is not True
            or inspection.get('sourceBytesPreserved') is not True
            or inspection.get('candidateMap')!=candidate.get('siegeMap')
            or inspection.get('inspectionKind')!='fresh_native_retained_mountain_v1'
            or inspection.get('candidateSha256')!=digest(candidate)
            or inspection.get('candidateCityRevision')!=candidate.get('city',{}).get('revision')
            or inspection.get('materials')!=[SOURCE_INSTANCE]):
        raise ValueError('Inspection differs from the exact candidate/material binding')
    chain=inspection.get('chain')
    if (not isinstance(chain,list) or len(chain)!=2 or chain[0].get('material')!=SOURCE_INSTANCE
            or chain[0].get('materialClass')!='MaterialInstanceConstant' or chain[0].get('parent')!=SOURCE_PARENT
            or chain[1].get('material')!=SOURCE_PARENT or chain[1].get('materialClass')!='Material'):
        raise ValueError('Bounded measured MI/parent chain required')
    effective=chain[0].get('effectiveGlobalParameters')
    if effective!=dict(scalar={},vector={'Base_Color_Tint':TINT},texture={},static_switch={}):
        raise ValueError('Unknown or changed effective mountain parameter')
    from citadel_private_surface_study import ROOT_PROPERTIES
    roots=chain[1].get('nativeRoots',{})
    nodes=chain[1].get('nodes')
    if (roots.get('schemaVersion')!=1 or roots.get('readOnly') is not True or roots.get('available') is not True
            or roots.get('material')!=SOURCE_PARENT or set(roots.get('roots',{}))!=set(ROOT_PROPERTIES)
            or not isinstance(nodes,list) or len(nodes)!=5 or len({n.get('name') for n in nodes})!=5):
        raise ValueError('Complete bounded native parent graph observation required')
    carves=candidate.get('terrainCarves',[])
    if len(carves)!=1: raise ValueError('Exactly one measured retained mountain actor required')
    measured=carves[0]; state=measured.get('actualActorState',{})
    if (inspection.get('map')!=measured.get('package')
            or inspection.get('actorReadback')!=dict(level=measured.get('package'),actor=measured.get('actor'),state=state)):
        raise ValueError('Fresh exact source-level actor inspection required')
    components=state.get('components',[])
    if (len(components)!=1 or components[0].get('name')!=measured.get('component')
            or components[0].get('mesh')!=measured.get('mesh') or components[0].get('materials')!=[SOURCE_INSTANCE]
            or measured.get('actor')!='StaticMeshActor_306' or measured.get('package') not in candidate.get('sceneryLevels',[])):
        raise ValueError('Exact candidate actor/component/slot/mesh material match required')
    sources=candidate.get('sourceHashes',{}); packages=candidate.get('packageHashes',{})
    if any(sources[p]!=packages[p] for p in set(sources)&set(packages)):
        raise ValueError('Conflicting candidate source package bindings')
    closure={**sources,**packages}
    required=(package(SOURCE_INSTANCE),package(SOURCE_PARENT),measured['mesh'].split('.')[0],measured['package'])
    if any(not re.fullmatch('[a-f0-9]{64}',str(closure.get(p))) for p in required):
        raise ValueError('Missing signed MI/parent/actor/mesh package closure')
    if inspection.get('sourcePackageHashes')!=closure:
        raise ValueError('Fresh inspection differs from the signed package closure')
    if not isinstance(shader,str) or not shader.strip(): raise ValueError('Exact alpine shader source required')
    target_base=destination+'/Materials/M_PrivateSurface_mountain'
    target_instance=destination+'/Materials/MI_PrivateSurface_mountain'
    plan=dict(version=1,sourceInstance=SOURCE_INSTANCE,sourceParent=SOURCE_PARENT,
        targetInstance=target_instance+'.'+target_instance.rsplit('/',1)[-1],
        targetBase=target_base+'.'+target_base.rsplit('/',1)[-1],sourcePackageHashes=closure,
        candidateBinding=dict(actor=measured['actor'],level=measured['package'],component=measured['component'],
            mesh=measured['mesh'],slot=0,actorState=copy.deepcopy(state)),
        sourceGraphObservation=copy.deepcopy(chain[1]),effectiveGlobalParameters=copy.deepcopy(effective),
        candidateSha256=digest(candidate),inspectionSha256=digest(inspection),shader=shader,
        shaderSha256=hashlib.sha256(shader.encode()).hexdigest(),
        currentInspectionSufficientForExecution=True,completeNativeInstanceReadbackRequired=True,
        nativeReadinessExtensionRequired=True,geometryChanged=False,collisionChanged=False,
        lightingChanged=False,uvsChanged=False,visualApproved=False,releaseAcceptance=False)
    checked_instance(inspection.get('instanceReadback'),SOURCE_INSTANCE,SOURCE_PARENT,plan)
    if not isinstance(inspection.get('parentGraphReadback'),dict):
        raise ValueError('Fresh complete native parent graph profile required')
    checked_graph(inspection['parentGraphReadback'],plan)
    return plan


def checked_instance(state,material,parent,plan):
    required={'schemaVersion','readOnly','available','material','materialClass','parent',
        'overrideInventoryComplete','settingsInventoryComplete','localOverrides','effectiveGlobalParameters',
        'instanceProperties','hasStaticPermutationResource'}
    if (not isinstance(state,dict) or set(state)!=required or state['schemaVersion']!=1
            or state['readOnly'] is not True or state['available'] is not True or state['material']!=material
            or state['materialClass']!='MaterialInstanceConstant' or state['parent']!=parent
            or state['overrideInventoryComplete'] is not True or state['settingsInventoryComplete'] is not True
            or state['hasStaticPermutationResource'] is not False or not isinstance(state['instanceProperties'],dict)
            or not state['instanceProperties']):
        raise ValueError('Complete native MI overrides/settings and non-static resource state required')
    local=state['localOverrides']
    if not isinstance(local,dict) or set(local)!=set(FAMILIES) or any(not isinstance(v,list) for v in local.values()):
        raise ValueError('Unknown or missing override family')
    if any(local[k] for k in FAMILIES if k!='vector') or len(local['vector'])!=1:
        raise ValueError('Unknown local parameter/layer/static override')
    vector=local['vector'][0]
    if (not isinstance(vector,dict) or set(vector)!={'parameterInfo','expressionGuid','value'}
            or vector['parameterInfo']!=dict(name='Base_Color_Tint',association='GlobalParameter',index=-1)
            or not isinstance(vector['expressionGuid'],str) or not vector['expressionGuid']
            or vector['value']!=TINT or state['effectiveGlobalParameters']!=plan['effectiveGlobalParameters']):
        raise ValueError('Measured local/effective tint binding changed')
    overrides=state['instanceProperties'].get('basePropertyOverrides')
    if not isinstance(overrides,dict) or set(overrides)!=set(BASE_OVERRIDE_FLAGS+BASE_OVERRIDE_VALUES):
        raise ValueError('All 16 base-property flags and 16 values must be observed natively')
    if any(type(overrides[k]) is not bool for k in BASE_OVERRIDE_FLAGS if k!='bOverride_UsageFlags'):
        raise ValueError('Base-property override flags require native booleans')
    for key in ('bOverride_UsageFlags','UsageFlags'):
        if type(overrides[key]) is not int or not 0<=overrides[key]<=0xffffffff:
            raise ValueError('Full unsigned usage bitmask required')
    if any(type(overrides[k]) is not bool for k in BASE_OVERRIDE_VALUES[:9]):
        raise ValueError('Base-property boolean values require native booleans')
    digest(state)
    return copy.deepcopy(state)


def checked_graph(graph,plan):
    observed=plan['sourceGraphObservation']
    from citadel_private_surface_study import MATERIAL_PROPERTIES
    profile=dict(name='retained_mountain_material_properties_v1',complete=True,keys=list(MATERIAL_PROPERTIES))
    if (graph.get('materialProfile')!=profile or not isinstance(graph.get('materialProperties'),dict)
            or set(graph['materialProperties'])!=set(MATERIAL_PROPERTIES)
            or graph.get('roots')!=observed.get('nativeRoots',{}).get('roots')):
        raise ValueError('Complete original material roots/settings required')
    nodes=graph.get('nodes',{})
    if set(nodes)!={r['name'] for r in observed.get('nodes',[])}: raise ValueError('Original node inventory changed')
    dependencies=set()
    for row in observed['nodes']:
        actual=nodes[row['name']]; pins=row['pins']
        expected_pins={str(p['inputIndex']):{k:v for k,v in p.items() if k!='inputIndex'} for p in pins['inputs']}
        if (actual.get('klass')!=row['expressionClass'] or actual.get('pins')!=expected_pins
                or actual.get('outputs')!=pins['outputs'] or not isinstance(actual.get('values'),dict)
                or not actual['values']):
            raise ValueError('Original graph class/pin/value readback changed or incomplete')
        if actual['klass']=='MaterialExpressionTextureSample':
            dependencies.add(package(actual['values'].get('texture')))
        for value in actual['values'].values():
            if isinstance(value,str) and value.startswith('/Game/'):
                dependencies.add(package(value))
    if any(p not in plan['sourcePackageHashes'] for p in dependencies):
        raise ValueError('Graph texture/function dependency outside signed source package closure')
    parameter=nodes['MaterialExpressionVectorParameter_0']['values']
    if set(parameter)!={'parameter_name','default_value','group','sort_priority','expression_guid',
            'use_custom_primitive_data','primitive_data_index','channel_names'}:
        raise ValueError('Complete vector parameter identity/default/editor/primitive metadata required')
    if parameter.get('parameter_name')!='Base_Color_Tint': raise ValueError('Unknown parent graph parameter')
    from citadel_retained_mountain_bridge import checked_vector_values
    checked_vector_values(parameter)
    if parameter.get('use_custom_primitive_data') is not False:
        raise ValueError('Custom primitive parameter source requires separate native review')
    if any(graph['roots'][key]['node'] for key in ('MP_WORLD_POSITION_OFFSET','MP_PIXEL_DEPTH_OFFSET',
            'MP_MATERIAL_ATTRIBUTES','MP_DISPLACEMENT')):
        raise ValueError('Preserve independently changed displacement/attributes')
    digest(graph)
    return copy.deepcopy(graph)


def checked_graph_change(before,after,additions,shader_name,plan):
    if not isinstance(additions,dict) or len(additions)!=3 or set(additions)&set(before['nodes']):
        raise ValueError('Exactly three fresh alpine nodes required')
    classes=sorted(row.get('klass','') for row in additions.values())
    if classes!=sorted(('MaterialExpressionWorldPosition','MaterialExpressionVertexNormalWS','MaterialExpressionCustom')):
        raise ValueError('Alpine study may add only world position, vertex normal and BaseColor shader')
    shader=additions.get(shader_name,{})
    pins=shader.get('pins',{})
    if shader.get('values',{}).get('code')!=plan['shader'] or shader.get('values',{}).get('output_type')!='CMOT_FLOAT3':
        raise ValueError('Exact float3 alpine shader readback required')
    if [pins.get(str(i),{}).get('input_name') for i in range(3)]!=['P','N','Rock'] or len(pins)!=3:
        raise ValueError('Exact P/N/Rock shader input order required')
    for index,klass in ((0,'MaterialExpressionWorldPosition'),(1,'MaterialExpressionVertexNormalWS')):
        name=next(n for n,row in additions.items() if row['klass']==klass)
        edge=pins[str(index)]
        # Unreal's XYZ world-position output explicitly masks RGB; the normal
        # output is an unmasked float3. Require the measured native connection.
        expected_mask=(1,1,1,1,0) if index==0 else (0,0,0,0,0)
        if (edge.get('node')!=name or edge.get('output_index')!=0
                or tuple(edge.get(k) for k in MASK_KEYS)!=expected_mask):
            raise ValueError('Alpine position/normal source pin changed')
    rock=pins['2']; root=before['roots']['MP_BASE_COLOR']
    if any(rock.get(k)!=root[k] for k in ('node','output_index',*MASK_KEYS)):
        raise ValueError('Alpine Rock must consume original texture-times-instance-tint output')
    expected=copy.deepcopy(before);expected['nodes'].update(copy.deepcopy(additions))
    expected['roots']['MP_BASE_COLOR']=dict(node=shader_name,output_index=0,**dict.fromkeys(MASK_KEYS,0))
    if digest(after)!=digest(expected): raise ValueError('Unsigned material settings/root/UV/normal/ORM/graph change')


def checked_copy(before,after,material,parent):
    expected=copy.deepcopy(before);expected.update(material=material,parent=parent)
    if digest(after)!=digest(expected): raise ValueError('Private instance changed original overrides/settings/effective parameters')


def checked_readiness(binding,plan,expected_component):
    """Require the exact native MI proxy, copied parent resource and retained component."""
    if not isinstance(binding,dict): raise ValueError('Required retained instance render binding missing')
    resource=binding.get('renderMaterial',{})
    sections=binding.get('renderSections')
    prefix=package(plan['targetInstance']).split('/Materials/')[0]+'/'
    if (not isinstance(expected_component,str) or not expected_component.startswith(prefix)
            or binding.get('component')!=expected_component or binding.get('materialSlot')!=0
            or binding.get('material')!=plan['targetInstance'] or binding.get('baseMaterial')!=plan['targetBase']
            or binding.get('proxyInterface')!=plan['targetInstance']
            or binding.get('mesh')!=plan['candidateBinding']['mesh']
            or binding.get('hasStaticPermutationResource') is not False
            or any(binding.get(k) is not True for k in ('registered','visible','renderBuffersAvailable','rendererAvailable'))
            or any(binding.get(k) is not False for k in ('hiddenInGame','actorHidden','submittedMeshBatchVerified',
                'screenshotPixelBindingVerified','visualApproved'))
            or not isinstance(sections,list) or not 1<=len(sections)<=256
            or any(type(s.get('lod')) is not int or s['lod']!=0 or type(s.get('triangles')) is not int or s['triangles']<=0 for s in sections)
            or resource.get('available') is not True or resource.get('usedFallback') is not False
            or resource.get('effectiveInterface')!=plan['targetBase'] or resource.get('materialDomain')!=0
            or resource.get('shaderMapPresent') is not True or resource.get('shaderMapValidForRendering') is not True):
        raise ValueError('Missing/fallback/mismatched retained MI proxy, parent resource or actual render section')
    return dict(effectiveProxyReady=True,boundInterface=plan['targetInstance'],expectedResourceOwner=plan['targetBase'],
        submittedMeshBatchVerified=False,screenshotPixelBindingVerified=False,visualApproved=False)


def create_adapter(plan,operations):
    """Native owner supplies readers, fresh duplication, graph edit and save APIs.

    Reader completeness is an explicit prerequisite. Existing inspection JSON or
    reflected struct strings cannot substitute for the native reader contract.
    """
    plan=copy.deepcopy(plan)
    if operations.read_actor_binding(plan['candidateBinding'])!=plan['candidateBinding']['actorState']:
        raise ValueError('Actual candidate actor/component state differs before copying')
    source=checked_instance(operations.read_instance(plan['sourceInstance']),
        plan['sourceInstance'],plan['sourceParent'],plan)
    graph=checked_graph(operations.read_graph(plan['sourceParent']),plan)
    before_hashes=operations.source_hashes()
    if before_hashes!=plan['sourcePackageHashes']: raise ValueError('Signed source package bytes changed')
    if any(operations.exists(package(p)) for p in (plan['targetBase'],plan['targetInstance'])):
        raise ValueError('Preserve existing/interrupted private packages')
    operations.duplicate(package(plan['sourceParent']),package(plan['targetBase']))
    operations.duplicate(package(plan['sourceInstance']),package(plan['targetInstance']))
    if operations.read_graph(plan['targetBase'])!=graph: raise ValueError('Copied parent graph is not exact')
    copied=operations.read_instance(plan['targetInstance'])
    checked_copy(source,copied,plan['targetInstance'],plan['sourceParent'])
    operations.set_parent(plan['targetInstance'],plan['targetBase'])
    retargeted=operations.read_instance(plan['targetInstance'])
    checked_instance(retargeted,plan['targetInstance'],plan['targetBase'],plan)
    checked_copy(source,retargeted,plan['targetInstance'],plan['targetBase'])
    # A reader may cache its result; freeze this witness before compile/reload.
    result=copy.deepcopy(operations.add_alpine_base_color(plan['targetBase'],plan['shader']))
    checked_graph_change(graph,result['graph'],result['additions'],result['shader'],plan)
    operations.compile_and_save(plan['targetBase'],plan['targetInstance'])
    final_graph=operations.read_graph(plan['targetBase']);final_instance=operations.read_instance(plan['targetInstance'])
    if final_graph!=result['graph']: raise ValueError('Saved/reloaded private parent graph changed')
    checked_instance(final_instance,plan['targetInstance'],plan['targetBase'],plan)
    checked_copy(source,final_instance,plan['targetInstance'],plan['targetBase'])
    if operations.read_instance(plan['sourceInstance'])!=source or operations.read_graph(plan['sourceParent'])!=graph:
        raise ValueError('Retained source instance/parent state was mutated')
    if operations.read_actor_binding(plan['candidateBinding'])!=plan['candidateBinding']['actorState']:
        raise ValueError('Retained mountain actor state was mutated')
    if operations.source_hashes()!=before_hashes: raise ValueError('Retained native source bytes were mutated')
    return dict(material=plan['targetInstance'],graphMaterial=plan['targetBase'],
        sourceMaterial=plan['sourceInstance'],sourcePbrGraph=plan['sourceParent'],
        beforeGraph=graph,afterGraph=final_graph,beforeInstance=source,afterInstance=final_instance,
        expectedResourceOwner=plan['targetBase'],hasStaticPermutationResource=False,
        editorContractChecksPassed=True,coldProcessVerified=False,rendererStateVerified=False,
        submittedMeshBatchVerified=False,screenshotPixelBindingVerified=False,visualApproved=False,releaseAcceptance=False)
