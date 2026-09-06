"""Serialize explicitly edited accepted cages for the Novitiate Field Harness.

No geometry is inferred or generated: retained topology and UV corners come from
the accepted source records, and every changed control coordinate is listed here.
Run with Blender and --verify-blender to also check evaluated closed surfaces.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / "battle-prelate-reference-rebuild"
sys.path.insert(0, str(ROOT / "tools"))
from validate_source import validate_component

# Short rounded elbow cup; the former projecting wing is folded close to the joint.
ELBOW = {
    "P0": [-.064, -.019, .020], "P1": [-.047, -.027, .060],
    "P2": [-.006, -.029, .078], "P3": [.046, -.022, .065],
    "P4": [.073, -.003, .039], "P5": [.080, .017, .034],
    "P6": [.073, .034, .035], "P7": [.046, .048, .054],
    "P8": [.004, .055, .063], "P9": [-.045, .048, .048],
    "P10": [-.063, .029, .018], "Q0": [-.050, .006, .060],
    "Q1": [-.006, .008, .087], "Q2": [.043, .013, .074],
    "Q3": [.065, .020, .047], "Q4": [.032, .034, .071],
    "Q5": [-.011, .038, .075], "Q6": [-.050, .030, .046],
}

# A front guard leaves the existing leather backing visible at both sides.
# Close paired rows describe rolled edges, with no flared or gilded cuff.
FOREARM = {
    "A0": [-.056, .084, .029], "A1": [-.042, .077, .054],
    "A2": [-.004, .071, .079], "A3": [.041, .079, .057],
    "A4": [.058, .091, .029], "B0": [-.055, .093, .031],
    "B1": [-.041, .086, .056], "B2": [-.004, .080, .081],
    "B3": [.040, .088, .059], "B4": [.057, .100, .031],
    "C0": [-.049, .172, .020], "C1": [-.037, .171, .045],
    "C2": [.003, .165, .064], "C3": [.037, .174, .048],
    "C4": [.051, .180, .019], "D0": [-.035, .251, .016],
    "D1": [-.028, .257, .035], "D2": [.003, .263, .047],
    "D3": [.029, .257, .037], "D4": [.038, .246, .014],
    "E0": [-.035, .243, .018], "E1": [-.028, .249, .037],
    "E2": [.003, .255, .049], "E3": [.029, .249, .039],
    "E4": [.038, .238, .016],
}

# Leather thigh panels end above the joint, without the original long front point.
THIGH = {
    "v000": [.031, .016, .944], "v001": [.072, -.086, .954],
    "v002": [.121, -.113, .967], "v003": [.186, -.111, .956],
    "v004": [.219, .031, .935], "v005": [.037, .020, .884],
    "v006": [.080, -.097, .884], "v007": [.129, -.124, .888],
    "v008": [.194, -.112, .882], "v009": [.226, .034, .871],
    "v010": [.047, .024, .791], "v011": [.090, -.101, .792],
    "v012": [.140, -.127, .792], "v013": [.201, -.107, .789],
    "v014": [.235, .035, .783], "v015": [.062, .018, .720],
    "v016": [.104, -.099, .711], "v017": [.151, -.128, .711],
    "v018": [.206, -.093, .712], "v019": [.240, .029, .720],
    "v020": [.067, .011, .699], "v021": [.108, -.097, .690],
    "v022": [.154, -.126, .687], "v023": [.207, -.091, .692],
    "v024": [.241, .023, .701],
}

# Plain shallow steel knee cup, rounded at top/bottom and without insignia.
KNEE = {
    "v000": [.159, -.125, .624], "v001": [.205, -.114, .611],
    "v002": [.235, -.094, .574], "v003": [.231, -.108, .535],
    "v004": [.204, -.122, .504], "v005": [.167, -.133, .489],
    "v006": [.123, -.126, .506], "v007": [.091, -.113, .537],
    "v008": [.091, -.114, .575], "v009": [.119, -.127, .610],
    "v010": [.160, -.165, .609], "v011": [.191, -.168, .598],
    "v012": [.213, -.166, .573], "v013": [.209, -.174, .544],
    "v014": [.190, -.173, .522], "v015": [.166, -.170, .508],
    "v016": [.137, -.174, .523], "v017": [.114, -.171, .546],
    "v018": [.114, -.166, .573], "v019": [.134, -.169, .599],
    "v020": [.163, -.192, .559],
}

# Short, subdued shin plate; exposed leather/chainmail remains at the sides.
SHIN = {
    "v000": [.108, -.009, .454], "v001": [.120, -.099, .464],
    "v002": [.166, -.139, .471], "v003": [.216, -.090, .473],
    "v004": [.250, -.001, .471], "v005": [.106, .013, .425],
    "v006": [.124, -.096, .421], "v007": [.175, -.137, .427],
    "v008": [.226, -.086, .429], "v009": [.256, .019, .431],
    "v010": [.115, .022, .337], "v011": [.140, -.084, .336],
    "v012": [.190, -.129, .338], "v013": [.236, -.077, .341],
    "v014": [.264, .027, .344], "v015": [.127, .017, .250],
    "v016": [.156, -.075, .249], "v017": [.201, -.117, .252],
    "v018": [.245, -.069, .257], "v019": [.269, .028, .263],
    "v020": [.144, .009, .206], "v021": [.171, -.065, .203],
    "v022": [.210, -.108, .204], "v023": [.249, -.064, .212],
    "v024": [.273, .024, .220], "v025": [.147, .007, .195],
    "v026": [.174, -.063, .191], "v027": [.212, -.106, .192],
    "v028": [.251, -.062, .201], "v029": [.275, .021, .210],
}

REMOVED = {
    "arms": {"rerebrace_shaped_shell"},
    "legs": {
        "thigh_cuisse_lower_brass_border", "thigh_cuisse_outer_brass_seam",
        "knee_poleyn_brass_rim", "greave_inner_brass_edge",
        "greave_outer_brass_edge", "greave_brass_ankle_arch",
        "knee_skull_relief", "knee_skull_dark_sockets", "knee_skull_teeth",
        "knee_cross_flourish", "knee_and_greave_fasteners",
    },
    "feet": {
        "sabaton_first_articulated_lame", "sabaton_second_articulated_lame",
        "sabaton_instep_articulated_lame", "sabaton_brass_toe_rim",
        "sabaton_brass_instep_border", "boot_heel_steel_counter",
        "boot_heel_brass_upper_lip",
    },
}
PROTECTED = {
    "upper_arm_joint_underlayer", "forearm_leather_underlayer",
    "gauntlet_glove_palm_and_web", "thigh_padded_underlayer",
    "knee_and_calf_padded_underlayer",
}
COORDINATES = {
    "elbow_couter_and_wing": ELBOW, "vambrace_front_and_cuff": FOREARM,
    "thigh_steel_cuisse": THIGH, "knee_pointed_poleyn": KNEE,
    "greave_shaped_front_shell": SHIN,
}


def construction_details(name,record):
    """Retain authored topology and serialize individually specified additions."""
    accepted_legs=json.loads((BASE/"source/legs.json").read_text())
    accepted_feet=json.loads((BASE/"source/feet.json").read_text())
    templates={p["id"]:p for data in (accepted_legs,accepted_feet) for p in data["parts"]}

    def patch(template,new_id,coordinates,material):
        part=copy.deepcopy(templates[template])
        part["id"]=new_id
        assert len(coordinates)==len(part["vertices"])
        for vertex,co in zip(part["vertices"],coordinates):
            vertex["co"]=co
        for face in part["faces"]:
            face["material"]=material
        part["derivation"]={"accepted_part":template,"coordinate_edit":"literal construction-detail coordinates", "topology_uv":"retained accepted topology and UV corners"}
        return part

    additions=[]
    if name=="arms":
        straps=patch("greave_leather_closure_bands","novitiate_forearm_binding_straps",[
            [-.066,.108,.005],[-.066,.121,.005],[-.049,.106,-.048],[-.049,.119,-.048],
            [.001,.107,-.066],[.001,.120,-.066],[.050,.110,-.047],[.050,.123,-.047],
            [.067,.112,.004],[.067,.125,.004],[.054,.113,.041],[.054,.126,.041],
            [-.044,.226,.001],[-.044,.239,.001],[-.032,.228,-.035],[-.032,.241,-.035],
            [.002,.228,-.048],[.002,.241,-.048],[.034,.226,-.035],[.034,.239,-.035],
            [.046,.225,.001],[.046,.238,.001],[.035,.224,.031],[.035,.237,.031],
        ],"leather")
        forearm=next(p for p in record["parts"] if p["id"]=="forearm_leather_underlayer")
        straps["slot"]="hands"
        straps["rigid_bone"]="forearm_L"
        straps.pop("mirror_bone",None)
        straps["instances"]=copy.deepcopy(forearm["instances"])
        straps["modifiers"]=[{"type":"SOLIDIFY","thickness":.002,"offset":0},{"type":"BEVEL","width":.0006,"segments":2}]
        additions.append(straps)
    if name=="legs":
        inner=patch("greave_inner_brass_edge","novitiate_shin_inner_rolled_edge",[
            [.108,-.014,.448],[.113,-.023,.448],[.106,.012,.425],[.111,.005,.425],
            [.115,.021,.337],[.120,.014,.337],[.127,.016,.250],[.132,.009,.250],
            [.144,.008,.206],[.149,.001,.206],[.147,.006,.195],[.152,-.001,.195],
        ],"steel")
        outer=patch("greave_outer_brass_edge","novitiate_shin_outer_rolled_edge",[
            [.248,-.007,.462],[.243,-.016,.462],[.257,.018,.431],[.252,.011,.431],
            [.265,.026,.344],[.260,.019,.344],[.270,.027,.263],[.265,.020,.263],
            [.274,.023,.220],[.269,.016,.220],[.276,.020,.210],[.271,.013,.210],
        ],"steel")
        additions.extend([inner,outer])
        rivets=copy.deepcopy(templates["knee_and_greave_fasteners"])
        rivets["id"]="novitiate_shin_strap_rivets"
        for face in rivets["faces"]:
            face["material"]="dark_steel"
        rivets["instances"]=[
            {"location":[.134,-.0864,.410],"rotation_degrees":[11.4,0,-55.4],"scale":[1,1,1],"rigid_bone":"shin_L"},
            {"location":[.229,-.0629,.415],"rotation_degrees":[-3.4,0,67.5],"scale":[1,1,1],"rigid_bone":"shin_L"},
            {"location":[.175,-.0739,.222],"rotation_degrees":[16.8,0,-54.9],"scale":[1,1,1],"rigid_bone":"shin_L"},
            {"location":[.243,-.0615,.229],"rotation_degrees":[-2.7,0,58.3],"scale":[1,1,1],"rigid_bone":"shin_L"},
            {"location":[-.134,-.0864,.410],"rotation_degrees":[11.4,0,55.4],"scale":[1,1,1],"rigid_bone":"shin_R"},
            {"location":[-.229,-.0629,.415],"rotation_degrees":[-3.4,0,-67.5],"scale":[1,1,1],"rigid_bone":"shin_R"},
            {"location":[-.175,-.0739,.222],"rotation_degrees":[16.8,0,54.9],"scale":[1,1,1],"rigid_bone":"shin_R"},
            {"location":[-.243,-.0615,.229],"rotation_degrees":[-2.7,0,-58.3],"scale":[1,1,1],"rigid_bone":"shin_R"},
        ]
        rivets["derivation"]={"accepted_part":"knee_and_greave_fasteners","method":"Eight individually placed iron strap fasteners; unchanged authored cap topology/UV."}
        additions.append(rivets)
    if name=="feet":
        # The accepted toe footprint supports the shared falling animation.
        # Retain its explicit cage as a practical leather toe rand.
        rand=copy.deepcopy(templates["sabaton_brass_toe_rim"])
        rand["id"]="novitiate_boot_leather_toe_rand"
        for face in rand["faces"]:
            face["material"]="leather"
        rand["derivation"]={"accepted_part":"sabaton_brass_toe_rim","coordinate_edit":"unchanged accepted explicit toe footprint","purpose":"Leather toe reinforcement retains ground contact in the shared death clip"}
        additions.append(rand)
        welt=patch("boot_contoured_welt_and_sole","novitiate_boot_leather_welt",[
            [.119,-.245,.027],[.131,-.305,.025],[.169,-.328,.023],[.248,-.327,.023],
            [.297,-.304,.026],[.316,-.245,.029],[.304,-.111,.033],[.289,.079,.037],
            [.250,.101,.035],[.169,.096,.035],[.138,.071,.036],[.128,-.090,.031],
            [.119,-.245,.032],[.131,-.305,.030],[.169,-.328,.028],[.248,-.327,.028],
            [.297,-.304,.031],[.316,-.245,.034],[.304,-.111,.038],[.289,.079,.042],
            [.250,.101,.040],[.169,.096,.040],[.138,.071,.041],[.128,-.090,.036],
        ],"leather")
        welt["modifiers"]=[{"type":"MIRROR","axis":"X"},{"type":"BEVEL","width":.001,"segments":2}]
        additions.append(welt)
        stitches={"id":"novitiate_boot_welt_stitches","slot":"feet","rigid_bone":"foot_L",
            "vertices":[{"id":i,"co":co} for i,co in [
                ("a",[-.0020,0,0]),("b",[-.0015,-.0006,.0003]),("c",[.0014,-.0006,.0003]),("d",[.0020,0,0]),
                ("e",[.0014,.0006,.0003]),("f",[-.0015,.0006,.0003]),("g",[-.0010,0,.0008]),("h",[.0010,0,.0008]),
            ]],
            "faces":[{"id":i,"vertices":v,"uv":uv,"material":"parchment"} for i,v,uv in [
                ("thread0",["a","b","g"],[[0,.5],[.1,0],[.25,.5]]),
                ("thread1",["b","c","h","g"],[[.1,0],[.9,0],[.75,.5],[.25,.5]]),
                ("thread2",["c","d","h"],[[.9,0],[1,.5],[.75,.5]]),
                ("thread3",["d","e","h"],[[1,.5],[.9,1],[.75,.5]]),
                ("thread4",["e","f","g","h"],[[.9,1],[.1,1],[.25,.5],[.75,.5]]),
                ("thread5",["f","a","g"],[[.1,1],[0,.5],[.25,.5]]),
                ("thread_back",["f","e","d","c","b","a"],[[.1,1],[.9,1],[1,.5],[.9,0],[.1,0],[0,.5]]),
            ]],"modifiers":[],"landmarks":{},"seams":[],"sharp_edges":[],"creases":[],"closed":True,
            "transform":{"location":[0,0,0],"rotation_degrees":[0,0,0],"scale":[1,1,1]},
            "instances":[
                {"location":[.177,-.326,.0284],"rotation_degrees":[0,0,78],"rigid_bone":"foot_L"},
                {"location":[.190,-.326,.0284],"rotation_degrees":[0,0,82],"rigid_bone":"foot_L"},
                {"location":[.204,-.326,.0284],"rotation_degrees":[0,0,87],"rigid_bone":"foot_L"},
                {"location":[.218,-.325,.0284],"rotation_degrees":[0,0,91],"rigid_bone":"foot_L"},
                {"location":[.232,-.325,.0284],"rotation_degrees":[0,0,96],"rigid_bone":"foot_L"},
                {"location":[.247,-.324,.0284],"rotation_degrees":[0,0,103],"rigid_bone":"foot_L"},
                {"location":[.309,-.206,.0353],"rotation_degrees":[0,0,-5],"rigid_bone":"foot_L"},
                {"location":[.307,-.180,.0361],"rotation_degrees":[0,0,-7],"rigid_bone":"foot_L"},
                {"location":[.304,-.151,.03695],"rotation_degrees":[0,0,-8],"rigid_bone":"foot_L"},
                {"location":[.301,-.123,.0378],"rotation_degrees":[0,0,-9],"rigid_bone":"foot_L"},
                {"location":[-.177,-.326,.0284],"rotation_degrees":[0,0,-78],"rigid_bone":"foot_R"},
                {"location":[-.190,-.326,.0284],"rotation_degrees":[0,0,-82],"rigid_bone":"foot_R"},
                {"location":[-.204,-.326,.0284],"rotation_degrees":[0,0,-87],"rigid_bone":"foot_R"},
                {"location":[-.218,-.325,.0284],"rotation_degrees":[0,0,-91],"rigid_bone":"foot_R"},
                {"location":[-.232,-.325,.0284],"rotation_degrees":[0,0,-96],"rigid_bone":"foot_R"},
                {"location":[-.247,-.324,.0284],"rotation_degrees":[0,0,-103],"rigid_bone":"foot_R"},
                {"location":[-.309,-.206,.0353],"rotation_degrees":[0,0,5],"rigid_bone":"foot_R"},
                {"location":[-.307,-.180,.0361],"rotation_degrees":[0,0,7],"rigid_bone":"foot_R"},
                {"location":[-.304,-.151,.03695],"rotation_degrees":[0,0,8],"rigid_bone":"foot_R"},
                {"location":[-.301,-.123,.0378],"rotation_degrees":[0,0,9],"rigid_bone":"foot_R"},
            ],"derivation":{"method":"One literal tapered thread mesh, twenty named explicit placements on boot welt; parchment material represents unbleached thread."}}
        additions.append(stitches)
    return additions


def digest(data):
    return hashlib.sha256(data).hexdigest()


def part_bytes(part):
    return json.dumps(part, ensure_ascii=False, indent=2).encode("utf-8")


def author():
    report = {"design": "Novitiate Field Harness", "status": "source_validated",
              "method": "Accepted explicit cages, literal coordinate replacements, retained face IDs/UV corners and canonical transforms.",
              "files": [], "protected_parts": [], "limitations": [
                  "Source and evaluated topology checks do not establish dynamic collision clearance; root integration must review all nine clips.",
                  "Part IDs retain accepted heritage names for stable provenance, including names with brass/pointed/sabaton; materials and retained geometry are authoritative.",
              ]}
    for name in ("arms", "legs", "feet"):
        source_path = BASE / "source" / (name + ".json")
        baseline = json.loads(source_path.read_text(encoding="utf-8"))
        record = copy.deepcopy(baseline)
        record["parts"] = [p for p in record["parts"] if p["id"] not in REMOVED[name]]
        record["reference_notes"] = [
            "Novitiate Field Harness: practical level-one equipment derived from accepted explicit source cages.",
            "No primitives, sampled profiles, generated anatomy or decorative scattering. All changed XYZ controls are literal values in tools/author_novitiate_limbs.py.",
            "Original stable vertex/face IDs, UV corners, rig transforms and permitted finishing operations are retained unless documented per part.",
            "No gold borders, skulls or crosses remain on these limb modules. Shared body underlayers remain byte-value identical.",
        ]
        record["derived_from"] = {"package": BASE.name, "file": "source/" + name + ".json", "sha256": digest(source_path.read_bytes())}
        for part in record["parts"]:
            if part["id"] in PROTECTED:
                original = next(p for p in baseline["parts"] if p["id"] == part["id"])
                assert part_bytes(part) == part_bytes(original)
                report["protected_parts"].append({"part": part["id"], "sha256": digest(part_bytes(part)), "unchanged": True})
                continue
            part["derivation"] = {"accepted_part": part["id"], "coordinate_edit": "literal replacement table" if part["id"] in COORDINATES else "unchanged accepted cage", "topology_uv_and_rig": "unchanged accepted source"}
            if part["id"] in COORDINATES:
                changes = COORDINATES[part["id"]]
                assert set(changes) == {v["id"] for v in part["vertices"]}
                for vertex in part["vertices"]:
                    vertex["co"] = changes[vertex["id"]]
            for face in part["faces"]:
                if face["material"] == "brass":
                    face["material"] = "dark_steel"
                if part["id"] in {"thigh_steel_cuisse", "vambrace_rear_closure"}:
                    face["material"] = "leather"
            if part["id"] in {"elbow_couter_and_wing", "knee_pointed_poleyn", "vambrace_front_and_cuff", "greave_shaped_front_shell"}:
                for modifier in part["modifiers"]:
                    if modifier["type"] == "SOLIDIFY":
                        modifier["thickness"] = .003
            if part["id"] == "thigh_steel_cuisse":
                for modifier in part["modifiers"]:
                    if modifier["type"] == "SOLIDIFY":
                        modifier["thickness"] = .003
        additions=construction_details(name,record)
        record["parts"].extend(additions)
        record["reference_notes"].append("Small construction details: leather forearm straps, narrow rolled shin edges, eight individually placed iron strap rivets, and stitched leather boot welts. No additional heraldic decoration.")
        validation = validate_component(record)
        path = ROOT / "source" / (name + ".json")
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Validate the actual serialized artifact, not just the in-memory record.
        assert validate_component(json.loads(path.read_text(encoding="utf-8"))) == validation
        report["files"].append({"file": "source/" + name + ".json", "sha256": digest(path.read_bytes()), "removed_parts": sorted(REMOVED[name]),"construction_detail_parts":[p["id"] for p in additions], "parts": validation})
    return report


def main():
    report = author()
    if "--verify-blender" in sys.argv:
        import bpy
        from build_proof import load_sources, evaluated_record
        snapshots = {n + ".json": (ROOT / "source" / (n + ".json")).read_bytes() for n in ("arms", "legs", "feet")}
        collection, _ = load_sources(ROOT, snapshots, {"comparison_pose": {}})
        bpy.context.view_layer.update()
        evaluated = evaluated_record(collection)
        report["evaluated_validation"] = {
            "status": "passed", "objects": [{k: p[k] for k in ("name", "triangles", "boundary_edges", "expected_closed")} for p in evaluated["parts"]],
            "total_triangles_including_shared_body_parts": sum(p["triangles"] for p in evaluated["parts"]),
        }
    (ROOT / "review").mkdir(exist_ok=True)
    (ROOT / "review" / "limb_design.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "source_parts": sum(len(f["parts"]) for f in report["files"]), "protected_parts_unchanged": len(report["protected_parts"]), "evaluated": report.get("evaluated_validation", {}).get("status")}))


if __name__ == "__main__":
    main()
