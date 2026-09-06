"""Compare Novitiate master corrections with the unchanged accepted body clips."""
from pathlib import Path
import json
import sys

import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import rig_character as backend
import correct_animation as correction


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig=backend.import_contract_rig(backend.SHARED_ROOT/"runtime/chr_civic_battle_prelate_t1_m.glb")
    shared,_,expected,_=backend.load_shared_modules(rig,[0])
    for obj in shared.values():
        bpy.context.scene.collection.objects.link(obj)
    path=ROOT/"source/feet.json"
    control,_=backend.authored.load_sources(ROOT,{path.name:path.read_bytes()},{"comparison_pose":{}})
    runtime=bpy.data.collections.new("probe.runtime_feet")
    bpy.context.scene.collection.children.link(runtime)
    parts=[backend.evaluate_runtime_part(obj,runtime,rig,0) for obj in control.all_objects if obj.type=="MESH"]
    boots=backend.join_slot(parts,"feet",0)
    backend.audit_mesh(boots,rig)
    result=correction.apply_animation_corrections(rig,shared[(0,"weapon")])
    reuse=backend.reuse_accepted_action_bank(rig)
    active_actions={name:bpy.data.actions[name] for name in backend.CLIPS}
    with bpy.data.libraries.load(str(backend.SHARED_MASTER),link=False) as (data_from,data_to):
        data_to.actions=sorted(backend.CLIPS)
    differences={}
    exact={}
    for name,accepted in zip(sorted(backend.CLIPS),data_to.actions):
        current=active_actions[name]
        exact[name]=correction._curve_digest(current,[])==correction._curve_digest(accepted,[])
        if not exact[name]:
            old={(c.data_path,c.array_index):c for c in correction._curves(accepted)}
            new={(c.data_path,c.array_index):c for c in correction._curves(current)}
            changed=[]
            assert set(old)==set(new)
            for key in old:
                a,b=old[key],new[key]
                if len(a.keyframe_points)!=len(b.keyframe_points):
                    changed.append({"path":key[0],"index":key[1],"key_counts":[len(a.keyframe_points),len(b.keyframe_points)]})
                    continue
                maximum=max((abs(a.evaluate(p.co.x)-b.evaluate(p.co.x)) for p in a.keyframe_points),default=0)
                if maximum>1e-8:
                    changed.append({"path":key[0],"index":key[1],"max_key_value_delta":maximum})
            differences[name]=changed
    backend.verify_contract_rig(rig)
    for key,obj in shared.items():
        assert backend.mesh_archive_record(obj,key[0])==expected[key]
    report={"status":"passed" if all(exact.values()) else "action_difference_requires_review",
        "feet_source_sha256":backend.file_sha256(path),"canonical_rest_unchanged":True,
        "shared_meshes_unchanged":True,"exact_action_curve_matches":exact,"immutable_animation_reuse":reuse,
        "action_differences":differences,"correction_report":result,
        "scope":"Fresh canonical corrections in memory compared with actions from accepted master; no GLB re-export."}
    (ROOT/"review/shared_animation_probe.json").write_text(json.dumps(report,indent=2)+"\n")
    print("SHARED_ANIMATION_PROBE "+json.dumps({"status":report["status"],"exact":exact,"differences":differences}),flush=True)


if __name__=="__main__":
    main()
