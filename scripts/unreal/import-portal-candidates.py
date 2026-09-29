"""Import immutable baked portal candidates into private native draft packages.

No map, route, startup setting, or approval flag is changed.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/portal-models/baked'
records=json.loads((OUT/'materials.json').read_text())
spec=importlib.util.spec_from_file_location('portal_import_materials',Path(__file__).with_name('import-models.py'))
models=importlib.util.module_from_spec(spec);spec.loader.exec_module(models)
library=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
result=[]
for row in records:
    name=row['name'];source=OUT/(name+'.glb')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=row['glbSha256']:raise RuntimeError('Changed baked portal: '+name)
    directory='/Game/PortalCandidates/'+name+'_'+digest[:12]
    if library.does_directory_exist(directory):raise RuntimeError('Preserve existing candidate: '+directory)
    gltf,images=models.read_glb(source)
    transmission={}
    for material in gltf.get('materials',[]):
        extension=material.get('extensions',{}).pop('KHR_materials_transmission',None)
        if extension is None:continue
        if set(extension)-{'transmissionFactor'}:raise RuntimeError('Textured transmission needs a separate reviewed translation')
        factor=extension.get('transmissionFactor',0)
        if not math.isfinite(factor) or not 0<=factor<=1:raise RuntimeError('Invalid crystal transmission')
        transmission[material['name']]=(factor,material.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1]))
    context=dict(profile=name,directory=OUT,gltf=gltf,images=images,destination=directory,
        conversion=dict(kind='staticProps',sourceSha256=digest))
    textures,_=models.import_textures(unreal,context)
    materials,_=models.create_materials(unreal,context,textures)
    # The shared importer intentionally rejects transmission. Translate the
    # candidates' constant thin-surface transmission explicitly instead of dropping it.
    # https://dev.epicgames.com/documentation/unreal-engine/lit-translucency-in-unreal-engine
    graph=unreal.MaterialEditingLibrary
    for key,(factor,color) in transmission.items():
        material=materials[key]
        material.set_editor_properties(dict(blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT,
            shading_model=unreal.MaterialShadingModel.MSM_THIN_TRANSLUCENT,
            translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING))
        thin=graph.create_material_expression(material,unreal.MaterialExpressionThinTranslucentMaterialOutput)
        tint=graph.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
        tint.set_editor_property('constant',unreal.LinearColor(*[c*factor for c in color[:3]],1))
        if not graph.connect_material_expressions(tint,'',thin,'TransmittanceColor'):raise RuntimeError('Cannot bind crystal transmittance')
        opacity=graph.create_material_expression(material,unreal.MaterialExpressionConstant)
        opacity.set_editor_property('r',1-factor)
        if not graph.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY):raise RuntimeError('Cannot bind crystal opacity')
        graph.layout_material_expressions(material)
        if graph.recompile_material(material):raise RuntimeError('Crystal shader compilation failed')
        library.set_metadata_tag(material,'WarPortalTransmission',str(factor))
    mapping=models.material_slot_mapping(materials.keys())
    parts={}
    for part in ('Structure','Effects'):
        fbx=OUT/(name+'_'+part+'.fbx')
        if hashlib.sha256(fbx.read_bytes()).hexdigest()!=row['fbx'][part]:raise RuntimeError('Changed FBX: '+str(fbx))
        options=unreal.FbxImportUI()
        options.set_editor_properties(dict(automated_import_should_detect_type=False,
            mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,original_import_type=unreal.FBXImportType.FBXIT_STATIC_MESH,
            import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False))
        options.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,auto_generate_collision=False,import_uniform_scale=1.,
            normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS))
        task=unreal.AssetImportTask()
        task.set_editor_properties(dict(filename=str(fbx),destination_path=directory,destination_name=name+'_'+part,
            automated=True,save=False,replace_existing=False,factory=unreal.FbxFactory(),options=options))
        tools.import_asset_tasks([task])
        mesh=unreal.load_asset(directory+'/'+name+'_'+part)
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('No imported portal '+part)
        slots=list(mesh.static_materials)
        for slot in slots:slot.material_interface=materials[mapping[str(slot.material_slot_name)]]
        mesh.static_materials=slots
        bounds=mesh.get_bounds()
        parts[part]=dict(asset=mesh.get_path_name(),extentCm=[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],collisionApproved=False)
    for path in library.list_assets(directory,recursive=True):
        asset=unreal.load_asset(path)
        library.set_metadata_tag(asset,'WarPortalCandidate','Unapproved')
        if not library.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+path)
    result.append(dict(name=name,sourceSha256=digest,parts=parts,nativeImported=True,artApproved=False,worldInstalled=False,
        transmissionMaterials=list(transmission),nativeVisualParityVerified=False))
    (OUT/'native-candidates.json').write_text(json.dumps(result,indent=2)+'\n')
    unreal.log('WAR_PORTAL_CANDIDATE_IMPORTED='+name)
