"""Serialize literal fitted shirt, crotch and breeches control meshes.

Coordinates and topology are individually recorded. Bone matrices are placement
data only; they do not extract, sample or generate any body surface.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RIG = json.loads((ROOT / "source/rig_reference.dat").read_text())["bones"]


def mesh(name, vertices, faces, bone, modifiers, closed=False):
    points, uvs = [], {}
    for row in vertices.strip().splitlines():
        values = row.split()
        points.append({"id": values[0], "co": [float(v) for v in values[1:4]]})
        uvs[values[0]] = [float(v) for v in values[4:6]]
    polygons = []
    for row in faces.strip().splitlines():
        values = row.split()
        mat = values[-1][1:] if values[-1].startswith("@") else "leather"
        ids = values[1:-1] if values[-1].startswith("@") else values[1:]
        polygons.append({"id": values[0], "vertices": ids,
                         "uv": [uvs[v] for v in ids], "material": mat})
    return {"id": name, "vertices": points, "faces": polygons,
            "modifiers": modifiers, "closed": closed, "slot": "body", "rigid_bone": bone,
            "landmarks": {}, "seams": [], "sharp_edges": [], "creases": [],
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]}}


shirt = mesh("fitted_padded_torso_shirt", """
N0 0 -.053 1.606 .50 .99
N1 .036 -.044 1.606 .56 .99
N2 .056 -.003 1.612 .63 .99
N3 .036 .042 1.608 .77 .99
N4 0 .053 1.607 .88 .99
NC 0 0 1.596 .50 .97
K0 0 -.098 1.540 .50 .82
K1 .075 -.080 1.550 .56 .85
K2 .150 -.053 1.540 .63 .82
K3 .202 -.012 1.530 .69 .79
K4 .160 .067 1.548 .76 .84
K5 .082 .107 1.550 .82 .85
K6 0 .119 1.548 .88 .84
R0 0 -.117 1.480 .50 .64
R1 .083 -.119 1.478 .55 .635
R2 .156 -.096 1.477 .61 .633
R3 .196 -.051 1.475 .66 .627
R4 .202 .020 1.475 .71 .627
R5 .168 .087 1.477 .77 .633
R6 .092 .122 1.479 .82 .637
R7 0 .128 1.480 .88 .64
M0 0 -.113 1.397 .50 .41
M1 .084 -.115 1.405 .55 .43
M2 .164 -.090 1.409 .61 .44
M3 .201 -.037 1.405 .66 .43
M4 .204 .031 1.397 .71 .41
M5 .166 .087 1.392 .77 .39
M6 .089 .119 1.397 .82 .41
M7 0 .128 1.399 .88 .415
F0 0 -.100 1.298 .50 .13
F1 .078 -.107 1.301 .55 .14
F2 .150 -.091 1.307 .61 .155
F3 .190 -.040 1.309 .66 .16
F4 .192 .024 1.304 .71 .145
F5 .152 .079 1.299 .77 .13
F6 .084 .118 1.297 .82 .125
F7 0 .127 1.299 .88 .13
H0 0 -.099 1.281 .50 .08
H1 .077 -.105 1.283 .55 .085
H2 .148 -.089 1.288 .61 .10
H3 .187 -.038 1.291 .66 .108
H4 .190 .024 1.286 .71 .095
H5 .150 .078 1.282 .77 .082
H6 .083 .116 1.280 .82 .078
H7 0 .125 1.282 .88 .082
HC 0 .005 1.281 .69 .08
""", """
neck_closure01 N0 NC N1
neck_closure02 N1 NC N2
neck_closure03 N2 NC N3
neck_closure04 N3 NC N4
clavicle01 N0 K0 K1 N1
clavicle02 N1 K1 K2 N2
shoulder01 N2 K2 K3
shoulder02 N2 K3 K4 N3
trapezius01 N3 K4 K5 N4
trapezius02 N4 K5 K6
pectoral01 K0 R0 R1 K1
pectoral02 K1 R1 R2 K2
deltoid01 K2 R2 R3 K3
deltoid02 K3 R3 R4
deltoid03 K3 R4 R5 K4
scapula01 K4 R5 R6 K5
scapula02 K5 R6 R7 K6
thorax01 R0 M0 M1 R1
thorax02 R1 M1 M2 R2
thorax03 R2 M2 M3 R3
axilla01 R3 M3 M4 R4
latissimus01 R4 M4 M5 R5
latissimus02 R5 M5 M6 R6
back01 R6 M6 M7 R7
abdomen01 M0 F0 F1 M1
abdomen02 M1 F1 F2 M2
abdomen03 M2 F2 F3 M3
flank01 M3 F3 F4 M4
flank02 M4 F4 F5 M5
back02 M5 F5 F6 M6
back03 M6 F6 F7 M7
hem01 F0 H0 H1 F1
hem02 F1 H1 H2 F2
hem03 F2 H2 H3 F3
hem04 F3 H3 H4 F4
hem05 F4 H4 H5 F5
hem06 F5 H5 H6 F6
hem07 F6 H6 H7 F7
hidden_base01 H0 HC H1
hidden_base02 H1 HC H2
hidden_base03 H2 HC H3
hidden_base04 H3 HC H4
hidden_base05 H4 HC H5
hidden_base06 H5 HC H6
hidden_base07 H6 HC H7
""", "upper_chest", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 1}])
shirt["landmarks"] = {"neck_front": "N0", "shoulder_interface_left": "K3", "sternum": "R0", "abdomen_overlap": "H0"}
shirt["seams"] = [["N0", "N1"], ["N1", "N2"], ["N2", "N3"], ["N3", "N4"],
                   ["F0", "F1"], ["F1", "F2"], ["F2", "F3"], ["F3", "F4"],
                   ["F4", "F5"], ["F5", "F6"], ["F6", "F7"]]

hips = mesh("tailored_hip_and_crotch_breeches", """
T0 0 -.115 1.124 .50 .99
T1 .088 -.112 1.125 .55 .99
T2 .164 -.086 1.123 .61 .985
T3 .202 -.025 1.119 .67 .97
T4 .196 .054 1.120 .72 .973
T5 .141 .114 1.123 .78 .985
T6 .070 .128 1.125 .83 .99
T7 0 .129 1.124 .88 .99
TC 0 .003 1.122 .69 .98
M0 0 -.132 1.015 .50 .55
M1 .095 -.128 1.020 .55 .57
M2 .176 -.095 1.028 .61 .60
M3 .219 -.023 1.028 .67 .60
M4 .212 .057 1.025 .72 .59
M5 .145 .130 1.020 .78 .57
M6 .070 .137 1.020 .83 .57
M7 0 .137 1.016 .88 .55
CF 0 -.071 .889 .50 .04
CM 0 .012 .884 .69 .02
CB 0 .081 .896 .88 .07
L0 .027 -.048 .914 .51 .15
L1 .053 -.105 .935 .56 .23
L2 .133 -.108 .948 .61 .28
L3 .200 -.061 .967 .67 .35
L4 .215 .027 .973 .72 .38
L5 .165 .107 .955 .78 .31
L6 .078 .113 .934 .83 .23
L7 .023 .039 .913 .87 .15
LC .113 .005 .944 .70 .26
""", """
hidden_waist01 T0 T1 TC
hidden_waist02 T1 T2 TC
hidden_waist03 T2 T3 TC
hidden_waist04 T3 T4 TC
hidden_waist05 T4 T5 TC
hidden_waist06 T5 T6 TC
hidden_waist07 T6 T7 TC
hip01 T0 M0 M1 T1
hip02 T1 M1 M2 T2
hip03 T2 M2 M3 T3
hip04 T3 M3 M4 T4
hip05 T4 M4 M5 T5
hip06 T5 M5 M6 T6
hip07 T6 M6 M7 T7
front_rise M0 CF L0 L1 M1
front_thigh_root01 M1 L1 L2 M2
front_thigh_root02 M2 L2 L3 M3
outer_hip M3 L3 L4 M4
rear_thigh_root01 M4 L4 L5 M5
rear_thigh_root02 M5 L5 L6 M6
rear_rise M6 L6 L7 CB M7
crotch_front CF CM L0
crotch_rear CM CB L7
crotch_join CM L7 L0
hidden_leg01 L0 LC L1
hidden_leg02 L1 LC L2
hidden_leg03 L2 LC L3
hidden_leg04 L3 LC L4
hidden_leg05 L4 LC L5
hidden_leg06 L5 LC L6
hidden_leg07 L6 LC L7
hidden_leg08 L7 LC L0
""", "hips", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 1}])
hips["landmarks"] = {"waist_front": "T0", "crotch_lowest": "CM", "thigh_interface_left": "LC"}
hips["seams"] = [["M0", "CF"], ["CF", "CM"], ["CM", "CB"], ["CB", "M7"]]

thighs = mesh("fitted_padded_breeches_thighs", """
A0 -.080 -.020 .026 .02 .02
A1 -.045 -.020 .078 .15 .02
A2 .029 -.020 .084 .29 .02
A3 .075 -.020 .043 .43 .02
A4 .085 -.020 -.031 .57 .02
A5 .040 -.020 -.086 .71 .02
A6 -.030 -.020 -.092 .85 .02
A7 -.078 -.020 -.045 .98 .02
B0 -.085 .109 .024 .02 .29
B1 -.048 .113 .081 .15 .30
B2 .029 .117 .085 .29 .31
B3 .079 .122 .042 .43 .32
B4 .087 .117 -.030 .57 .31
B5 .044 .111 -.089 .71 .30
B6 -.034 .107 -.096 .85 .28
B7 -.083 .105 -.046 .98 .28
C0 -.066 .288 .019 .02 .67
C1 -.041 .294 .063 .15 .68
C2 .023 .299 .068 .29 .69
C3 .063 .298 .034 .43 .69
C4 .071 .290 -.024 .57 .67
C5 .036 .282 -.069 .71 .65
C6 -.026 .279 -.074 .85 .65
C7 -.065 .283 -.036 .98 .66
D0 -.052 .447 .015 .02 .99
D1 -.032 .449 .047 .15 .99
D2 .018 .452 .052 .29 .99
D3 .051 .451 .026 .43 .99
D4 .058 .446 -.018 .57 .99
D5 .028 .441 -.052 .71 .98
D6 -.021 .440 -.057 .85 .98
D7 -.052 .442 -.027 .98 .98
""", """
breeches01 A0 B0 B1 A1
breeches02 A1 B1 B2 A2
breeches03 A2 B2 B3 A3
breeches04 A3 B3 B4 A4
breeches05 A4 B4 B5 A5
breeches06 A5 B5 B6 A6
breeches07 A6 B6 B7 A7
breeches08 A7 B7 B0 A0
breeches09 B0 C0 C1 B1
breeches10 B1 C1 C2 B2
breeches11 B2 C2 C3 B3
breeches12 B3 C3 C4 B4
breeches13 B4 C4 C5 B5
breeches14 B5 C5 C6 B6
breeches15 B6 C6 C7 B7
breeches16 B7 C7 C0 B0
breeches17 C0 D0 D1 C1
breeches18 C1 D1 D2 C2
breeches19 C2 D2 D3 C3
breeches20 C3 D3 D4 C4
breeches21 C4 D4 D5 C5
breeches22 C5 D5 D6 C6
breeches23 C6 D6 D7 C7
breeches24 C7 D7 D0 C0
hidden_hip_end A7 A6 A5 A4 A3 A2 A1 A0
hidden_knee_end D0 D1 D2 D3 D4 D5 D6 D7
""", "thigh_L", [{"type": "SUBSURF", "levels": 1}], closed=True)
thighs["instances"] = [
    {"matrix": RIG["thigh_L"]["matrix"], "scale": [1, 1, 1], "rigid_bone": "thigh_L"},
    {"matrix": RIG["thigh_R"]["matrix"], "scale": [-1, 1, 1], "rigid_bone": "thigh_R"},
]
thighs["seams"] = [["A0", "B0"], ["B0", "C0"], ["C0", "D0"]]
thighs["landmarks"] = {"upper_outer_thigh": "A3", "knee_interface": "D2"}

# Fixed image-map placement records; no geometry or binding is changed here.
MAIL_UV = {
    "tailored_hip_and_crotch_breeches": {
        "scale": [52.0, 9.0], "offset": [-26.0, 0.0],
        "seam_corner_u": {},
    },
    "fitted_padded_breeches_thighs": {
        "scale": [18.0, 16.0], "offset": [0.0, 0.0],
        "seam_corner_u": {
            "breeches08": {2: 1.02, 3: 1.02},
            "breeches16": {2: 1.02, 3: 1.02},
            "breeches24": {2: 1.02, 3: 1.02},
        },
    },
}
for mesh_part in [hips, thighs]:
    placement = MAIL_UV[mesh_part["id"]]
    mesh_part["material_uv_authorship"] = placement
    for face in mesh_part["faces"]:
        if face["id"].startswith("hidden_"):
            continue
        face["material"] = "chainmail"
        corrected = placement["seam_corner_u"].get(face["id"], {})
        face["uv"] = [
            [round(corrected.get(i, uv[0]) * placement["scale"][0] + placement["offset"][0], 6),
             round(uv[1] * placement["scale"][1] + placement["offset"][1], 6)]
            for i, uv in enumerate(face["uv"])
        ]

document = {
    "schema_version": 1,
    "component": "body_underlayers",
    "reference_notes": [
        "Fresh literal padded clothing surfaces, never sampled from an earlier body or armor mesh.",
        "The fitted shirt records neck, clavicle, shoulder, thorax and hem contours. Neck and hem caps are closed hidden interfaces; the shoulder surface overlaps the separate arm underlayers.",
        "Shirt hem at approximately 1.28 m overlaps the existing abdomen garment that ends at 1.299 m. The upper waist at 1.124 m similarly overlaps the abdomen garment's lower extent.",
        "The hip mesh has an explicitly connected front rise, crotch and rear rise. Each hidden thigh interface meets a separately articulated padded breeches leg.",
        "Thigh pieces use literal custom cross-sectional points with authored front/back asymmetry and individually specified changes along the thigh, plus exact canonical placement matrices. No cross sections, profiles or connecting faces are calculated.",
        "All pieces belong to the body slot. Current torso/hip/thigh rigid ownership is preliminary binding metadata; deformation blends and overlap clearance still need motion review.",
        "Mirror seams are the only open control boundaries in the half-shirt and half-hip cages. After Mirror the fitted shells are closed. Visible hip and thigh surfaces use authored chainmail geometry bakes; per-part literal scale/offset records serialize repeated UV coordinates into face corners. The shirt remains padded leather and hidden interface caps retain their materials."
    ],
    "parts": [shirt, hips, thighs],
}

if __name__ == "__main__":
    output = ROOT / "source/body_underlayers.json"
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(output)
    print({"parts": len(document["parts"]),
           "control_vertices": sum(len(p["vertices"]) for p in document["parts"]),
           "control_faces": sum(len(p["faces"]) for p in document["parts"])})
