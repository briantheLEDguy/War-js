"""Private leaf shading/normal adaptation; source geometry, bark and collision are retained."""
import copy,json
from t1_canopy import softened_leaf_normals,retained_native_canopy
import unreal


def adapt_canopies(assets,states,sources):
    if not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_'):raise RuntimeError('Canopy adaptation requires fresh private T1 assets')
    result=copy.deepcopy(states);cache={};meshes={};adapted=[];lib=unreal.MaterialEditingLibrary
    for label,state in result.items():
        if state['kind']!='mesh':continue
        name=state['mesh'].rsplit('/',1)[-1].split('.')[0]
        if name not in sources:continue
        recipe=sources[name]
        if len(state['materials'])!=recipe['materialCount']:raise RuntimeError('Native canopy slots differ from reviewed source')
        old=state['materials'][:];old_mesh=state['mesh'];mesh_key=(name,old_mesh)
        if mesh_key not in meshes:
            original_mesh=unreal.load_asset(old_mesh)
            before=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(original_mesh,0))
            mesh=assets.composite('soft_canopy_'+name,softened_leaf_normals(recipe['data'],recipe['leafSlots']),True)
            after=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0))
            retained_native_canopy(before,after,recipe['leafSlots'])
            if original_mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')!=mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag'):raise RuntimeError('Canopy collision policy differs')
            meshes[mesh_key]=mesh.get_path_name()
        state['mesh']=meshes[mesh_key]
        for slot in recipe['leafSlots']:
            original=state['materials'][slot];key=(name,slot,original)
            if key not in cache:
                destination=assets.folder+'/Materials/M_canopy_'+name+'_'+str(slot)
                if unreal.EditorAssetLibrary.does_asset_exist(destination):raise RuntimeError('Preserve an existing canopy material')
                material=unreal.EditorAssetLibrary.duplicate_asset(original,destination)
                if not isinstance(material,unreal.Material):raise RuntimeError('Canopy adaptation requires its exact source material graph')
                base=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
                output=lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_BASE_COLOR)
                if not base:raise RuntimeError('Canopy source color is unbound')
                factor=lib.create_material_expression(material,unreal.MaterialExpressionConstant);factor.set_editor_property('r',.24)
                transmission=lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
                if not lib.connect_material_expressions(base,output,transmission,'A') or not lib.connect_material_expressions(factor,'',transmission,'B') or not lib.connect_material_property(transmission,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR):
                    raise RuntimeError('Cannot bind reviewed leaf transmission')
                material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
                material.set_editor_property('two_sided',True)
                lib.recompile_material(material)
                if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError('Cannot save private canopy material')
                cache[key]=material.get_path_name()
            state['materials'][slot]=cache[key]
        if state['materials'][0]!=old[0]:raise RuntimeError('Canopy adaptation changed bark')
        adapted.append(dict(id=label,sourceModel=recipe['sourceModel'],originalMaterials=old,materials=state['materials'][:],leafSlots=recipe['leafSlots'],barkPreserved=True,originalMesh=old_mesh,mesh=state['mesh'],sourceGeometryAndCollisionPreserved=True,leafNormalsAdapted=True))
    if not adapted:raise RuntimeError('No reviewed canopy bindings were adapted')
    return result,dict(actors=adapted,materials=len(cache),meshes=len(meshes),sourceChannelsPreserved=True,worldDisplacement=False,visualApproved=False)
