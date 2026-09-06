"""Bind only the new authored geometry to the existing animation contract.

The old GLB supplies its armature and actions only. Imported meshes, materials and
images are discarded. Source control meshes remain separately editable; runtime
modules contain inspectable evaluated geometry and explicit vertex weights.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
sys.path.insert(0,str(ROOT/"tools"))
import build_proof as authored

SLOTS=("body","head","shoulders","chest","hands","waist","legs","feet","back","tabard","weapon")
COMPONENT_SLOTS={"head":"body","gorget":"head","breastplate":"chest","pauldron":"shoulders","medallion":"chest","garments":"tabard","backplate":"back","warhammer":"weapon","tome":"waist","arms":"hands","body_underlayers":"body"}
CLIPS={"idle","walk","run","combat_idle","attack_melee","attack_ranged","cast","death","jump"}
BAKED_CLOTH_DETAILS={"relic_tabard_fold_following_cross","relic_tabard_gilded_pointed_hem"}
LOD2_OMIT={
    "gorget_creed_inlay","gorget_authored_rivet","knee_skull_teeth",
    "knee_and_greave_fasteners","left_pauldron_authored_rivet","left_pauldron_lame_fasteners",
    "reliquary_inner_beaded_border","reliquary_dental_crowns","reliquary_rim_fasteners",
    "rear_reliquary_inner_beaded_border","rear_reliquary_dental_crowns","rear_reliquary_rim_fasteners",
    "belt_reliquary_dental_crowns","relic_upper_manual_ink_strokes","relic_upper_wax_stamp_marks",
    "rear_reliquary_lower_pendant",
    "relic_belt_wax_stamp_marks","relic_tabard_explicit_fringe_tassels","tome_page_foreedge_rules",
    "tome_corner_fasteners","boot_buckle_tongue","warhammer_skull_nose_and_teeth",
    "warhammer_authored_corner_stud","breastplate_reinforcement_steel_inset",
}


def verify_contract_rig(rig):
    reference=json.loads((ROOT/"source/rig_reference.dat").read_text())
    if set(reference["bones"])!=set(rig.data.bones.keys()):
        raise ValueError("Canonical bone names differ")
    for name,record in reference["bones"].items():
        if max(abs(rig.data.bones[name].matrix_local[r][c]-record["matrix"][r][c]) for r in range(4) for c in range(4))>1e-5:
            raise ValueError(f"Canonical rest matrix differs: {name}")
    if max(abs(rig.matrix_world[r][c]-(1 if r==c else 0)) for r in range(4) for c in range(4))>1e-5:
        raise ValueError("Canonical rig world transform differs")
    for name in ("socket_hand_R","socket_hand_L","socket_back","socket_root"):
        socket=bpy.data.objects.get(name)
        if socket is None or socket.type!="EMPTY" or socket.parent!=rig:
            raise ValueError(f"Canonical attachment socket invalid: {name}")


def import_contract_rig(path):
    frozen=ROOT/"source/humanoid_game_v2_animation_contract.blend"
    if frozen.exists():
        metadata=json.loads(frozen.with_suffix(".dat").read_text())
        if hashlib.sha256(frozen.read_bytes()).hexdigest()!=metadata["sha256"]:
            raise ValueError("Frozen animation contract hash mismatch")
        with bpy.data.libraries.load(str(frozen),link=False) as (data_from,data_to):
            data_to.objects=data_from.objects
            data_to.actions=data_from.actions
        for obj in data_to.objects:
            if obj.type not in {"ARMATURE","EMPTY"}:
                raise ValueError("Animation contract must contain no mesh objects")
            bpy.context.scene.collection.objects.link(obj)
        rigs=[obj for obj in data_to.objects if obj.type=="ARMATURE"]
        if len(rigs)!=1 or not CLIPS.issubset({a.name for a in data_to.actions}):
            raise ValueError("Frozen animation contract missing rig/actions")
        rig=rigs[0]
        rig.data.pose_position="REST"
        bpy.context.view_layer.update()
        verify_contract_rig(rig)
        return rig
    before_objects=set(bpy.data.objects)
    before_materials=set(bpy.data.materials)
    before_images=set(bpy.data.images)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported=set(bpy.data.objects)-before_objects
    rigs=[o for o in imported if o.type=="ARMATURE"]
    if len(rigs)!=1:
        raise ValueError("Canonical animation source must contain one rig")
    rig=rigs[0]
    rig.name="humanoid_game_v2"
    if max(abs(rig.matrix_world[row][column]-(1 if row==column else 0)) for row in range(4) for column in range(4))>1e-5:
        raise ValueError("Canonical rig world transform must be identity")
    sockets={o for o in imported if o.type=="EMPTY" and o.name in {"socket_hand_R","socket_hand_L","socket_back","socket_root"}}
    if len(sockets)!=4:
        raise ValueError("Canonical source must provide all four attachment sockets")
    for obj in imported-{rig}-sockets:
        data=obj.data
        kind=obj.type
        bpy.data.objects.remove(obj,do_unlink=True)
        if kind=="MESH" and data.users==0:
            bpy.data.meshes.remove(data)
    for mat in set(bpy.data.materials)-before_materials:
        if mat.users==0:
            bpy.data.materials.remove(mat)
    for image in set(bpy.data.images)-before_images:
        if image.users==0:
            bpy.data.images.remove(image)
    if not CLIPS.issubset({a.name for a in bpy.data.actions}):
        raise ValueError("Canonical source is missing required animation clips")
    if rig.animation_data:
        rig.animation_data.action=None
        for track in rig.animation_data.nla_tracks:
            track.mute=True
    rig.data.pose_position="REST"
    for bone in rig.pose.bones:
        bone.matrix_basis=Matrix.Identity(4)
    rig["socket_objects"]=json.dumps(sorted(o.name for o in sockets))
    bpy.context.view_layer.update()
    rig["geometry_provenance"]="Armature and compatible animations only; no original mesh retained"
    rig["source_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    verify_contract_rig(rig)
    bpy.data.libraries.write(str(frozen),{rig,*sockets,*bpy.data.actions},fake_user=True,compress=True)
    frozen.with_suffix(".dat").write_text(json.dumps({"sha256":hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "source_glb_sha256":rig["source_sha256"],"geometry_retained":False,
        "contents":"Canonical armature, four socket empties and nine compatible actions only"},indent=2)+"\n")
    return rig


def source_slot(obj):
    value=obj.get("slot","")
    component=Path(obj["source_file"]).stem
    if component=="head":
        return "body"
    # Covered cloth/gloves remain visible when the corresponding metal module is removed.
    if obj["source_part"] in {"upper_arm_joint_underlayer","forearm_leather_underlayer","gauntlet_glove_palm_and_web"}:
        return "body"
    return value if value in SLOTS else COMPONENT_SLOTS.get(component,value)


def clamp(value, low, high):
    return max(low,min(high,value))


def weights_for(obj, co, slot):
    bone=obj.get("rigid_bone","")
    mirrored=obj.get("mirror_bone","")
    if mirrored and co.x < -1e-7:
        bone=mirrored
    part=obj["source_part"]
    if slot=="tabard":
        # A continuous garment follows both legs through the center panel.
        hips=clamp((co.z-.42)/.65,.20,1.0)
        left=clamp(co.x/.18+.5,0,1)
        return {"hips":hips,"thigh_L":(1-hips)*left,"thigh_R":(1-hips)*(1-left)}
    if part=="head_skin":
        head=clamp((co.z-1.61)/.075,0,1)
        return {"neck":1-head,"head":head}
    if part=="padded_abdominal_doublet":
        chest=clamp((co.z-1.13)/.12,0,1)
        return {"spine":1-chest,"chest":chest}
    if bone and bone!="weapon_root":
        return {bone:1.0}
    component=Path(obj["source_file"]).stem
    if component=="head":
        return {"head":1.0}
    return {{"head":"upper_chest","chest":"upper_chest","back":"upper_chest","waist":"hips","body":"hips"}.get(slot,"hips"):1.0}


def recalculate_normals(mesh):
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()


def finishing_cap(source, slot, lod):
    for modifier in source.modifiers:
        if modifier.type=="SUBSURF":
            if source["source_part"]=="front_crimson_tabard":
                # The explicitly fitted embroidery follows this finished surface.
                cap=1
            elif lod==0:
                cap=2 if Path(source["source_file"]).stem=="head" else 1
            else:
                cap=1 if lod==1 and slot=="body" else 0
            modifier.levels=modifier.render_levels=min(modifier.levels,cap)
        elif modifier.type=="BEVEL":
            modifier.segments=1 if lod==2 or slot=="waist" else min(modifier.segments,2)


def evaluate_runtime_part(source, collection, rig, lod):
    slot=source_slot(source)
    if slot not in SLOTS:
        raise ValueError(f"Unmapped runtime slot {slot} for {source.name}")
    saved=[(m,m.levels,m.render_levels) if m.type=="SUBSURF" else (m,m.segments,None) for m in source.modifiers if m.type in {"SUBSURF","BEVEL"}]
    finishing_cap(source,slot,lod)
    # A thin authored-surface finish closes skin/eye interfaces for runtime QC.
    shell=None
    if source["source_part"] in {"head_skin","eyes"}:
        shell=source.modifiers.new("Runtime skin wall","SOLIDIFY")
        shell.thickness=.001
        shell.offset=-1
    bpy.context.view_layer.update()
    evaluated=source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
    mesh.transform(source.matrix_world)
    recalculate_normals(mesh)
    obj=bpy.data.objects.new(f"lod{lod}.{source.name}",mesh)
    collection.objects.link(obj)
    obj["slot"]=slot
    obj["source_part"]=source["source_part"]
    obj["source_sha256"]=source["source_sha256"]
    obj["source_file"]=source["source_file"]
    obj["source_finishing"]=json.dumps([{"type":m.type,**({"level":m.levels} if m.type=="SUBSURF" else {"segments":m.segments} if m.type=="BEVEL" else {})} for m in source.modifiers])
    if slot!="weapon":
        obj.parent=rig
        for vertex in mesh.vertices:
            weights={name:weight for name,weight in weights_for(source,vertex.co,slot).items() if weight>1e-6}
            total=sum(weights.values())
            if not total or len(weights)>4 or any(name not in rig.data.bones for name in weights):
                raise ValueError(f"Invalid skin assignment {source.name}: {weights}")
            for name,weight in weights.items():
                group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                group.add([vertex.index],weight/total,"REPLACE")
        modifier=obj.modifiers.new("Canonical deformation","ARMATURE")
        modifier.object=rig
        modifier.use_deform_preserve_volume=False
    if shell:
        source.modifiers.remove(shell)
    for mod,a,b in saved:
        if mod.type=="SUBSURF":
            mod.levels,mod.render_levels=a,b
        else:
            mod.segments=a
    return obj


def join_slot(objects, slot, lod):
    provenance=[{"part":o["source_part"],"file":o["source_file"],"sha256":o["source_sha256"],"finishing":json.loads(o["source_finishing"])} for o in objects]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    if len(objects)>1:
        bpy.ops.object.join()
    joined=bpy.context.object
    joined.name=f"ember_arcanist_{slot}_lod{lod}"
    joined["slot"]=slot
    joined["lod"]=lod
    joined["geometry_provenance"]="Explicit authored source records evaluated with permitted finishing"
    joined["source_records"]=json.dumps(provenance)
    return joined


def calibrate_weapon(obj, rig):
    """Store the real hand grip at the socket origin using existing rest matrices."""
    bpy.context.view_layer.update()
    socket_object=bpy.data.objects["socket_hand_R"]
    socket=socket_object.matrix_world.copy()
    grip=Vector((0,0,1.09))
    desired=Matrix.Translation(socket.translation-grip)
    calibration=socket.inverted() @ desired
    obj.data.transform(calibration)
    recalculate_normals(obj.data)
    obj["primary_grip_local"]=[0,0,0]
    obj["secondary_grip_local"]=list(calibration @ Vector((0,0,.75)))
    obj["head_center_local"]=list(calibration @ Vector((0,0,1.87)))
    obj["weaponSlot"]="mainHand"
    obj["weaponKind"]="staff"
    obj["socket"]="socket_hand_R"
    constraint=obj.constraints.new("COPY_TRANSFORMS")
    constraint.name="Preview hand socket"
    constraint.target=socket_object
    obj.matrix_world=socket
    return constraint


def audit_mesh(obj, rig):
    mesh=obj.data
    mesh.calc_loop_triangles()
    edges=Counter()
    for face in mesh.polygons:
        ids=list(face.vertices)
        edges.update(tuple(sorted((a,b))) for a,b in zip(ids,ids[1:]+ids[:1]))
    influences=[len([g for g in v.groups if g.weight>1e-6]) for v in mesh.vertices]
    finite=all(math.isfinite(n) for v in mesh.vertices for n in v.co)
    bad=sum(t.area<1e-12 for t in mesh.loop_triangles)
    report={"triangles":len(mesh.loop_triangles),"vertices":len(mesh.vertices),"materials":len(mesh.materials),
        "boundary_edges":sum(n==1 for n in edges.values()),"nonmanifold_edges":sum(n>2 for n in edges.values()),
        "degenerate_triangles":bad,"finite_coordinates":finite,
        "max_influences":max(influences,default=0),"unweighted_vertices":sum(n==0 for n in influences) if obj["slot"]!="weapon" else 0}
    if not finite or bad or report["nonmanifold_edges"] or report["boundary_edges"] or report["max_influences"]>4 or report["unweighted_vertices"]:
        raise ValueError(f"Runtime geometry rejected: {obj.name}: {report}")
    return report


def export_glb(path, objects, animations):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.hide_viewport=False
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,
        export_animations=animations,export_skins=True,export_morph=False,export_extras=True,
        export_yup=True,export_apply=False,export_draco_mesh_compression_enable=False,
        export_force_sampling=False,
        export_tangents=True,
        export_animation_mode="ACTIONS",export_nla_strips=False,export_anim_single_armature=True)


def bake_cached(obj, sources, output, lod, slot):
    """Reuse a verified atlas only when geometry, paint and baker inputs match."""
    from bake_atlas import bake_module_atlas
    resolution=2048 if slot=="body" and lod==0 else 512 if lod==2 else 1024
    material_names=sorted({m.name for m in obj.data.materials} | {m.name for source in sources for m in source.data.materials})
    paint_files=sorted(p for p in (ROOT/"textures/source").glob("*.png") if any(p.name.startswith(name.removeprefix("proof.")+"_") for name in material_names))
    digest=hashlib.sha256()
    digest.update(obj["source_records"].encode())
    digest.update(json.dumps(sorted({source["source_sha256"] for source in sources})).encode())
    digest.update(json.dumps({"resolution":resolution,"slot":slot,"lod":lod,"groups":[g.name for g in obj.vertex_groups]}).encode())
    for script in ("rig_character.py","bake_atlas.py","build_proof.py"):
        digest.update((ROOT/"tools"/script).read_bytes())
    for path in paint_files:
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    key=digest.hexdigest()
    def geometry_digest(mesh):
        value={"vertices":[[list(v.co),[(g.group,g.weight) for g in v.groups]] for v in mesh.vertices],
            "faces":[list(p.vertices) for p in mesh.polygons]}
        return hashlib.sha256(json.dumps(value,separators=(",",":")).encode()).hexdigest()
    expected_geometry=geometry_digest(obj.data)
    cache=output/"atlas_cache"
    cache.mkdir(exist_ok=True)
    cache_path=cache/f"{slot}_lod{lod}_{key}.blend"
    metadata_path=cache_path.with_suffix(".json")
    if cache_path.exists() and metadata_path.exists():
        metadata=json.loads(metadata_path.read_text())
        if hashlib.sha256(cache_path.read_bytes()).hexdigest()==metadata.get("cache_sha256") and all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==metadata["hashes"][c] for c,p in metadata["textures"].items()):
            with bpy.data.libraries.load(str(cache_path),link=False) as (data_from,data_to):
                data_to.meshes=data_from.meshes
            if len(data_to.meshes)!=1 or geometry_digest(data_to.meshes[0])!=expected_geometry:
                raise ValueError("Invalid atlas geometry cache")
            obj.data=data_to.meshes[0]
            obj["atlas_cache_sha256"]=key
            print(f"ATLAS_CACHE_HIT {slot} LOD{lod}",flush=True)
            return metadata["textures"]
    paths=bake_module_atlas(obj,f"{slot}_lod{lod}",output/"textures",resolution=resolution,high_sources=sources,
        transfer_surface_channels=slot=="tabard" or (lod>0 and slot!="body"))
    # Store the datablock only: rest pose, actions and bones are never cache inputs.
    bpy.data.libraries.write(str(cache_path),{obj.data},fake_user=True,compress=True)
    if geometry_digest(obj.data)!=expected_geometry:
        raise ValueError("Atlas bake unexpectedly changed geometry or weights")
    metadata_path.write_text(json.dumps({"key":key,"cache_sha256":hashlib.sha256(cache_path.read_bytes()).hexdigest(),"textures":paths,"hashes":{c:hashlib.sha256(Path(p).read_bytes()).hexdigest() for c,p in paths.items()}},indent=2)+"\n")
    obj["atlas_cache_sha256"]=key
    return paths


def archive_runtime_meshes(modules, destination):
    """Write the actual exported mesh coordinates, topology, UVs and weights."""
    records=[]
    for lod,objects in modules.items():
        for obj in objects:
            mesh=obj.data
            uv=mesh.uv_layers.active
            records.append({"lod":lod,"slot":obj["slot"],"object":obj.name,
                "vertices":[{"id":v.index,"co":list(v.co),"weights":{obj.vertex_groups[g.group].name:g.weight for g in v.groups}} for v in mesh.vertices],
                "faces":[{"id":p.index,"vertices":list(p.vertices),"uv":[list(uv.data[i].uv) for i in p.loop_indices],"material":p.material_index} for p in mesh.polygons],
                "materials":[m.name for m in mesh.materials],"source_records":json.loads(obj["source_records"])})
    with gzip.open(destination,"wt",encoding="utf-8") as stream:
        json.dump({"coordinates":"Blender Z-up; weapon vertices in socket-local frame","meshes":records},stream,separators=(",",":"))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--lods",default="0")
    parser.add_argument("--bake",action="store_true")
    parser.add_argument("--export",action="store_true")
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--preflight",action="store_true",help="Measure all requested geometry without replacing staged exports or reports")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_data=json.loads((ROOT/"source/scene.json").read_text())
    bind_scene=dict(scene_data,comparison_pose={})
    control,_=authored.load_sources(scene_data=bind_scene)
    rig=import_contract_rig(REPO/"public/assets/models/chr_civic_ember_arcanist_t1_m.glb")
    authored.setup_review(scene_data)
    output=ROOT/"runtime"
    output.mkdir(exist_ok=True)
    report={"status":"staged", "created_at":datetime.now(timezone.utc).isoformat(),"rig_source_sha256":rig["source_sha256"],"animations":sorted(CLIPS),"lods":{},"lod2_omitted_details":sorted(LOD2_OMIT)}
    all_modules={}
    controls={slot:[o for o in control.all_objects if o.type=="MESH" and source_slot(o)==slot] for slot in SLOTS}
    for lod in [int(value) for value in args.lods.split(",")]:
        collection=bpy.data.collections.new(f"RUNTIME_LOD{lod}")
        bpy.context.scene.collection.children.link(collection)
        groups={slot:[] for slot in SLOTS}
        for source in list(control.all_objects):
            if source.type=="MESH" and source["source_part"] not in BAKED_CLOTH_DETAILS and not(lod==2 and source["source_part"] in LOD2_OMIT):
                obj=evaluate_runtime_part(source,collection,rig,lod)
                groups[obj["slot"]].append(obj)
        lod_report={}
        modules=[]
        for slot,objects in groups.items():
            if not objects:
                raise ValueError(f"Missing module {slot}")
            obj=join_slot(objects,slot,lod)
            if slot=="tabard":
                records=json.loads(obj["source_records"])
                for source in controls[slot]:
                    if source["source_part"] in BAKED_CLOTH_DETAILS:
                        records.append({"file":source["source_file"],"part":source["source_part"],
                            "sha256":source["source_sha256"],"representation":"baked_surface",
                            "finishing":[{"type":m.type,**({"level":m.levels} if m.type=="SUBSURF" else {"segments":m.segments} if m.type=="BEVEL" else {})} for m in source.modifiers]})
                obj["source_records"]=json.dumps(records)
                obj["cloth_details"]="Modeled source cross and hem transferred to cloth PBR maps for consistent deformation"
            modules.append(obj)
            audit=audit_mesh(obj,rig)
            audit["source_records"]=json.loads(obj["source_records"])
            if slot=="body" and audit["triangles"]>45000:
                raise ValueError(f"Body exceeds 45k triangle budget: {audit['triangles']}")
            if slot not in {"body","weapon"} and audit["triangles"]>14000:
                raise ValueError(f"{slot} exceeds per-slot triangle budget: {audit['triangles']}")
            lod_report[slot]=audit
        total=sum(item["triangles"] for item in lod_report.values())
        limit={0:120000,1:60000,2:30000}[lod]
        print(f"LOD_GEOMETRY {lod} {total} "+json.dumps({s:r["triangles"] for s,r in lod_report.items()}),flush=True)
        if total>limit:
            raise ValueError(f"LOD{lod} exceeds equipped triangle budget {total}>{limit}")
        report["lods"][str(lod)]={"modules":lod_report,"total_triangles":total,"draw_calls":sum(len(obj.data.materials) for obj in modules)}
        all_modules[lod]=modules
    if args.preflight:
        (output/"preflight_report.json").write_text(json.dumps(report,indent=2)+"\n")
        print("RUNTIME_PREFLIGHT_COMPLETE",flush=True)
        return
    for lod,modules in all_modules.items():
        for obj in modules:
            slot=obj["slot"]
            audit=report["lods"][str(lod)]["modules"][slot]
            rig.data.pose_position="REST"
            if args.bake:
                audit["textures"]=bake_cached(obj,controls[slot],output,lod,slot)
                audit["materials"]=len(obj.data.materials)
                audit["surface_channel_transfer"]=slot=="tabard" or (lod>0 and slot!="body")
            if slot=="weapon":
                calibrate_weapon(obj,rig)
        report["lods"][str(lod)]["draw_calls"]=sum(len(obj.data.materials) for obj in modules)
        if args.bake and report["lods"][str(lod)]["draw_calls"]>16:
            raise ValueError("Equipped draw-call budget exceeded")
    if (ROOT/"tools/correct_animation.py").exists():
        from correct_animation import apply_animation_corrections
        report["animation_corrections"]=apply_animation_corrections(rig,next(o for o in all_modules[min(all_modules)] if o["slot"]=="weapon"))
    from tessellate_runtime import prepare_tangents
    report["tessellation_tool_sha256"]=hashlib.sha256((ROOT/"tools/tessellate_runtime.py").read_bytes()).hexdigest()
    for lod,modules in all_modules.items():
        for obj in modules:
            slot=obj["slot"]
            audit=report["lods"][str(lod)]["modules"][slot]
            audit["tessellation"]=prepare_tangents(obj)
            weapon_constraint=obj.constraints.get("Preview hand socket")
            if args.export:
                filename=("chr_civic_ember_arcanist_t1_m" if slot=="body" else "wep_civic_ember_arcanist_ember_staff" if slot=="weapon" else f"arm_civic_ember_arcanist_{slot}_t1_m")+("" if lod==0 else f"_lod{lod}")+".glb"
                path=output/filename
                rig.data.pose_position="POSE"
                if rig.animation_data:
                    rig.animation_data.action=None
                for bone in rig.pose.bones:
                    bone.matrix_basis=Matrix.Identity(4)
                bpy.context.scene.frame_set(1)
                bpy.context.view_layer.update()
                if weapon_constraint:
                    weapon_constraint.mute=True
                    obj.matrix_world=Matrix.Identity(4)
                export_objects=[obj] if slot=="weapon" else [rig,obj]+([bpy.data.objects[name] for name in json.loads(rig["socket_objects"])] if slot=="body" else [])
                export_glb(path,export_objects,slot=="body")
                if weapon_constraint:
                    weapon_constraint.mute=False
                audit["model"]=filename
                audit["bytes"]=path.stat().st_size
                audit["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
        collection=bpy.data.collections[f"RUNTIME_LOD{lod}"]
        collection.hide_render=lod!=0
        collection.hide_viewport=lod!=0
    control.hide_render=True
    control.hide_viewport=True
    rig.data.pose_position="POSE"
    bpy.context.scene.frame_set(1)
    # Source cage master stays separate until the bound/textured revision passes.
    if args.bake:
        bpy.ops.file.pack_all()
    archive_runtime_meshes(all_modules,output/"evaluated_lods.json.gz")
    report["evaluated_mesh_archive_sha256"]=hashlib.sha256((output/"evaluated_lods.json.gz").read_bytes()).hexdigest()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/("ember_arcanist_game_master.blend" if args.bake and args.export else "ember_arcanist_rigged_study.blend")),compress=True)
    pending=output/"runtime_report.pending.json"
    pending.write_text(json.dumps(report,indent=2)+"\n")
    pending.replace(output/"runtime_report.json")
    if args.render:
        authored.render_views(scene_data,bpy.data.collections["RUNTIME_LOD0"],["full_front","full_three_quarter"],["material"],output_prefix="rig_")
    print("RUNTIME_STAGE_COMPLETE "+json.dumps({lod:data["total_triangles"] for lod,data in report["lods"].items()}))


if __name__=="__main__":
    main()
