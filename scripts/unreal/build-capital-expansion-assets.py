"""Adapt selected authored meshes into private static GM building templates."""
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import recipes, digest, rotate, rectangle, overlaps, piece
from capital_expansion_materials import ExpansionMaterials
OUT=ROOT/'artifacts/unreal/capital-expansion'
DEST='/Game/LicensedKits/CapitalExpansion/V1'


def main():
    if Path(unreal.Paths.project_dir()).resolve()!=ROOT/'unreal/AegisWar': raise RuntimeError('Use AegisWar')
    if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Merging requires rendering')
    staged=json.loads((OUT/'staged.json').read_text())
    for row in staged['files']:
        if hashlib.sha256((ROOT/'unreal/AegisWar/Content'/row['path']).read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Staged source changed: '+row['path'])
    baseline=json.loads((OUT/'baseline.json').read_text())
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    workspace=DEST+'/AssemblyWorkspace_'+uuid.uuid4().hex
    if unreal.EditorAssetLibrary.does_asset_exist(workspace): raise RuntimeError('Scratch level already exists')
    if not level.new_level(workspace): raise RuntimeError('Cannot create assembly workspace')
    mesh_tools=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
    assets=unreal.EditorAssetLibrary
    report_path=OUT/'assets.json'
    prior=json.loads(report_path.read_text()) if report_path.exists() else {'templates':{}}
    result={'schemaVersion':1,'sourceFingerprint':digest(staged['files']),'templates':{},'visualApproved':False}
    sources={}
    palette=ExpansionMaterials(DEST+'/Materials')

    def resolve(name):
        if name in sources: return sources[name]
        if name.startswith('riftspire_house_'):
            paths=sorted({c['mesh'] for a in baseline['riftspire_capital']['actors'] for c in a['state']['components']
                          if c.get('mesh') and ('/prop_'+name+'_') in c['mesh']})
            if not paths: raise RuntimeError('Missing native Riftspire house: '+name)
            meshes=[unreal.load_asset(p) for p in paths]
        else:
            meshes=[unreal.load_asset(staged['meshes'][name]['path'])]
            if name in ('SM_Bed','SM_Bed_2'):
                meshes.extend(unreal.load_asset(staged['meshes'][n]['path'])
                              for n in ('SM_Bed_Matress','SM_Bed_Pillow','SM_Bed_Sheet'))
        if any(not isinstance(m,unreal.StaticMesh) for m in meshes): raise RuntimeError('Missing mesh: '+name)
        sources[name]=meshes
        return meshes

    for recipe in recipes():
        signature=digest({'recipe':recipe,'sources':result['sourceFingerprint'],'assemblyRevision':4 if recipe['interior'] else 3})
        target=DEST+'/SM_'+recipe['id']+'_'+signature[:10]
        old=prior['templates'].get(recipe['id'])
        if old and old['signature']==signature:
            file=ROOT/'unreal/AegisWar/Content'/(old['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')
            if hashlib.sha256(file.read_bytes()).hexdigest()!=old['sha256']: raise RuntimeError('Preserve edited template')
            result['templates'][recipe['id']]=old
            continue
        if assets.does_asset_exist(target): raise RuntimeError('Unreceipted template: '+target)
        instances=[]; parts=[]; occupied=[]; furniture_positions={}
        definitions=list(recipe['components'])
        if not recipe['interior']:
            base_meshes=resolve(definitions[0]['mesh'])
            bx=max(m.get_bounds().origin.x+m.get_bounds().box_extent.x for m in base_meshes)-min(m.get_bounds().origin.x-m.get_bounds().box_extent.x for m in base_meshes)
            by=max(m.get_bounds().origin.y+m.get_bounds().box_extent.y for m in base_meshes)-min(m.get_bounds().origin.y-m.get_bounds().box_extent.y for m in base_meshes)
            if recipe.get('roomSize'): bx,by=recipe['roomSize']
            variant=int(recipe['id'].rsplit('_',1)[1])
            definitions += [piece('SM_Barrel' if variant%2 else 'SM_Crate',bx/2+75,by/3,0,variant*30,role='furniture'),
                            piece('SM_Bench',-bx/2-65,-by/4,0,90,role='furniture'),
                            piece('SM_Crate' if variant%3 else 'SM_Barrel',bx/2+65,-by/3,0,variant*20,role='furniture')]
        for number,definition in enumerate(definitions):
            name=definition['mesh']; meshes=resolve(name)
            # Imported Riftspire parts share one origin. Centre the whole assembly,
            # retaining their relative pivots and original material assignments.
            bounds=[m.get_bounds() for m in meshes]
            low=[min(getattr(b.origin,k)-getattr(b.box_extent,k) for b in bounds) for k in ('x','y','z')]
            high=[max(getattr(b.origin,k)+getattr(b.box_extent,k) for b in bounds) for k in ('x','y','z')]
            origin=[(a+b)/2 for a,b in zip(low,high)]
            scale=definition['scale']; yaw=definition['yaw']; anchor=list(definition['anchor'])
            if definition['role']=='furniture' and recipe['interior']:
                if 'support' in definition:
                    support=furniture_positions.get(definition['support'])
                    if not support: continue
                    anchor=[support[0],support[1],support[2]]
                else:
                    w,d=recipe['roomSize']; base=anchor[2]
                    # Fit edge furnishings around a continuous 140 cm central aisle.
                    # Large shop counters are intentionally shortened as furniture,
                    # never used to scale a player doorway or architectural shell.
                    if name=='SM_Counter': scale=[.65,.65,.85]
                    if name in ('SM_Bench','SM_Bench_2'): scale=[.65,1,1]
                    if name=='SM_Bookshelf': scale=[.72,.72,.72]
                    ex,ey=(high[0]-low[0])*scale[0],(high[1]-low[1])*scale[1]
                    candidates=[(anchor[0],anchor[1],yaw)]
                    for turn in (0,90):
                        for y in range(int(d/2-80),int(-d/2+80),-25):
                            for x in range(int(-w/2+80),int(w/2-80),25): candidates.append((x,y,turn))
                    found=None
                    for x,y,turn in candidates:
                        footprint=rectangle((x,y),(ex,ey),turn,12)
                        if any(abs(px)>w/2-35 or abs(py)>d/2-40 for px,py in footprint): continue
                        if any(overlaps(footprint,p) for z,p in occupied if z==base): continue
                        # Keep the east entrance lane and central cross aisle clear.
                        if overlaps(footprint,rectangle((w/2-150,-d/4),(140,d/2+120),0)): continue
                        if overlaps(footprint,rectangle((0,0),(w-80,140),0)): continue
                        if recipe['upperFloor'] and overlaps(footprint,rectangle((-w/2+150,-d/2+380),(190,760),0)): continue
                        if base>=300 and overlaps(footprint,rectangle((0,-d/2+800),(w-80,140),0)): continue
                        found=(x,y,turn,footprint);break
                    if found is None: raise RuntimeError('Furnishing cannot fit: '+recipe['id']+'/'+name)
                    x,y,yaw,footprint=found; anchor=[x,y,base]; occupied.append((base,footprint))
                    if name=='SM_Bookshelf': yaw+=180
                    furniture_positions[len(furniture_positions)]=[x,y,base+(high[2]-low[2])*scale[2]]
            ox,oy=rotate(origin[0]*scale[0],origin[1]*scale[1],yaw)
            location=unreal.Vector(anchor[0]-ox,anchor[1]-oy,anchor[2]-low[2]*scale[2])
            for mesh in meshes:
                actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,location,unreal.Rotator(yaw=yaw))
                actor.set_actor_scale3d(unreal.Vector(*scale))
                actor.static_mesh_component.set_static_mesh(mesh)
                for slot in range(len(mesh.static_materials)):
                    source=mesh.get_material(slot)
                    actor.static_mesh_component.set_material(slot,palette.material(source,
                        'gateward' if recipe['id'].startswith('aegis') else 'ashgate',definition['role']))
                instances.append(actor)
                parts.append({'mesh':mesh.get_path_name(),'anchor':anchor,'yaw':yaw,'scale':scale,'role':definition['role']})
        settings=unreal.MeshMergingSettings()
        for key,value in {'lod_selection_type':unreal.MeshLODSelectionType.ALL_LODS,
                          'merge_materials':False,'merge_equivalent_materials':False,
                          'bake_vertex_data_to_mesh':True,'generate_light_map_uv':False,
                          'pivot_type':unreal.MeshMergePivotType.WORLD_ORIGIN}.items():
            settings.set_editor_property(key,value)
        options=unreal.MergeStaticMeshActorsOptions()
        options.base_package_name=target; options.mesh_merging_settings=settings
        merged=mesh_tools.merge_static_mesh_actors(instances,options)
        mesh=merged.static_mesh_component.static_mesh if merged else None
        if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Merge failed: '+recipe['id'])
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if mesh.get_num_lods()<3:
            lod=unreal.EditorScriptingMeshReductionOptions()
            lod.auto_compute_lod_screen_size=True
            lod.reduction_settings=[unreal.EditorScriptingMeshReductionSettings(percent_triangles=p,screen_size=s)
                                    for p,s in ((1,1),(.5,.5),(.2,.2))]
            mesh_tools.set_lods(mesh,lod)
        if not assets.save_loaded_asset(mesh,only_if_is_dirty=False): raise RuntimeError('Template save failed')
        b=mesh.get_bounds()
        file=ROOT/'unreal/AegisWar/Content'/(mesh.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
        materials=[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials]
        if not all(materials): raise RuntimeError('Merge lost a material')
        row={**recipe,'components':parts,'mesh':mesh.get_path_name(),'signature':signature,
             'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'materials':materials,
             'origin':[b.origin.x,b.origin.y,b.origin.z],'extent':[b.box_extent.x,b.box_extent.y,b.box_extent.z],
             'triangles':[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]}
        result['templates'][recipe['id']]=row
        # Write progress receipts after each saved template, allowing safe recovery.
        report_path.write_text(json.dumps(result,indent=2)+'\n')
        # Only this invocation's explicit temporary actors can be removed. Never
        # enumerate the level for cleanup, even in this newly-created scratch map.
        for a in instances+[merged]:
            if unreal.SystemLibrary.is_valid(a): actors.destroy_actor(a)
        unreal.log('WAR_EXPANSION_TEMPLATE='+recipe['id'])
    report_path.write_text(json.dumps(result,indent=2)+'\n')
    unreal.log('WAR_EXPANSION_ASSETS='+str(len(result['templates'])))


main()
