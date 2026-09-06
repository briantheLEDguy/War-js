"""Serialize literal, individually placed pauldron surface control points.

No geometry is inferred here. The tables contain both the complete coordinate
list and the complete face connectivity; loops only serialize those records.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = []


def part(name, points, faces, material="steel", modifiers=None, closed=False,
         landmarks=None, instances=None):
    rows = [line.split() for line in points.strip().splitlines() if line.strip()]
    vertices = [{"id": f"v{i:03}", "co": [float(v) for v in row[:3]]}
                for i, row in enumerate(rows)]
    records = []
    for index, line in enumerate(faces.strip().splitlines()):
        indices = [int(v) for v in line.split()]
        records.append({"id": f"f{index:03}",
                        "vertices": [f"v{i:03}" for i in indices],
                        "uv": [[float(v) for v in rows[i][3:5]] for i in indices],
                        "material": material})
    bone = "upper_arm_L" if name in (
        "left_pauldron_upper_lame", "left_pauldron_upper_lame_brass_hem",
        "left_pauldron_lower_lame", "left_pauldron_lower_lame_brass_hem") else "shoulder_L"
    data = {"id": name, "slot": "shoulders", "rigid_bone": bone,
            "mirror_bone": bone.replace("_L", "_R"), "vertices": vertices, "faces": records,
            "modifiers": ([] if instances else [{"type": "MIRROR", "axis": "X"}]) + (modifiers or []),
            "landmarks": landmarks or {},
            "seams": [], "sharp_edges": [], "creases": [], "closed": closed,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0],
                          "scale": [1, 1, 1]}}
    if instances:
        data["instances"] = instances
    PARTS.append(data)
    return data


shell = part("left_pauldron_main_shell", """
.218 -.085 1.617 0 0
.215 -.080 1.645 0 .08
.215 -.025 1.694 0 .30
.217 .035 1.700 0 .55
.221 .088 1.681 0 .80
.224 .124 1.646 0 .94
.225 .133 1.626 0 1
.229 -.105 1.603 .07 0
.227 -.095 1.638 .07 .08
.225 -.027 1.708 .07 .30
.228 .035 1.713 .07 .55
.234 .102 1.690 .07 .80
.239 .143 1.648 .07 .94
.240 .153 1.623 .07 1
.268 -.139 1.577 .23 0
.265 -.130 1.625 .23 .08
.261 -.032 1.713 .23 .30
.264 .038 1.711 .23 .55
.271 .121 1.682 .23 .80
.279 .165 1.634 .23 .94
.280 .177 1.606 .23 1
.315 -.170 1.548 .43 0
.312 -.157 1.601 .43 .08
.305 -.041 1.704 .43 .30
.311 .039 1.699 .43 .55
.321 .137 1.663 .43 .80
.332 .183 1.610 .43 .94
.333 .193 1.581 .43 1
.365 -.181 1.518 .64 0
.363 -.166 1.574 .64 .08
.352 -.045 1.681 .64 .30
.362 .041 1.674 .64 .55
.375 .141 1.631 .64 .80
.388 .186 1.576 .64 .94
.390 .193 1.549 .64 1
.413 -.171 1.496 .82 0
.415 -.151 1.551 .82 .08
.410 -.039 1.637 .82 .30
.420 .044 1.625 .82 .55
.434 .132 1.581 .82 .80
.446 .167 1.533 .82 .94
.448 .173 1.513 .82 1
.443 -.141 1.488 .95 0
.450 -.119 1.535 .95 .08
.456 -.029 1.593 .95 .30
.465 .043 1.579 .95 .55
.470 .117 1.543 .95 .80
.470 .145 1.503 .95 .94
.467 .151 1.490 .95 1
.447 -.132 1.482 1 0
.456 -.110 1.523 1 .08
.468 -.025 1.578 1 .30
.477 .043 1.563 1 .55
.479 .111 1.530 1 .80
.476 .134 1.493 1 .94
.472 .140 1.482 1 1
""", """
0 7 8 1
1 8 9 2
2 9 10 3
3 10 11 4
4 11 12 5
5 12 13 6
7 14 15 8
8 15 16 9
9 16 17 10
10 17 18 11
11 18 19 12
12 19 20 13
14 21 22 15
15 22 23 16
16 23 24 17
17 24 25 18
18 25 26 19
19 26 27 20
21 28 29 22
22 29 30 23
23 30 31 24
24 31 32 25
25 32 33 26
26 33 34 27
28 35 36 29
29 36 37 30
30 37 38 31
31 38 39 32
32 39 40 33
33 40 41 34
35 42 43 36
36 43 44 37
37 44 45 38
38 45 46 39
39 46 47 40
40 47 48 41
42 49 50 43
43 50 51 44
44 51 52 45
45 52 53 46
46 53 54 47
47 54 55 48
""", modifiers=[{"type": "SUBSURF", "levels": 2},
                   {"type": "SOLIDIFY", "thickness": .004, "offset": -1},
                   {"type": "BEVEL", "width": .0007, "segments": 2}],
             landmarks={"inner_crown": "v017", "outside_edge": "v052",
                        "front_plate_corner": "v049", "rear_plate_corner": "v055"})
# These are literal boundary pairs, not a topology-discovery or shape operation.
shell["creases"] = [{"edge": [f"v{a:03}", f"v{b:03}"], "value": .85}
                    for a, b in [(0, 7), (7, 14), (14, 21), (21, 28), (28, 35),
                                 (35, 42), (42, 49), (55, 48), (48, 41),
                                 (41, 34), (34, 27), (27, 20), (20, 13), (13, 6),
                                 (6, 5), (5, 4), (4, 3), (3, 2), (2, 1), (1, 0)]]

part("left_pauldron_front_brass_border", """
.218 -.087 1.617 0 0
.218 -.082 1.624 0 1
.229 -.107 1.603 .10 0
.229 -.104 1.611 .10 1
.268 -.141 1.577 .27 0
.268 -.139 1.586 .27 1
.315 -.172 1.548 .45 0
.315 -.170 1.557 .45 1
.365 -.183 1.518 .63 0
.365 -.181 1.527 .63 1
.413 -.173 1.496 .82 0
.413 -.170 1.505 .82 1
.443 -.143 1.488 .95 0
.443 -.140 1.497 .95 1
.447 -.134 1.482 1 0
.446 -.132 1.491 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
10 12 13 11
12 14 15 13
""", "brass", [{"type": "SOLIDIFY", "thickness": .002, "offset": 0},
                  {"type": "BEVEL", "width": .0008, "segments": 2}])

outer_border = part("left_pauldron_outer_brass_border", """
.447 -.134 1.482 0 0
.440 -.139 1.492 0 1
.456 -.111 1.523 .10 0
.449 -.117 1.534 .10 1
.469 -.025 1.579 .32 0
.459 -.026 1.591 .32 1
.478 .043 1.564 .55 0
.468 .043 1.576 .55 1
.480 .111 1.531 .79 0
.472 .113 1.543 .79 1
.477 .134 1.494 .94 0
.470 .141 1.505 .94 1
.473 .140 1.483 1 0
.466 .147 1.494 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
10 12 13 11
""", "brass", [{"type": "SOLIDIFY", "thickness": .002, "offset": 0},
                  {"type": "BEVEL", "width": .0008, "segments": 2}])
outer_border["modifiers"].insert(1, {"type": "SUBSURF", "levels": 2})

part("left_pauldron_rear_brass_border", """
.225 .135 1.626 0 0
.225 .130 1.633 0 1
.240 .155 1.623 .10 0
.240 .150 1.631 .10 1
.280 .179 1.606 .27 0
.280 .173 1.614 .27 1
.333 .195 1.581 .45 0
.333 .189 1.590 .45 1
.390 .195 1.549 .64 0
.390 .189 1.557 .64 1
.448 .175 1.513 .83 0
.445 .169 1.522 .83 1
.467 .153 1.490 .96 0
.466 .146 1.502 .96 1
.473 .142 1.483 1 0
.466 .147 1.494 1 1
""", """
0 1 3 2
2 3 5 4
4 5 7 6
6 7 9 8
8 9 11 10
10 11 13 12
12 13 15 14
""", "brass", [{"type": "SOLIDIFY", "thickness": .002, "offset": 0},
                  {"type": "BEVEL", "width": .0008, "segments": 2}])

guard = part("left_pauldron_raised_inner_guard", """
.201 -.105 1.616 0 0
.205 -.108 1.654 0 .5
.217 -.101 1.674 0 1
.201 -.079 1.657 .17 0
.206 -.076 1.698 .17 .5
.218 -.069 1.714 .17 1
.205 -.021 1.680 .38 0
.210 -.019 1.721 .38 .5
.223 -.018 1.731 .38 1
.210 .038 1.680 .60 0
.216 .041 1.721 .60 .5
.229 .041 1.732 .60 1
.216 .093 1.658 .80 0
.222 .100 1.700 .80 .5
.235 .104 1.710 .80 1
.221 .125 1.620 1 0
.228 .139 1.660 1 .5
.241 .143 1.664 1 1
""", """
0 3 4 1
1 4 5 2
3 6 7 4
4 7 8 5
6 9 10 7
7 10 11 8
9 12 13 10
10 13 14 11
12 15 16 13
13 16 17 14
""", modifiers=[{"type": "SUBSURF", "levels": 2},
                   {"type": "SOLIDIFY", "thickness": .004, "offset": 0}],
     landmarks={"raised_guard_peak": "v011"})
guard["creases"] = [{"edge": [f"v{a:03}", f"v{b:03}"], "value": .95}
                    for a, b in [(0, 1), (1, 2), (2, 5), (5, 8), (8, 11),
                                 (11, 14), (14, 17), (17, 16), (16, 15),
                                 (15, 12), (12, 9), (9, 6), (6, 3), (3, 0)]]

part("left_pauldron_guard_brass_lip", """
.214 -.103 1.674 0 0
.220 -.099 1.676 0 1
.215 -.071 1.715 .17 0
.221 -.067 1.716 .17 1
.220 -.020 1.732 .38 0
.226 -.016 1.733 .38 1
.226 .039 1.733 .60 0
.232 .043 1.734 .60 1
.232 .102 1.711 .80 0
.238 .106 1.712 .80 1
.238 .141 1.665 1 0
.244 .145 1.666 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
""", "brass", [{"type": "SUBSURF", "levels": 2},
                  {"type": "SOLIDIFY", "thickness": .0025, "offset": 0},
                  {"type": "BEVEL", "width": .001, "segments": 2}])

upper_lame = part("left_pauldron_upper_lame", """
.351 -.130 1.592 0 0
.378 -.137 1.576 .25 0
.413 -.120 1.558 .5 0
.443 -.076 1.561 .75 0
.452 -.014 1.571 1 0
.346 -.135 1.530 0 .5
.378 -.142 1.503 .25 .5
.422 -.122 1.481 .5 .5
.458 -.075 1.475 .75 .5
.470 -.010 1.489 1 .5
.343 -.135 1.507 0 1
.381 -.142 1.483 .25 1
.429 -.120 1.461 .5 1
.466 -.070 1.463 .75 1
.476 -.008 1.470 1 1
.450 .053 1.561 1.20 0
.431 .108 1.535 1.42 0
.398 .136 1.518 1.65 0
.463 .061 1.489 1.20 .5
.441 .124 1.479 1.42 .5
.400 .153 1.465 1.65 .5
.469 .066 1.468 1.20 1
.444 .133 1.460 1.42 1
.399 .162 1.449 1.65 1
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
4 9 18 15
15 18 19 16
16 19 20 17
9 14 21 18
18 21 22 19
19 22 23 20
""", modifiers=[{"type": "SUBSURF", "levels": 2},
                   {"type": "SOLIDIFY", "thickness": .0035, "offset": -1}])
upper_lame["creases"] = [{"edge": [f"v{a:03}", f"v{b:03}"], "value": .95}
                         for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 15),
                                      (15, 16), (16, 17), (17, 20), (20, 23),
                                      (23, 22), (22, 21), (21, 14), (14, 13),
                                      (13, 12), (12, 11), (11, 10), (10, 5), (5, 0)]]

part("left_pauldron_upper_lame_brass_hem", """
.343 -.137 1.507 0 0
.344 -.137 1.514 0 1
.381 -.144 1.483 .14 0
.381 -.144 1.490 .14 1
.429 -.122 1.461 .28 0
.427 -.123 1.468 .28 1
.468 -.071 1.463 .42 0
.465 -.071 1.470 .42 1
.478 -.008 1.470 .57 0
.475 -.008 1.477 .57 1
.471 .067 1.468 .71 0
.468 .065 1.475 .71 1
.446 .134 1.460 .85 0
.444 .131 1.467 .85 1
.399 .164 1.449 1 0
.399 .161 1.456 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
10 12 13 11
12 14 15 13
""", "brass", [{"type": "SOLIDIFY", "thickness": .0015, "offset": 0},
                  {"type": "BEVEL", "width": .0007, "segments": 2}])

lower_lame = part("left_pauldron_lower_lame", """
.346 -.122 1.525 0 0
.384 -.130 1.506 .15 0
.426 -.107 1.488 .30 0
.453 -.063 1.481 .45 0
.462 -.003 1.487 .58 0
.453 .060 1.477 .72 0
.426 .113 1.458 .87 0
.393 .138 1.448 1 0
.343 -.120 1.490 0 .6
.387 -.128 1.468 .15 .6
.433 -.104 1.447 .30 .6
.467 -.058 1.439 .45 .6
.476 .004 1.445 .58 .6
.465 .071 1.429 .72 .6
.433 .127 1.414 .87 .6
.392 .151 1.410 1 .6
.342 -.119 1.477 0 1
.389 -.128 1.454 .15 1
.439 -.101 1.433 .30 1
.475 -.056 1.424 .45 1
.483 .007 1.430 .58 1
.471 .078 1.414 .72 1
.435 .136 1.401 .87 1
.390 .159 1.397 1 1
""", """
0 8 9 1
1 9 10 2
2 10 11 3
3 11 12 4
4 12 13 5
5 13 14 6
6 14 15 7
8 16 17 9
9 17 18 10
10 18 19 11
11 19 20 12
12 20 21 13
13 21 22 14
14 22 23 15
""", modifiers=[{"type": "SUBSURF", "levels": 2},
                   {"type": "SOLIDIFY", "thickness": .003, "offset": -1}])
lower_lame["creases"] = [{"edge": [f"v{a:03}", f"v{b:03}"], "value": .95}
                         for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
                                      (5, 6), (6, 7), (7, 15), (15, 23),
                                      (23, 22), (22, 21), (21, 20), (20, 19),
                                      (19, 18), (18, 17), (17, 16), (16, 8), (8, 0)]]

part("left_pauldron_lower_lame_brass_hem", """
.342 -.121 1.477 0 0
.343 -.121 1.484 0 1
.389 -.130 1.454 .15 0
.388 -.130 1.461 .15 1
.440 -.102 1.433 .30 0
.437 -.104 1.440 .30 1
.477 -.057 1.424 .45 0
.473 -.058 1.431 .45 1
.485 .007 1.430 .58 0
.481 .005 1.437 .58 1
.473 .079 1.414 .72 0
.470 .076 1.421 .72 1
.437 .138 1.401 .87 0
.435 .133 1.408 .87 1
.390 .161 1.397 1 0
.391 .157 1.404 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
10 12 13 11
12 14 15 13
""", "brass", [{"type": "SOLIDIFY", "thickness": .0015, "offset": 0},
                  {"type": "BEVEL", "width": .0007, "segments": 2}])

# Sculpted cross-shaped badge, conformed by individually authored front depths.
# The four quads around its center form a single contiguous raised ornament.
part("left_pauldron_sun_cross_emblem", """
.350 -.1140 1.620 .4 1
.356 -.1056 1.624 .6 1
.362 -.1073 1.619 .8 .92
.358 -.1218 1.609 .6 .80
.359 -.1328 1.598 .6 .62
.372 -.1279 1.595 .85 .62
.379 -.1177 1.599 1 .70
.380 -.1314 1.586 1 .46
.372 -.1339 1.589 .85 .50
.360 -.1382 1.592 .6 .50
.363 -.1550 1.571 .6 .15
.370 -.1563 1.565 .78 .08
.354 -.1617 1.566 .4 .05
.356 -.1569 1.572 .46 .15
.353 -.1398 1.594 .46 .50
.340 -.1435 1.596 .20 .50
.333 -.1485 1.592 .05 .40
.333 -.1364 1.606 .05 .67
.340 -.1377 1.602 .20 .62
.352 -.1345 1.600 .46 .62
.351 -.1226 1.612 .46 .82
""", """
0 1 2 3 20
20 3 4 19
19 4 9 14
4 5 6 7 8 9
14 9 10 13
13 10 11 12
18 19 14 15
17 18 15 16
""", "brass", [{"type": "SOLIDIFY", "thickness": .003, "offset": 0},
                  {"type": "BEVEL", "width": .0007, "segments": 2}])

# Hand-placed octagonal domed fastener: local axis points toward the front (-Y).
rivet = part("left_pauldron_authored_rivet", """
.004 0 0 1 .5
.0028 0 .0028 .85 .85
0 0 .004 .5 1
-.0028 0 .0028 .15 .85
-.004 0 0 0 .5
-.0028 0 -.0028 .15 .15
0 0 -.004 .5 0
.0028 0 -.0028 .85 .15
.003 -.002 0 .87 .5
.0021 -.002 .0021 .76 .76
0 -.002 .003 .5 .87
-.0021 -.002 .0021 .24 .76
-.003 -.002 0 .13 .5
-.0021 -.002 -.0021 .24 .24
0 -.002 -.003 .5 .13
.0021 -.002 -.0021 .76 .24
0 -.0032 0 .5 .5
""", """
0 8 9 1
1 9 10 2
2 10 11 3
3 11 12 4
4 12 13 5
5 13 14 6
6 14 15 7
7 15 8 0
8 16 9
9 16 10
10 16 11
11 16 12
12 16 13
13 16 14
14 16 15
15 16 8
7 6 5 4 3 2 1 0
""", "brass", closed=True, instances=[
    {"location": [.243, -.118, 1.605], "rotation_degrees": [-8, 0, -12], "scale": [1, 1, 1]},
    {"location": [.275, -.144, 1.584], "rotation_degrees": [-8, 0, -8], "scale": [1, 1, 1]},
    {"location": [.308, -.165, 1.564], "rotation_degrees": [-10, 0, 0], "scale": [1, 1, 1]},
    {"location": [.404, -.173, 1.515], "rotation_degrees": [-10, 0, 15], "scale": [1, 1, 1]},
    {"location": [.431, -.154, 1.504], "rotation_degrees": [-10, 0, 30], "scale": [1, 1, 1]},
    {"location": [.449, -.122, 1.515], "rotation_degrees": [-10, 0, 50], "scale": [1, 1, 1]},
    {"location": [.355, -.142, 1.510], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
    {"location": [.420, -.129, 1.469], "rotation_degrees": [0, 0, 15], "scale": [.85, .85, .85]},
    {"location": [.358, -.124, 1.489], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
    {"location": [.411, -.118, 1.455], "rotation_degrees": [0, 0, 15], "scale": [.85, .85, .85]},
    {"location": [.236, .153, 1.638], "rotation_degrees": [25, 0, 180], "scale": [1, 1, 1]},
    {"location": [.293, .184, 1.611], "rotation_degrees": [25, 0, 180], "scale": [1, 1, 1]},
    {"location": [.376, .196, 1.566], "rotation_degrees": [25, 0, 180], "scale": [1, 1, 1]},
])

part("left_pauldron_leather_suspension", """
.218 -.012 1.631 0 0
.237 -.020 1.635 1 0
.242 -.022 1.615 1 .35
.222 -.014 1.612 0 .35
.231 -.011 1.597 0 .65
.251 -.017 1.600 1 .65
.259 -.012 1.583 1 1
.240 -.006 1.580 0 1
""", """
0 1 2 3
3 2 5 4
4 5 6 7
""", "leather", [{"type": "SOLIDIFY", "thickness": .003, "offset": 0},
                   {"type": "BEVEL", "width": .0008, "segments": 2}])

# A short individually shaped padded shoulder attachment fills the dark space
# between the breastplate's arm opening and the independent metal plates.
part("left_pauldron_padded_shoulder_support", """
.212 -.032 1.615 0 1
.256 -.064 1.638 .25 1
.317 -.079 1.636 .55 1
.371 -.063 1.605 .80 1
.399 -.039 1.559 1 1
.212 -.067 1.578 0 .55
.259 -.107 1.579 .25 .55
.321 -.123 1.568 .55 .55
.380 -.100 1.535 .80 .55
.411 -.054 1.494 1 .55
.217 -.061 1.538 0 0
.260 -.100 1.533 .25 0
.324 -.114 1.513 .55 0
.384 -.091 1.483 .80 0
.414 -.043 1.462 1 0
.211 .035 1.611 0 1
.255 .078 1.633 .25 1
.318 .104 1.624 .55 1
.374 .098 1.589 .80 1
.402 .069 1.548 1 1
.215 .071 1.573 0 .55
.261 .118 1.567 .25 .55
.325 .141 1.550 .55 .55
.384 .126 1.520 .80 .55
.418 .081 1.481 1 .55
.220 .064 1.535 0 0
.264 .103 1.524 .25 0
.329 .128 1.501 .55 0
.390 .116 1.472 .80 0
.422 .075 1.452 1 0
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
15 16 21 20
16 17 22 21
17 18 23 22
18 19 24 23
20 21 26 25
21 22 27 26
22 23 28 27
23 24 29 28
0 1 16 15
1 2 17 16
2 3 18 17
3 4 19 18
4 9 24 19
9 14 29 24
10 25 26 11
11 26 27 12
12 27 28 13
13 28 29 14
0 15 20 5
5 20 25 10
""", "dark_steel", [{"type": "SUBSURF", "levels": 2}], closed=True)

# Reuse the new authored fastener mesh with explicitly enumerated placements.
# Local X symmetry permits a proper reflected rotation without a negative scale.
lame_rivets = json.loads(json.dumps(rivet))
lame_rivets["id"] = "left_pauldron_lame_fasteners"
lame_rivets["rigid_bone"] = "upper_arm_L"
lame_rivets["mirror_bone"] = "upper_arm_R"
lame_rivets["instances"] = [rivet["instances"][i] for i in (6, 7, 8, 9)] + [
    {"location": [-.355, -.142, 1.510], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
    {"location": [-.420, -.129, 1.469], "rotation_degrees": [0, 0, -15], "scale": [.85, .85, .85]},
    {"location": [-.358, -.124, 1.489], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
    {"location": [-.411, -.118, 1.455], "rotation_degrees": [0, 0, -15], "scale": [.85, .85, .85]},
]
rivet["instances"] = [rivet["instances"][i] for i in (0, 1, 2, 3, 4, 5, 10, 11, 12)] + [
    {"location": [-.243, -.118, 1.605], "rotation_degrees": [-8, 0, 12], "scale": [1, 1, 1]},
    {"location": [-.275, -.144, 1.584], "rotation_degrees": [-8, 0, 8], "scale": [1, 1, 1]},
    {"location": [-.308, -.165, 1.564], "rotation_degrees": [-10, 0, 0], "scale": [1, 1, 1]},
    {"location": [-.404, -.173, 1.515], "rotation_degrees": [-10, 0, -15], "scale": [1, 1, 1]},
    {"location": [-.431, -.154, 1.504], "rotation_degrees": [-10, 0, -30], "scale": [1, 1, 1]},
    {"location": [-.449, -.122, 1.515], "rotation_degrees": [-10, 0, -50], "scale": [1, 1, 1]},
    {"location": [-.236, .153, 1.638], "rotation_degrees": [25, 0, -180], "scale": [1, 1, 1]},
    {"location": [-.293, .184, 1.611], "rotation_degrees": [25, 0, -180], "scale": [1, 1, 1]},
    {"location": [-.376, .196, 1.566], "rotation_degrees": [25, 0, -180], "scale": [1, 1, 1]},
]
PARTS.append(lame_rivets)

record = {"schema_version": 1, "component": "left_pauldron", "reference_notes": [
    "Large front illustration is primary: a broad curved steel shell with a high inner ridge and lower overlapping lames.",
    "The shoulder is authored in meters with the character's left on positive X and the front toward negative Y.",
    "The inner defense rises slightly above the main dome, matching the prominent tall shoulder ridge in the source.",
    "The shoulder emblem is a raised cross-like brass ornament; small engraved decoration is deferred until the silhouette proof passes.",
    "Fastener coordinates are an explicit finite placement list. No scatter, profile sweep, primitive operator, or body surface is used.",
    "The exact rear fastening is occluded in the sheet; a conservative dark leather suspension strap is documented here.",
    "Positive-X shoulder plates have X Mirror finishing. Local rivet meshes have an explicit reflected transform for each right-side copy.",
    "Paired shoulder module with explicit rigid_bone/mirror_bone metadata. No visual acceptance or runtime suitability is implied by import success."
], "parts": PARTS}
(ROOT / "source" / "pauldron.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(PARTS)} authored parts; {sum(len(p['vertices']) for p in PARTS)} control vertices; {sum(len(p['faces']) for p in PARTS)} faces.")
