"""Private source-derived cosmetic foliage LODs and materials; never edits shared assets."""
import hashlib,json
import unreal
from t1_foliage_recipe import foliage_recipe


def foliage_detail(assets,identity,mesh):
    recipe=foliage_recipe(identity)
    before=unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)
    if not json.loads(before).get('valid'):raise RuntimeError('Foliage LOD zero source data is missing')
    if not mesh.get_path_name().startswith(assets.folder+'/') or not assets.folder.startswith('/Game/WorldRebuild/T1'):
        raise RuntimeError('Foliage detail requires a fresh isolated T1 asset')
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    # Commandlets do not register this stateless editor utility subsystem. Its
    # public mesh operations remain bounded here to fresh private assets.
    if editor is None:editor=unreal.new_object(unreal.StaticMeshEditorSubsystem)
    options=unreal.StaticMeshReductionOptions()
    options.set_editor_property('auto_compute_lod_screen_size',False)
    rows=[]
    for row in recipe['lods']:
        setting=unreal.StaticMeshReductionSettings();setting.set_editor_property('percent_triangles',row['triangles']);setting.set_editor_property('screen_size',row['screen']);rows.append(setting)
    options.set_editor_property('reduction_settings',rows)
    if editor.set_lods(mesh,options)!=3 or editor.get_lod_count(mesh)!=3:
        raise RuntimeError('Private foliage LOD construction failed')
    counts=[editor.get_number_verts(mesh,i) for i in range(3)]
    if not counts[0]>counts[1]>counts[2]>0:raise RuntimeError('Foliage detail must retain nonempty descending native geometry')
    sizes=list(editor.get_lod_screen_sizes(mesh))
    if len(sizes)!=3 or any(abs(a-b['screen'])>1e-5 for a,b in zip(sizes,recipe['lods'])):
        raise RuntimeError('Saved foliage screen thresholds differ from their recipe')
    lib=unreal.MaterialEditingLibrary;materials=[]
    for i in range(mesh.get_num_sections(0)):
        material=mesh.get_material(i)
        if not material or not material.get_path_name().startswith(assets.folder+'/'):
            raise RuntimeError('Preserve shared foliage materials')
        base=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
        output=lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_BASE_COLOR)
        if not base:raise RuntimeError('Foliage source color binding is missing')
        def expr(kind,**values):
            node=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
            for k,v in values.items():node.set_editor_property(k,v)
            return node
        def scalar(value):return expr('Constant',r=value)
        def connect(a,ap,b,bp):
            if not lib.connect_material_expressions(a,ap,b,bp):raise RuntimeError('Cannot bind foliage adaptation')
        tint=expr('Constant3Vector',constant=unreal.LinearColor(*recipe['tint'],1))
        regional=expr('Multiply');connect(base,output,regional,'A');connect(tint,'',regional,'B')
        variation=expr('LinearInterpolate');connect(scalar(recipe['instanceTintRange'][0]),'',variation,'A');connect(scalar(recipe['instanceTintRange'][1]),'',variation,'B');connect(expr('PerInstanceRandom'),'',variation,'Alpha')
        shaded=expr('Multiply');connect(regional,'',shaded,'A');connect(variation,'',shaded,'B')
        transmission=expr('Multiply');connect(regional,'',transmission,'A');connect(scalar(recipe['transmission']),'',transmission,'B')
        material.set_editor_property('two_sided',True)
        material.set_editor_property('dithered_lod_transition',True)
        material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        material.set_editor_property('used_with_instanced_static_meshes',True)
        if not lib.connect_material_property(shaded,'',unreal.MaterialProperty.MP_BASE_COLOR) or not lib.connect_material_property(transmission,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR):
            raise RuntimeError('Cannot bind source-derived foliage shading')
        lib.recompile_material(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError('Cannot save private foliage material')
        materials.append(material.get_path_name())
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):raise RuntimeError('Cannot save private foliage LODs')
    if json.loads(before)!=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)):
        raise RuntimeError('Foliage adaptation changed source geometry at LOD zero')
    return dict(recipe=recipe,sourceLodZeroPreserved=True,nativeVertexCounts=counts,nativeScreenSizes=sizes,materials=materials,sourceTextureChannelsPreserved=True,
        appearanceApproved=False,performanceAccepted=False)


def foliage_inventory(mesh):
    if not mesh or not mesh.get_path_name().startswith('/Game/WorldRebuild/T1'):
        raise RuntimeError('Detailed foliage must remain in private T1 assets')
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if editor is None:editor=unreal.new_object(unreal.StaticMeshEditorSubsystem)
    if editor.get_lod_count(mesh)!=3:raise RuntimeError('Saved foliage lost its three detail levels')
    vertices=[mesh.get_num_vertices(i) for i in range(3)];triangles=[mesh.get_num_triangles(i) for i in range(3)]
    screens=list(editor.get_lod_screen_sizes(mesh))
    if not vertices[0]>vertices[1]>vertices[2]>0 or not triangles[0]>triangles[1]>triangles[2]>0 or len(screens)!=3 or any(abs(a-b)>1e-5 for a,b in zip(screens,[1,.1,.025])):
        raise RuntimeError('Saved foliage detail geometry or thresholds differ')
    materials=[]
    for i in range(mesh.get_num_sections(0)):
        m=mesh.get_material(i)
        if not m.get_editor_property('two_sided') or not m.get_editor_property('used_with_instanced_static_meshes') or m.get_editor_property('shading_model')!=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE:
            raise RuntimeError('Saved source-derived foliage shading differs')
        if not unreal.MaterialEditingLibrary.get_material_property_input_node(m,unreal.MaterialProperty.MP_SUBSURFACE_COLOR):
            raise RuntimeError('Saved foliage transmission is unbound')
        materials.append(dict(path=m.get_path_name(),twoSided=True,shading='TwoSidedFoliage',sourceTransmissionBound=True))
    source=unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)
    if not json.loads(source).get('valid'):raise RuntimeError('Saved foliage source data is missing')
    return dict(nativeVertexCounts=vertices,nativeTriangleCounts=triangles,screenSizes=screens,materials=materials,
        sourceLodZeroSha256=hashlib.sha256(source.encode()).hexdigest(),worldDisplacement=False,performanceAccepted=False,visualApproved=False)
