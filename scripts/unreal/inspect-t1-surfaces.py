"""Read native terrain bindings and normal orientation; no saved package changes."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'native-latest.json').read_text())
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
results=[]
for zone in receipt['zones']:
    if not levels.load_level(zone['map']):raise RuntimeError('Review map missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world);unreal.WarImportLibrary.prepare_world_preview_frame(world)
    for actor in actors.get_all_level_actors():
        if 'WarT1PrototypeTerrain' not in [str(t) for t in actor.tags]:continue
        component=actor.static_mesh_component;mesh=component.static_mesh
        faces=json.loads(unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh))
        row={'zone':zone['id'],'actor':actor.get_actor_label(),'mesh':mesh.get_path_name(),
             'materials':[component.get_material(i).get_path_name() for i in range(component.get_num_materials())],
             'faceDiagnostic':{k:v for k,v in faces.items() if k!='triangles'},'sample':faces.get('triangles',[])[:2],
             'castShadow':component.get_editor_property('cast_shadow')}
        material=component.get_material(0)
        expression=unreal.MaterialEditingLibrary.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
        row['baseColorExpression']=expression.get_class().get_name() if expression else None
        if isinstance(expression,unreal.MaterialExpressionConstant3Vector):row['baseColor']=str(expression.get_editor_property('constant'))
        results.append(row)
(DIRECTORY/'surface-inspection.json').write_text(json.dumps(results,indent=2)+'\n')
unreal.log('WAR_T1_SURFACES_INSPECTED='+str(len(results)))
