"""Literal articulated arm and glove meshes placed by canonical bone matrices.

Only fixed coordinate/face tables are serialized. Canonical matrices place those
authored meshes; explicit listed scales fit the individual finger articulations.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RIG = json.loads((ROOT / "source/rig_reference.dat").read_text())["bones"]


def placements(records):
    return [{"matrix": RIG[bone]["matrix"], "rigid_bone": bone, "scale": scale}
            for bone, scale in records]


def mesh(name, vertices, faces, bones, modifiers=(), closed=False, material="steel"):
    records, uv = [], {}
    for line in vertices.strip().splitlines():
        row = line.split()
        records.append({"id": row[0], "co": [float(c) for c in row[1:4]]})
        uv[row[0]] = [float(c) for c in row[4:6]]
    polygons = []
    for line in faces.strip().splitlines():
        row = line.split()
        mat = row[-1][1:] if row[-1].startswith("@") else material
        ids = row[1:-1] if row[-1].startswith("@") else row[1:]
        polygons.append({"id": row[0], "vertices": ids,
                         "uv": [uv[v] for v in ids], "material": mat})
    return {"id": name, "vertices": records, "faces": polygons,
            "modifiers": list(modifiers), "closed": closed, "landmarks": {},
            "seams": [], "sharp_edges": [], "creases": [], "slot": "hands",
            "rigid_bone": bones[0][0], "instances": placements(bones),
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0],
                          "scale": [1, 1, 1]}}


upper_sleeve = mesh("upper_arm_joint_underlayer", """
A0 -.052 .000 .032 .02 .02
A1 -.037 .000 .059 .15 .02
A2 .013 .000 .065 .29 .02
A3 .057 .000 .038 .43 .02
A4 .066 .000 -.017 .57 .02
A5 .029 .000 -.055 .71 .02
A6 -.025 .000 -.059 .85 .02
A7 -.058 .000 -.027 .98 .02
B0 -.065 .106 .034 .02 .41
B1 -.040 .112 .070 .15 .43
B2 .018 .118 .074 .29 .45
B3 .066 .112 .039 .43 .43
B4 .072 .105 -.020 .57 .41
B5 .033 .096 -.063 .71 .38
B6 -.029 .092 -.066 .85 .36
B7 -.068 .096 -.029 .98 .38
C0 -.049 .273 .022 .02 .98
C1 -.033 .277 .049 .15 .99
C2 .013 .278 .053 .29 .99
C3 .050 .273 .027 .43 .98
C4 .056 .266 -.018 .57 .96
C5 .027 .262 -.048 .71 .94
C6 -.024 .260 -.051 .85 .93
C7 -.053 .265 -.024 .98 .95
""", """
sleeve01 A0 B0 B1 A1
sleeve02 A1 B1 B2 A2
sleeve03 A2 B2 B3 A3
sleeve04 A3 B3 B4 A4
sleeve05 A4 B4 B5 A5
sleeve06 A5 B5 B6 A6
sleeve07 A6 B6 B7 A7
sleeve08 A7 B7 B0 A0
sleeve09 B0 C0 C1 B1
sleeve10 B1 C1 C2 B2
sleeve11 B2 C2 C3 B3
sleeve12 B3 C3 C4 B4
sleeve13 B4 C4 C5 B5
sleeve14 B5 C5 C6 B6
sleeve15 B6 C6 C7 B7
sleeve16 B7 C7 C0 B0
shoulder_end A7 A6 A5 A4 A3 A2 A1 A0
elbow_end C0 C1 C2 C3 C4 C5 C6 C7
""", [("upper_arm_L", [1, 1, 1]), ("upper_arm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}], closed=True, material="dark_steel")

upper_plate = mesh("rerebrace_shaped_shell", """
A0 -.065 .075 .026 .02 .06
A1 -.049 .060 .065 .21 .02
A2 0 .055 .085 .50 .01
A3 .053 .066 .067 .81 .04
A4 .076 .090 .020 .98 .10
B0 -.073 .145 .021 .02 .42
B1 -.055 .143 .069 .21 .42
B2 -.003 .136 .092 .50 .39
B3 .059 .145 .070 .81 .43
B4 .079 .155 .016 .98 .47
C0 -.058 .226 .018 .02 .86
C1 -.041 .238 .058 .21 .92
C2 .003 .245 .070 .50 .96
C3 .047 .237 .052 .81 .91
C4 .065 .222 .010 .98 .85
D0 -.057 .217 .021 .03 .82
D1 -.040 .229 .061 .22 .87
D2 .003 .236 .073 .50 .91
D3 .047 .228 .055 .80 .87
D4 .064 .213 .013 .97 .80
""", """
rerebrace01 A0 B0 B1 A1
rerebrace02 A1 B1 B2 A2
rerebrace03 A2 B2 B3 A3
rerebrace04 A3 B3 B4 A4
rerebrace05 B0 D0 D1 B1
rerebrace06 B1 D1 D2 B2
rerebrace07 B2 D2 D3 B3
rerebrace08 B3 D3 D4 B4
lower_rim01 D0 C0 C1 D1 @brass
lower_rim02 D1 C1 C2 D2 @brass
lower_rim03 D2 C2 C3 D3 @brass
lower_rim04 D3 C3 C4 D4 @brass
""", [("upper_arm_L", [1, 1, 1]), ("upper_arm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .004, "offset": 0}])

elbow = mesh("elbow_couter_and_wing", """
P0 -.067 -.028 .017 .02 .02
P1 -.050 -.036 .059 .16 .01
P2 -.006 -.041 .080 .40 .01
P3 .049 -.030 .067 .65 .02
P4 .084 -.006 .035 .86 .18
P5 .112 .018 .031 .99 .39
P6 .087 .042 .029 .86 .63
P7 .053 .059 .056 .69 .84
P8 .004 .071 .064 .44 .99
P9 -.049 .059 .047 .16 .88
P10 -.071 .034 .010 .02 .60
Q0 -.054 .006 .058 .13 .33
Q1 -.007 .007 .094 .42 .34
Q2 .048 .013 .078 .66 .39
Q3 .073 .019 .049 .81 .43
Q4 .035 .037 .073 .61 .67
Q5 -.012 .046 .078 .37 .73
Q6 -.054 .035 .045 .13 .66
""", """
couter01 P0 Q0 P1
couter02 P1 Q0 Q1 P2
couter03 P2 Q1 Q2 P3
couter04 P3 Q2 Q3 P4
couter05 P4 Q3 P5 @brass
couter06 P5 Q3 P6 @brass
couter07 P6 Q3 Q4 P7
couter08 P7 Q4 Q5 P8
couter09 P8 Q5 Q6 P9
couter10 P9 Q6 P10
couter11 P10 Q6 Q0 P0
couter12 Q0 Q6 Q5 Q1
couter13 Q1 Q5 Q4 Q2
couter14 Q2 Q4 Q3
""", [("forearm_L", [1, 1, 1]), ("forearm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .004, "offset": 0}])

forearm_sleeve = mesh("forearm_leather_underlayer", """
A0 -.057 .006 .023 .02 .01
A1 -.035 .006 .054 .15 .01
A2 .015 .006 .059 .29 .01
A3 .058 .006 .032 .43 .01
A4 .063 .006 -.012 .57 .01
A5 .030 .006 -.049 .71 .01
A6 -.025 .006 -.052 .85 .01
A7 -.060 .006 -.026 .98 .01
B0 -.049 .137 .022 .02 .48
B1 -.033 .141 .048 .15 .50
B2 .012 .145 .052 .29 .51
B3 .049 .139 .028 .43 .49
B4 .054 .134 -.013 .57 .47
B5 .026 .132 -.045 .71 .46
B6 -.021 .133 -.047 .85 .47
B7 -.052 .135 -.023 .98 .48
C0 -.033 .290 .016 .02 .98
C1 -.022 .290 .033 .15 .98
C2 .010 .290 .036 .29 .98
C3 .033 .290 .019 .43 .98
C4 .038 .290 -.009 .57 .98
C5 .019 .290 -.030 .71 .98
C6 -.016 .290 -.032 .85 .98
C7 -.035 .290 -.017 .98 .98
""", """
under01 A0 B0 B1 A1
under02 A1 B1 B2 A2
under03 A2 B2 B3 A3
under04 A3 B3 B4 A4
under05 A4 B4 B5 A5
under06 A5 B5 B6 A6
under07 A6 B6 B7 A7
under08 A7 B7 B0 A0
under09 B0 C0 C1 B1
under10 B1 C1 C2 B2
under11 B2 C2 C3 B3
under12 B3 C3 C4 B4
under13 B4 C4 C5 B5
under14 B5 C5 C6 B6
under15 B6 C6 C7 B7
under16 B7 C7 C0 B0
elbow_end A7 A6 A5 A4 A3 A2 A1 A0
wrist_end C0 C1 C2 C3 C4 C5 C6 C7
""", [("forearm_L", [1, 1, 1]), ("forearm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}], closed=True, material="leather")

vambrace = mesh("vambrace_front_and_cuff", """
A0 -.068 .071 .006 .02 .08
A1 -.049 .062 .051 .23 .05
A2 -.004 .050 .081 .50 .01
A3 .049 .065 .054 .77 .06
A4 .070 .078 .005 .98 .10
B0 -.065 .083 .009 .03 .13
B1 -.047 .074 .054 .24 .10
B2 -.004 .063 .083 .50 .05
B3 .047 .077 .057 .76 .11
B4 .067 .090 .008 .97 .16
C0 -.057 .171 -.001 .05 .53
C1 -.041 .171 .044 .25 .53
C2 .003 .162 .065 .50 .50
C3 .041 .175 .047 .75 .55
C4 .059 .182 -.004 .95 .58
D0 -.043 .263 -.006 .09 .92
D1 -.031 .270 .033 .27 .95
D2 .003 .284 .048 .50 .99
D3 .033 .271 .035 .73 .95
D4 .046 .255 -.012 .93 .89
E0 -.043 .251 -.003 .09 .87
E1 -.031 .258 .036 .27 .90
E2 .003 .271 .052 .50 .95
E3 .033 .259 .038 .73 .90
E4 .046 .244 -.009 .93 .85
""", """
upper_brass01 A0 B0 B1 A1 @brass
upper_brass02 A1 B1 B2 A2 @brass
upper_brass03 A2 B2 B3 A3 @brass
upper_brass04 A3 B3 B4 A4 @brass
vambrace01 B0 C0 C1 B1
vambrace02 B1 C1 C2 B2
vambrace03 B2 C2 C3 B3
vambrace04 B3 C3 C4 B4
vambrace05 C0 E0 E1 C1
vambrace06 C1 E1 E2 C2
vambrace07 C2 E2 E3 C3
vambrace08 C3 E3 E4 C4
cuff01 E0 D0 D1 E1 @brass
cuff02 E1 D1 D2 E2 @brass
cuff03 E2 D2 D3 E3 @brass
cuff04 E3 D3 D4 E4 @brass
""", [("forearm_L", [1, 1, 1]), ("forearm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .004, "offset": 0}])
vambrace["creases"] = [{"edge": ["B2", "C2"], "value": .45},
                        {"edge": ["C2", "E2"], "value": .45}]

vambrace_rear = mesh("vambrace_rear_closure", """
P0 -.063 .082 -.011 .02 .02
P1 -.043 .077 -.048 .24 .01
P2 .002 .080 -.063 .50 .02
P3 .044 .087 -.047 .77 .04
P4 .065 .095 -.013 .98 .08
Q0 -.053 .176 -.015 .05 .54
Q1 -.035 .171 -.043 .26 .52
Q2 .002 .168 -.054 .50 .51
Q3 .036 .180 -.041 .74 .57
Q4 .054 .186 -.015 .95 .60
R0 -.039 .257 -.011 .09 .95
R1 -.025 .264 -.033 .28 .98
R2 .002 .266 -.043 .50 .99
R3 .027 .262 -.030 .72 .97
R4 .041 .250 -.013 .92 .92
""", """
closure01 P0 Q0 Q1 P1
closure02 P1 Q1 Q2 P2
closure03 P2 Q2 Q3 P3
closure04 P3 Q3 Q4 P4
closure05 Q0 R0 R1 Q1
closure06 Q1 R1 R2 Q2
closure07 Q2 R2 R3 Q3
closure08 Q3 R3 R4 Q4
""", [("forearm_L", [1, 1, 1]), ("forearm_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .003, "offset": 0}])

palm = mesh("gauntlet_glove_palm_and_web", """
W0 -.032 -.013 .014 .02 .02
W1 -.023 -.013 .030 .15 .02
W2 .013 -.013 .030 .29 .02
W3 .032 -.013 .013 .43 .02
W4 .037 -.013 -.017 .57 .02
W5 .018 -.013 -.033 .71 .02
W6 -.017 -.013 -.036 .85 .02
W7 -.035 -.013 -.014 .98 .02
P0 -.041 .048 .020 .02 .42
P1 -.025 .056 .035 .15 .46
P2 .014 .059 .019 .29 .48
P3 .044 .058 -.003 .43 .47
P4 .060 .053 -.026 .57 .44
P5 .042 .047 -.049 .71 .41
P6 .004 .042 -.047 .85 .38
P7 -.031 .042 -.024 .98 .38
K0 -.030 .112 .016 .02 .88
K1 -.016 .126 .026 .15 .99
K2 .012 .123 .008 .29 .97
K3 .037 .112 -.012 .43 .88
K4 .057 .099 -.029 .57 .78
K5 .043 .091 -.047 .71 .73
K6 .009 .111 -.034 .85 .87
K7 -.018 .117 -.008 .98 .92
""", """
palm01 W0 P0 P1 W1
palm02 W1 P1 P2 W2
palm03 W2 P2 P3 W3
palm04 W3 P3 P4 W4
palm05 W4 P4 P5 W5
palm06 W5 P5 P6 W6
palm07 W6 P6 P7 W7
palm08 W7 P7 P0 W0
palm09 P0 K0 K1 P1
palm10 P1 K1 K2 P2
palm11 P2 K2 K3 P3
palm12 P3 K3 K4 P4
palm13 P4 K4 K5 P5
palm14 P5 K5 K6 P6
palm15 P6 K6 K7 P7
palm16 P7 K7 K0 P0
wrist_closure W7 W6 W5 W4 W3 W2 W1 W0
web K0 K1 K2 K3 K4 K5 K6 K7
""", [("hand_L", [1, 1, 1]), ("hand_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}], closed=True, material="leather")

handplate = mesh("gauntlet_dorsal_plate", """
A0 -.033 -.003 -.011 .01 .03
A1 -.019 -.006 -.038 .22 .01
A2 .008 -.003 -.043 .53 .03
A3 .033 .009 -.025 .86 .13
A4 .039 .023 -.012 .98 .24
B0 -.034 .061 -.020 .01 .54
B1 -.015 .061 -.050 .25 .54
B2 .016 .063 -.060 .58 .56
B3 .042 .063 -.049 .87 .56
B4 .060 .064 -.027 .99 .57
C0 -.024 .119 -.006 .02 .98
C1 -.016 .121 -.024 .24 .99
C2 .011 .119 -.043 .58 .97
C3 .037 .108 -.052 .86 .89
C4 .056 .096 -.039 .98 .79
""", """
dorsal01 A0 B0 B1 A1
dorsal02 A1 B1 B2 A2
dorsal03 A2 B2 B3 A3
dorsal04 A3 B3 B4 A4
dorsal05 B0 C0 C1 B1
dorsal06 B1 C1 C2 B2
dorsal07 B2 C2 C3 B3
dorsal08 B3 C3 C4 B4
""", [("hand_L", [1, 1, 1]), ("hand_R", [-1, 1, 1])],
    [{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .0035, "offset": 0}])

proximal = mesh("finger_proximal_articulations", """
A0 -.010 -.005 .007 .02 .02
A1 -.006 -.005 .012 .15 .02
A2 .006 -.005 .012 .29 .02
A3 .011 -.005 .006 .43 .02
A4 .012 -.005 -.006 .57 .02
A5 .007 -.005 -.014 .71 .02
A6 -.007 -.005 -.014 .85 .02
A7 -.012 -.005 -.006 .98 .02
B0 -.012 .008 .007 .02 .28
B1 -.007 .008 .012 .15 .28
B2 .007 .008 .012 .29 .28
B3 .012 .008 .006 .43 .28
B4 .014 .008 -.006 .57 .28
B5 .008 .008 -.016 .71 .28
B6 -.008 .008 -.016 .85 .28
B7 -.014 .008 -.006 .98 .28
C0 -.009 .038 .006 .02 .98
C1 -.005 .038 .010 .15 .98
C2 .005 .038 .010 .29 .98
C3 .010 .038 .005 .43 .98
C4 .011 .038 -.005 .57 .98
C5 .006 .038 -.012 .71 .98
C6 -.006 .038 -.012 .85 .98
C7 -.011 .038 -.005 .98 .98
""", """
prox01 A0 B0 B1 A1 @leather
prox02 A1 B1 B2 A2 @leather
prox03 A2 B2 B3 A3 @leather
prox04 A3 B3 B4 A4 @leather
prox05 A4 B4 B5 A5 @brass
prox06 A5 B5 B6 A6 @brass
prox07 A6 B6 B7 A7 @brass
prox08 A7 B7 B0 A0 @leather
prox09 B0 C0 C1 B1 @leather
prox10 B1 C1 C2 B2 @leather
prox11 B2 C2 C3 B3 @leather
prox12 B3 C3 C4 B4
prox13 B4 C4 C5 B5
prox14 B5 C5 C6 B6
prox15 B6 C6 C7 B7
prox16 B7 C7 C0 B0
knuckle_cap A7 A6 A5 A4 A3 A2 A1 A0 @leather
distal_cap C0 C1 C2 C3 C4 C5 C6 C7 @leather
""", [
    ("index_01_L", [1, .86, 1]), ("index_01_R", [-1, .86, 1]),
    ("middle_01_L", [1.04, 1.123, 1.04]), ("middle_01_R", [-1.04, 1.123, 1.04]),
    ("ring_01_L", [.95, .989, .95]), ("ring_01_R", [-.95, .989, .95]),
    ("pinky_01_L", [.78, .705, .78]), ("pinky_01_R", [-.78, .705, .78]),
    ("thumb_01_L", [1.15, 1.026, 1.15]), ("thumb_01_R", [-1.15, 1.026, 1.15]),
], [{"type": "SUBSURF", "levels": 1}], closed=True)

intermediate = mesh("finger_middle_articulations", """
A0 -.009 -.004 .006 .02 .02
A1 -.005 -.004 .010 .15 .02
A2 .005 -.004 .010 .29 .02
A3 .009 -.004 .005 .43 .02
A4 .011 -.004 -.004 .57 .02
A5 .007 -.004 -.012 .71 .02
A6 -.007 -.004 -.012 .85 .02
A7 -.011 -.004 -.004 .98 .02
B0 -.010 .006 .006 .02 .27
B1 -.006 .006 .010 .15 .27
B2 .006 .006 .010 .29 .27
B3 .010 .006 .005 .43 .27
B4 .012 .006 -.005 .57 .27
B5 .007 .006 -.014 .71 .27
B6 -.007 .006 -.014 .85 .27
B7 -.012 .006 -.005 .98 .27
C0 -.008 .031 .005 .02 .98
C1 -.005 .031 .009 .15 .98
C2 .005 .031 .009 .29 .98
C3 .008 .031 .005 .43 .98
C4 .009 .031 -.004 .57 .98
C5 .005 .031 -.011 .71 .98
C6 -.005 .031 -.011 .85 .98
C7 -.009 .031 -.004 .98 .98
""", """
middle01 A0 B0 B1 A1 @leather
middle02 A1 B1 B2 A2 @leather
middle03 A2 B2 B3 A3 @leather
middle04 A3 B3 B4 A4 @leather
middle05 A4 B4 B5 A5 @brass
middle06 A5 B5 B6 A6 @brass
middle07 A6 B6 B7 A7 @brass
middle08 A7 B7 B0 A0 @leather
middle09 B0 C0 C1 B1 @leather
middle10 B1 C1 C2 B2 @leather
middle11 B2 C2 C3 B3 @leather
middle12 B3 C3 C4 B4
middle13 B4 C4 C5 B5
middle14 B5 C5 C6 B6
middle15 B6 C6 C7 B7
middle16 B7 C7 C0 B0
proximal_cap A7 A6 A5 A4 A3 A2 A1 A0 @leather
distal_cap C0 C1 C2 C3 C4 C5 C6 C7 @leather
""", [
    ("index_02_L", [1, .966, 1]), ("index_02_R", [-1, .966, 1]),
    ("middle_02_L", [1.04, 1.130, 1.04]), ("middle_02_R", [-1.04, 1.130, 1.04]),
    ("ring_02_L", [.95, 1.026, .95]), ("ring_02_R", [-.95, 1.026, .95]),
    ("pinky_02_L", [.78, .645, .78]), ("pinky_02_R", [-.78, .645, .78]),
    ("thumb_02_L", [1.15, 1.511, 1.15]), ("thumb_02_R", [-1.15, 1.511, 1.15]),
], [{"type": "SUBSURF", "levels": 1}], closed=True)

distal = mesh("finger_distal_capped_articulations", """
A0 -.008 -.004 .005 .02 .02
A1 -.005 -.004 .009 .15 .02
A2 .005 -.004 .009 .29 .02
A3 .008 -.004 .005 .43 .02
A4 .010 -.004 -.004 .57 .02
A5 .006 -.004 -.012 .71 .02
A6 -.006 -.004 -.012 .85 .02
A7 -.010 -.004 -.004 .98 .02
B0 -.009 .009 .006 .02 .36
B1 -.005 .010 .011 .15 .39
B2 .005 .010 .011 .29 .39
B3 .009 .009 .006 .43 .36
B4 .010 .008 -.004 .57 .34
B5 .006 .008 -.013 .71 .34
B6 -.006 .008 -.013 .85 .34
B7 -.010 .008 -.004 .98 .34
C0 -.005 .030 .004 .02 .97
C1 -.003 .032 .008 .15 .99
C2 .003 .032 .008 .29 .99
C3 .005 .030 .004 .43 .97
C4 .006 .029 -.002 .57 .94
C5 .003 .028 -.007 .71 .91
C6 -.003 .028 -.007 .85 .91
C7 -.006 .029 -.002 .98 .94
""", """
distal01 A0 B0 B1 A1 @leather
distal02 A1 B1 B2 A2 @leather
distal03 A2 B2 B3 A3 @leather
distal04 A3 B3 B4 A4 @leather
distal05 A4 B4 B5 A5 @brass
distal06 A5 B5 B6 A6 @brass
distal07 A6 B6 B7 A7 @brass
distal08 A7 B7 B0 A0 @leather
distal09 B0 C0 C1 B1 @leather
distal10 B1 C1 C2 B2 @leather
distal11 B2 C2 C3 B3 @leather
distal12 B3 C3 C4 B4
distal13 B4 C4 C5 B5
distal14 B5 C5 C6 B6
distal15 B6 C6 C7 B7
distal16 B7 C7 C0 B0
proximal_cap A7 A6 A5 A4 A3 A2 A1 A0 @leather
fingertip C0 C1 C2 C3 C4 C5 C6 C7
""", [
    ("index_03_L", [1, .966, 1]), ("index_03_R", [-1, .966, 1]),
    ("middle_03_L", [1.04, 1.130, 1.04]), ("middle_03_R", [-1.04, 1.130, 1.04]),
    ("ring_03_L", [.95, 1.026, .95]), ("ring_03_R", [-.95, 1.026, .95]),
    ("pinky_03_L", [.78, .645, .78]), ("pinky_03_R", [-.78, .645, .78]),
    ("thumb_03_L", [1.15, 1.511, 1.15]), ("thumb_03_R", [-1.15, 1.511, 1.15]),
], [{"type": "SUBSURF", "levels": 1}], closed=True)

# Literal material placement, serialized into every face corner before import.
MAIL_UV = {
    "scale": [14.0, 10.0], "offset": [0.0, 0.0],
    "seam_corner_u": {
        "sleeve08": {2: 1.02, 3: 1.02},
        "sleeve16": {2: 1.02, 3: 1.02},
    },
    "target_link_diameter_m": [0.008, 0.010],
}
upper_sleeve["material_uv_authorship"] = MAIL_UV
for face in upper_sleeve["faces"]:
    if face["id"].startswith("sleeve"):
        face["material"] = "chainmail"
        corrected = MAIL_UV["seam_corner_u"].get(face["id"], {})
        face["uv"] = [
            [round(corrected.get(i, uv[0]) * 14.0, 6), round(uv[1] * 10.0, 6)]
            for i, uv in enumerate(face["uv"])
        ]

document = {
    "schema_version": 1,
    "component": "arms",
    "reference_notes": [
        "Fresh literal rerebrace, elbow couter, shaped vambrace, rear closure and gauntlet surfaces. No body extraction, procedural sweep or primitive assembly is used.",
        "Upper arm articulation uses image maps baked from the explicitly authored chainmail_detail.dat links. Literal 14 x 10 UV repetition targets 8-10 mm visible link diameters; seam corner values are explicit and the transformed UVs are retained per face corner.",
        "Each thumb/index/middle/ring/pinky articulation is a separate source instance bound to its matching canonical bone. Three independently authored forms describe knuckle, intermediate plate and rounded fingertip construction.",
        "The individually listed scales fit bone length/width differences; matrices are copied exactly from rig_reference.dat. Negative local X on right-hand instances mirrors the authored surface into the canonical right-side orientation without changing skeleton rest matrices.",
        "Glove web geometry follows the measured hand-local finger root positions. Plates have separate thickness and overlap underlayers, which remain independent for later motion correction.",
        "All parts are assigned to the hands slot. Final grip and joint clearance require rendered motion review; a valid source import is not animation acceptance."
    ],
    "parts": [upper_sleeve, upper_plate, elbow, forearm_sleeve, vambrace,
              vambrace_rear, palm, handplate, proximal, intermediate, distal],
}

if __name__ == "__main__":
    output = ROOT / "source/arms.json"
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(output)
    print({"parts": len(document["parts"]),
           "instances": sum(len(p["instances"]) for p in document["parts"]),
           "control_vertices": sum(len(p["vertices"]) for p in document["parts"]),
           "control_faces": sum(len(p["faces"]) for p in document["parts"])})
