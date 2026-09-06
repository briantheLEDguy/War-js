"""Blender regression probe for immutable body/hammer sharing in the armor variant.

Writes only a temporary staging directory and review/shared_assets_probe.json.
The original master, archive, report and six runtime assets are hashed before/after.
"""
from pathlib import Path
import copy
import gzip
import json
import sys
import tempfile

import bpy
from mathutils import Matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import rig_character as backend


def must_reject(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError("Expected immutable shared asset guard to reject the operation")


def main():
    original=backend.SHARED_ROOT
    accepted=json.loads((original/"runtime/runtime_report.json").read_text())
    paths=[backend.SHARED_MASTER,original/"runtime/runtime_report.json",original/"runtime/evaluated_lods.json.gz"]
    paths += [original/"runtime"/accepted["lods"][str(lod)]["modules"][slot]["model"] for lod in (0,1,2) for slot in ("body","weapon")]
    before={str(p):backend.file_sha256(p) for p in paths}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig=backend.import_contract_rig(original/"runtime/chr_civic_battle_prelate_t1_m.glb")
    shared,report,expected,metadata=backend.load_shared_modules(rig,[0,1,2])
    for obj in shared.values():
        bpy.context.scene.collection.objects.link(obj)
    assert len([o for o in bpy.data.objects if o.type=="ARMATURE"])==1
    assert {a.name for a in bpy.data.actions}==backend.CLIPS
    assert {o.name for o in bpy.data.objects if o.type=="EMPTY"}=={"socket_hand_R","socket_hand_L","socket_back","socket_root"}
    backend.verify_contract_rig(rig)
    for (lod,slot),obj in shared.items():
        assert backend.mesh_archive_record(obj,lod)==expected[(lod,slot)]
        if slot=="body":
            assert obj.parent==rig
            assert [m.object for m in obj.modifiers if m.type=="ARMATURE"]==[rig]
            assert all(g.name in rig.data.bones for g in obj.vertex_groups)
        else:
            assert obj.parent is None and list(obj["primary_grip_local"])==[0,0,0]
            assert len(obj.constraints)==1 and obj.constraints[0].target==bpy.data.objects["socket_hand_R"]
            must_reject(lambda:backend.calibrate_weapon(obj,rig))
        must_reject(lambda:backend.bake_cached(obj,[],ROOT/"runtime",lod,slot))
        must_reject(lambda:backend.export_glb(ROOT/"runtime/should_not_exist.glb",[obj],False))
        must_reject(lambda:backend.armor_filename(slot,lod))
    names={backend.armor_filename(slot,lod) for lod in (0,1,2) for slot in backend.SLOTS if slot not in backend.SHARED_SLOTS}
    assert len(names)==27 and all("_novitiate_m" in name for name in names)
    badge_path=ROOT/"source/faith_badge.json"
    controls,_=backend.authored.load_sources(ROOT,{badge_path.name:badge_path.read_bytes()},{"comparison_pose":{}})
    badge=next(o for o in controls.all_objects if o.type=="MESH" and o["source_part"]=="novitiate_small_faith_badge")
    assert backend.source_slot(badge)=="chest"
    badge_policy={}
    for lod in (0,1,2):
        target=bpy.data.objects.new(f"probe.badge_provenance_lod{lod}",None)
        target["source_records"]="[]"
        backend.record_baked_surfaces(target,[badge],"chest",lod)
        entries=json.loads(target["source_records"])
        assert bool(entries)==(lod>0)
        assert (badge["source_part"] in backend.baked_surface_parts("chest",lod))==(lod>0)
        if lod>0:
            assert entries[0]["part"]==badge["source_part"] and entries[0]["representation"]=="baked_surface"
            assert entries[0]["sha256"]==backend.file_sha256(badge_path)
        badge_policy[str(lod)]={"modeled_geometry":lod==0,"retained_high_source":True,"baked_provenance":entries}
        bpy.data.objects.remove(target)
    # A changed pose moves attachments but cannot change local mesh coordinates.
    rig.data.pose_position="POSE"
    rig.pose.bones["hand_R"].rotation_mode="QUATERNION"
    rig.pose.bones["hand_R"].rotation_quaternion=(.98,.1,.1,.1)
    bpy.context.view_layer.update()
    for key,obj in shared.items():
        assert backend.mesh_archive_record(obj,key[0])==expected[key]
    for bone in rig.pose.bones:
        bone.matrix_basis=Matrix.Identity(4)
    temp_parent=(ROOT/"tmp").resolve()
    assert temp_parent.parent==ROOT.resolve()
    temp_parent.mkdir(exist_ok=True)
    copied={}
    with tempfile.TemporaryDirectory(prefix="shared-assets-",dir=temp_parent) as temporary:
        task_root=Path(temporary).resolve()
        # Validate the absolute deletion scope before TemporaryDirectory cleanup.
        assert task_root.parent==temp_parent and task_root.is_relative_to(ROOT.resolve())
        backend.ROOT=task_root
        output=task_root/"runtime"
        output.mkdir()
        try:
            for lod,slot in shared:
                audit=copy.deepcopy(report["lods"][str(lod)]["modules"][slot])
                backend.stage_shared_glb(audit,output)
                destination=output/audit["model"]
                stat=destination.stat()
                backend.stage_shared_glb(audit,output)
                assert destination.stat().st_mtime_ns==stat.st_mtime_ns
                assert backend.file_sha256(destination)==audit["sha256"]
                copied[audit["model"]]=audit["sha256"]
                broken=dict(audit,sha256="0"*64)
                must_reject(lambda:backend.stage_shared_glb(broken,output))
                assert backend.file_sha256(destination)==audit["sha256"]
            archive=output/"evaluated_lods.json.gz"
            backend.archive_runtime_meshes({lod:[shared[(lod,s)] for s in ("body","weapon")] for lod in (0,1,2)},archive)
            with gzip.open(archive,"rt",encoding="utf-8") as stream:
                actual=json.load(stream)
            assert len(actual["meshes"])==6
            assert all(mesh==expected[(mesh["lod"],mesh["slot"])] for mesh in actual["meshes"])
        finally:
            backend.ROOT=ROOT
    assert {str(p):backend.file_sha256(p) for p in paths}==before
    result={"status":"passed","shared_archive_records_exact":6,"byte_copied_glbs_exact":copied,
        "accepted_inputs_unchanged":before,"duplicate_rigs":0,"canonical_actions":sorted(backend.CLIPS),
        "new_armor_filenames":sorted(names),"guards_verified":["no_shared_bake","no_shared_export","no_hammer_recalibration","copy_hash_mismatch_rejected","idempotent_copy"],
        "shared_metadata":metadata,"badge_lod_policy":badge_policy}
    (ROOT/"review/shared_assets_probe.json").write_text(json.dumps(result,indent=2)+"\n")
    print("SHARED_ASSETS_PROBE_PASSED "+json.dumps({"shared_meshes":6,"exact_glbs":len(copied),"new_armor_filenames":len(names)}),flush=True)


if __name__=="__main__":
    main()
