"""Serialize literal parchment, seal, chain, censer and embroidered-trim meshes.

All shape coordinates and connections are hand-entered tables. Lists of repeated
wax seals, chain links and fringe placements are explicit and finite.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = []


def part(name, points, faces, material, slot, closed=False, modifiers=None, instances=None, bone=None):
    rows = [row.split() for row in points.strip().splitlines() if row.strip()]
    result = {
        "id": name, "slot": slot,
        "vertices": [{"id": f"v{i:03}", "co": [float(v) for v in row[:3]]} for i, row in enumerate(rows)],
        "faces": [{"id": f"f{i:03}", "vertices": [f"v{int(v):03}" for v in row.split()],
                   "uv": [[float(v) for v in rows[int(index)][3:5]] for index in row.split()], "material": material}
                  for i, row in enumerate(faces.strip().splitlines()) if row.strip()],
        "modifiers": modifiers or [], "landmarks": {}, "seams": [], "sharp_edges": [], "creases": [],
        "closed": closed, "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]},
    }
    if instances:
        result["instances"] = instances
    if bone:
        result["rigid_bone"] = bone
    PARTS.append(result)
    return result


part("relic_upper_folded_parchments", """
-.187 -.167 1.521 0 1
-.169 -.173 1.523 .5 1
-.151 -.166 1.520 1 1
-.187 -.182 1.466 0 .75
-.169 -.190 1.466 .5 .75
-.151 -.182 1.465 1 .75
-.189 -.201 1.389 0 .39
-.170 -.205 1.393 .5 .41
-.150 -.196 1.395 1 .42
-.194 -.211 1.316 0 .05
-.175 -.216 1.327 .48 .1
-.153 -.208 1.320 1 .07
.148 -.168 1.520 0 1
.166 -.175 1.523 .5 1
.184 -.168 1.520 1 1
.151 -.185 1.466 0 .75
.169 -.193 1.468 .5 .76
.188 -.184 1.464 1 .74
.157 -.206 1.391 0 .40
.175 -.210 1.394 .5 .42
.194 -.201 1.390 1 .39
.158 -.218 1.319 0 .07
.178 -.223 1.325 .5 .09
.199 -.213 1.309 1 .02
""", """
0 1 4 3
1 2 5 4
3 4 7 6
4 5 8 7
6 7 10 9
7 8 11 10
12 13 16 15
13 14 17 16
15 16 19 18
16 17 20 19
18 19 22 21
19 20 23 22
""", "parchment", "chest", modifiers=[{"type": "SOLIDIFY", "thickness": .001, "offset": 0}], bone="upper_chest")

part("relic_upper_offset_parchment_tails", """
-.183 -.166 1.505 0 1
-.167 -.174 1.505 1 1
-.204 -.182 1.413 0 .50
-.184 -.190 1.417 1 .52
-.216 -.197 1.353 0 .09
-.194 -.202 1.343 1 .04
.164 -.166 1.505 0 1
.179 -.165 1.505 1 1
.184 -.184 1.431 0 .57
.203 -.179 1.424 1 .54
.191 -.195 1.367 0 .20
.215 -.188 1.353 1 .12
""", """
0 1 3 2
2 3 5 4
6 7 9 8
8 9 11 10
""", "parchment", "chest", modifiers=[{"type": "SOLIDIFY", "thickness": .0008, "offset": 0}], bone="upper_chest")

WAX_POINTS = """
0 -.002 .026 .50 1
.013 -.002 .023 .76 .94
.023 -.003 .013 .96 .75
.026 -.002 -.001 1 .48
.022 -.003 -.014 .92 .23
.011 -.002 -.025 .72 .02
-.002 -.002 -.027 .46 0
-.015 -.003 -.022 .20 .08
-.025 -.002 -.012 0 .27
-.025 -.003 .003 0 .56
-.019 -.002 .017 .12 .83
-.009 -.003 .024 .32 .96
0 -.009 .001 .50 .52
"""
WAX_FACES = """
0 1 12
1 2 12
2 3 12
3 4 12
4 5 12
5 6 12
6 7 12
7 8 12
8 9 12
9 10 12
10 11 12
11 0 12
"""
CHEST_SEALS = [
    {"location": [-.169, -.169, 1.532], "rotation_degrees": [0, -8, 0]},
    {"location": [.166, -.169, 1.532], "rotation_degrees": [0, 9, 0]},
]
BELT_SEALS = [
    {"location": [-.189, -.128, 1.174], "rotation_degrees": [0, -8, -19], "scale": [.78, .78, .78]},
    {"location": [-.105, -.175, 1.170], "rotation_degrees": [0, 4, -4], "scale": [.75, .75, .75]},
    {"location": [.109, -.175, 1.173], "rotation_degrees": [0, -4, 5], "scale": [.75, .75, .75]},
    {"location": [.189, -.128, 1.176], "rotation_degrees": [0, 7, 19], "scale": [.78, .78, .78]},
]
part("relic_upper_wax_seals", WAX_POINTS, WAX_FACES, "crimson", "chest",
     modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0}], instances=CHEST_SEALS, bone="upper_chest")
part("relic_belt_wax_seals", WAX_POINTS, WAX_FACES, "crimson", "waist",
     modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0}], instances=BELT_SEALS, bone="hips")

STAMP_POINTS = """
-.003 -.012 .016 .43 1
.003 -.012 .016 .57 1
.003 -.013 .005 .57 .66
.012 -.012 .005 .91 .66
.012 -.012 -.001 .91 .48
.003 -.013 -.001 .57 .48
.003 -.012 -.015 .57 .05
-.003 -.012 -.015 .43 .05
-.003 -.013 -.001 .43 .48
-.012 -.012 -.001 .09 .48
-.012 -.012 .005 .09 .66
-.003 -.013 .005 .43 .66
"""
STAMP_FACES = """
0 1 2 11
2 3 4 5 8 9 10 11
5 6 7 8
"""
part("relic_upper_wax_stamp_marks", STAMP_POINTS, STAMP_FACES, "leather", "chest",
     modifiers=[{"type": "SOLIDIFY", "thickness": .0008, "offset": 0}], instances=CHEST_SEALS, bone="upper_chest")
part("relic_belt_wax_stamp_marks", STAMP_POINTS, STAMP_FACES, "leather", "waist",
     modifiers=[{"type": "SOLIDIFY", "thickness": .0008, "offset": 0}], instances=BELT_SEALS, bone="hips")

part("relic_four_belt_parchments", """
-.204 -.124 1.169 0 1
-.184 -.136 1.173 1 1
-.214 -.153 1.081 0 .57
-.185 -.164 1.085 1 .59
-.224 -.180 .991 0 .15
-.194 -.192 .979 1 .09
-.118 -.176 1.166 0 1
-.094 -.176 1.165 1 1
-.121 -.208 1.078 0 .60
-.092 -.214 1.074 1 .58
-.127 -.225 .942 0 .04
-.093 -.222 .953 1 .09
.096 -.176 1.171 0 1
.121 -.174 1.171 1 1
.095 -.213 1.080 0 .60
.126 -.205 1.081 1 .61
.101 -.225 .948 0 .05
.132 -.216 .936 1 0
.179 -.133 1.169 0 1
.202 -.124 1.174 1 1
.183 -.161 1.080 0 .59
.216 -.150 1.088 1 .62
.194 -.188 .984 0 .14
.226 -.175 .994 1 .18
""", """
0 1 3 2
2 3 5 4
6 7 9 8
8 9 11 10
12 13 15 14
14 15 17 16
18 19 21 20
20 21 23 22
""", "parchment", "waist", modifiers=[{"type": "SOLIDIFY", "thickness": .001, "offset": 0}], bone="hips")

part("relic_upper_manual_ink_strokes", """
-.182 -.187 1.486 0 1
-.156 -.187 1.486 1 1
-.158 -.188 1.484 .94 .9
-.181 -.188 1.484 .04 .9
-.182 -.194 1.457 0 .8
-.155 -.193 1.457 1 .8
-.156 -.194 1.455 .96 .7
-.180 -.195 1.455 .07 .7
-.183 -.200 1.430 0 .6
-.159 -.199 1.430 .90 .6
-.159 -.200 1.428 .90 .5
-.182 -.201 1.428 .03 .5
-.183 -.204 1.404 0 .4
-.157 -.203 1.404 1 .4
-.158 -.204 1.402 .96 .3
-.181 -.205 1.402 .07 .3
-.184 -.209 1.375 0 .2
-.161 -.208 1.375 .89 .2
-.160 -.209 1.373 .94 .1
-.183 -.210 1.373 .04 .1
.155 -.189 1.487 0 1
.181 -.188 1.487 1 1
.180 -.189 1.485 .96 .9
.156 -.190 1.485 .04 .9
.157 -.196 1.458 0 .8
.182 -.194 1.458 .96 .8
.181 -.195 1.456 .92 .7
.158 -.197 1.456 .04 .7
.160 -.202 1.431 0 .6
.185 -.200 1.431 .96 .6
.184 -.201 1.429 .92 .5
.160 -.203 1.429 0 .5
.162 -.209 1.404 0 .4
.187 -.206 1.404 .96 .4
.188 -.207 1.402 1 .3
.162 -.210 1.402 0 .3
.164 -.214 1.375 0 .2
.187 -.211 1.375 .89 .2
.187 -.212 1.373 .89 .1
.165 -.215 1.373 .04 .1
""", """
0 1 2 3
4 5 6 7
8 9 10 11
12 13 14 15
16 17 18 19
20 21 22 23
24 25 26 27
28 29 30 31
32 33 34 35
36 37 38 39
""", "leather", "chest", modifiers=[{"type": "SOLIDIFY", "thickness": .00025, "offset": 0}], bone="upper_chest")

LINK_POINTS = """
-.004 0 -.014 .25 0
.004 0 -.014 .75 0
.008 0 -.009 1 .18
.008 0 .009 1 .82
.004 0 .014 .75 1
-.004 0 .014 .25 1
-.008 0 .009 0 .82
-.008 0 -.009 0 .18
-.002 0 -.009 .38 .18
.002 0 -.009 .62 .18
.004 0 -.006 .75 .29
.004 0 .006 .75 .71
.002 0 .009 .62 .82
-.002 0 .009 .38 .82
-.004 0 .006 .25 .71
-.004 0 -.006 .25 .29
"""
LINK_FACES = """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
7 0 8 15
"""
part("relic_censer_suspension_links", LINK_POINTS, LINK_FACES, "brass", "waist",
     modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0}, {"type": "BEVEL", "width": .0006, "segments": 2}],
     instances=[
         {"location": [.263, 0, 1.127], "rotation_degrees": [0, -22, 0]},
         {"location": [.272, 0, 1.105], "rotation_degrees": [-22, 0, 90]},
         {"location": [.282, 0, 1.083], "rotation_degrees": [0, -26, 0]},
         {"location": [.294, 0, 1.061], "rotation_degrees": [-26, 0, 90]},
         {"location": [.306, 0, 1.039], "rotation_degrees": [0, -27, 0]},
         {"location": [.318, 0, 1.017], "rotation_degrees": [-27, 0, 90]},
         {"location": [.330, 0, .995], "rotation_degrees": [0, -27, 0]},
         {"location": [.342, 0, .973], "rotation_degrees": [-27, 0, 90]},
         {"location": [.354, 0, .951], "rotation_degrees": [0, -23, 0]},
         {"location": [.363, 0, .929], "rotation_degrees": [-23, 0, 90]},
         {"location": [.372, 0, .907], "rotation_degrees": [0, -21, 0]},
         {"location": [.380, 0, .885], "rotation_degrees": [-17, 0, 90]},
         {"location": [.386, 0, .863], "rotation_degrees": [0, -15, 0]},
         {"location": [.392, 0, .841], "rotation_degrees": [-13, 0, 90]},
         {"location": [.396, 0, .819], "rotation_degrees": [0, -8, 0]},
         {"location": [.399, 0, .797], "rotation_degrees": [-4, 0, 90]},
         {"location": [.400, 0, .775], "rotation_degrees": [0, 0, 0]},
         {"location": [.400, 0, .753], "rotation_degrees": [0, 0, 90]},
         {"location": [.400, 0, .731], "rotation_degrees": [0, 0, 0]},
     ], bone="hips")

part("relic_censer_hollow_fluted_bowl", """
.388 -.020 .583 .0 .08
.412 -.020 .583 .14 .08
.422 -.011 .583 .28 .08
.421 .012 .583 .42 .08
.411 .022 .583 .56 .08
.387 .022 .583 .70 .08
.377 .010 .583 .84 .08
.378 -.012 .583 1 .08
.377 -.039 .608 .0 .43
.423 -.039 .608 .14 .43
.441 -.022 .608 .28 .43
.442 .023 .608 .42 .43
.423 .041 .608 .56 .43
.376 .042 .608 .70 .43
.357 .022 .608 .84 .43
.358 -.023 .608 1 .43
.373 -.045 .633 .0 .78
.427 -.045 .633 .14 .78
.451 -.025 .633 .28 .78
.450 .026 .633 .42 .78
.426 .047 .633 .56 .78
.373 .046 .633 .70 .78
.348 .025 .633 .84 .78
.349 -.026 .633 1 .78
.376 -.041 .647 .0 1
.424 -.041 .647 .14 1
.447 -.023 .647 .28 1
.446 .025 .647 .42 1
.424 .044 .647 .56 1
.376 .043 .647 .70 1
.353 .023 .647 .84 1
.354 -.024 .647 1 1
.400 0 .571 .5 0
""", """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
7 0 8 15
8 9 17 16
9 10 18 17
10 11 19 18
11 12 20 19
12 13 21 20
13 14 22 21
14 15 23 22
15 8 16 23
16 17 25 24
17 18 26 25
18 19 27 26
19 20 28 27
20 21 29 28
21 22 30 29
22 23 31 30
23 16 24 31
0 32 1
1 32 2
2 32 3
3 32 4
4 32 5
5 32 6
6 32 7
7 32 0
""", "brass", "waist", modifiers=[{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .0025, "offset": 0}], bone="hips")

part("relic_censer_open_window_band", """
.394 -.045 .644 0 0
.405 -.045 .644 .12 0
.405 -.047 .679 .12 1
.394 -.047 .679 0 1
.440 -.026 .644 .13 0
.447 -.017 .644 .25 0
.450 -.018 .679 .25 1
.443 -.029 .679 .13 1
.446 .017 .644 .26 0
.439 .028 .644 .38 0
.442 .030 .679 .38 1
.450 .018 .679 .26 1
.406 .046 .644 .39 0
.394 .046 .644 .51 0
.394 .049 .679 .51 1
.406 .049 .679 .39 1
.361 .027 .644 .52 0
.354 .017 .644 .64 0
.351 .018 .679 .64 1
.358 .029 .679 .52 1
.354 -.017 .644 .65 0
.362 -.029 .644 .77 0
.359 -.031 .679 .77 1
.350 -.018 .679 .65 1
""", """
0 1 2 3
4 5 6 7
8 9 10 11
12 13 14 15
16 17 18 19
20 21 22 23
""", "brass", "waist", modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0}, {"type": "BEVEL", "width": .0007, "segments": 2}], bone="hips")

part("relic_censer_pointed_canopy", """
.372 -.046 .678 .0 0
.428 -.046 .678 .14 0
.452 -.025 .678 .28 0
.452 .027 .678 .42 0
.427 .050 .678 .56 0
.372 .049 .678 .70 0
.348 .025 .678 .84 0
.348 -.027 .678 1 0
.379 -.033 .691 .0 .32
.421 -.033 .691 .14 .32
.435 -.019 .691 .28 .32
.435 .020 .691 .42 .32
.420 .036 .691 .56 .32
.379 .035 .691 .70 .32
.364 .018 .691 .84 .32
.364 -.020 .691 1 .32
.392 -.011 .713 .0 .86
.408 -.011 .713 .14 .86
.412 -.006 .713 .28 .86
.412 .007 .713 .42 .86
.407 .013 .713 .56 .86
.392 .012 .713 .70 .86
.387 .006 .713 .84 .86
.387 -.007 .713 1 .86
.400 0 .720 .5 1
""", """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
7 0 8 15
8 9 17 16
9 10 18 17
10 11 19 18
11 12 20 19
12 13 21 20
13 14 22 21
14 15 23 22
15 8 16 23
16 17 24
17 18 24
18 19 24
19 20 24
20 21 24
21 22 24
22 23 24
23 16 24
""", "brass", "waist", modifiers=[{"type": "SOLIDIFY", "thickness": .002, "offset": 0}, {"type": "BEVEL", "width": .0007, "segments": 2}], bone="hips")

# Literal supports measured against the finished authored cloth, with a 0.7 mm
# front offset. The loader performs no projection or automatic deformation.
part("relic_tabard_fold_following_cross", """
-.011 -.204973 .850 .50 1
.013 -.194402 .830 .65 .92
.001 -.198193 .825 .57 .91
.001 -.195987 .752 .57 .67
.050 -.194938 .752 .80 .67
.060 -.202487 .769 .90 .70
.086 -.204726 .735 1 .64
.061 -.197833 .704 .89 .58
.050 -.192573 .722 .80 .61
.001 -.194176 .722 .57 .61
.001 -.184580 .583 .57 .09
.018 -.174962 .555 .68 .03
-.006 -.185499 .545 .51 .01
-.014 -.190828 .557 .45 .04
-.038 -.181119 .547 .32 .01
-.044 -.180954 .568 .28 .06
-.022 -.191667 .584 .42 .09
-.022 -.203633 .722 .43 .61
-.069 -.187958 .722 .19 .61
-.080 -.191092 .705 .10 .58
-.107 -.207950 .735 0 .64
-.080 -.194251 .770 .10 .70
-.069 -.189655 .752 .19 .67
-.022 -.206290 .752 .43 .67
-.022 -.208662 .825 .43 .91
-.035 -.201599 .830 .35 .92
-.022 -.207613 .789 .43 .79
-.020350 -.209577 .825 .44 .91
-.019680 -.208900 .789 .45 .79
.001 -.197012 .789 .57 .79
-.018980 -.207967 .752 .45 .67
-.018730 -.206777 .737 .45 .64
-.018480 -.205582 .722 .45 .61
-.022 -.204961 .737 .43 .64
.001 -.195082 .737 .57 .64
-.022 -.200621 .688 .43 .49
-.017930 -.202882 .688 .46 .49
.001 -.192123 .688 .57 .49
-.022 -.197911 .653 .43 .37
-.017360 -.200098 .653 .46 .37
.001 -.189832 .653 .57 .37
-.022 -.194819 .618 .43 .23
-.016800 -.197110 .618 .46 .23
.001 -.187218 .618 .57 .23
-.016250 -.194125 .5835 .47 .09
-.065590 -.188388 .752 .21 .67
-.065570 -.187532 .737 .21 .64
-.065550 -.186677 .722 .21 .61
-.042600 -.194916 .752 .32 .67
-.042460 -.194041 .737 .32 .64
-.042330 -.193162 .722 .32 .61
-.069 -.188806 .737 .19 .64
.004310 -.193996 .752 .59 .67
.004610 -.192910 .737 .59 .64
.004900 -.191829 .722 .59 .61
.027130 -.186799 .752 .69 .67
.027440 -.185632 .737 .69 .64
.027750 -.184466 .722 .69 .61
.050 -.193756 .737 .80 .64
-.085 -.194754 .737 .08 .64
.075300 -.209996 .737 .94 .64
-.016070 -.192729 .567 .47 .05
-.020530 -.209768 .835 .44 .95
-.020700 -.209875 .841917 .44 .97
.075100 -.210923 .749254 .96 .67
.075650 -.208824 .722166 .96 .62
-.022690 -.188857 .557 .42 .04
-.026000 -.186921 .552 .40 .03
""", """
62 0 1
62 1 2
62 2 27
62 27 24
62 24 25
62 25 63
62 63 0
24 27 28 26
27 2 29 28
26 28 30 23
28 29 3 30
22 45 46 51
51 46 47 18
45 48 49 46
46 49 50 47
48 23 33 49
49 33 17 50
23 30 31 33
33 31 32 17
30 3 34 31
31 34 9 32
3 52 53 34
34 53 54 9
52 55 56 53
53 56 57 54
55 4 58 56
56 58 8 57
59 22 51
59 51 18
59 18 19
59 19 20
59 20 21
59 21 22
60 4 5
60 5 64
60 64 6
60 6 65
60 65 7
60 7 8
60 8 58
60 58 4
17 32 36 35
32 9 37 36
35 36 39 38
36 37 40 39
38 39 42 41
39 40 43 42
41 42 44 16
42 43 10 44
61 10 11
61 11 12
61 12 13
66 61 13
66 13 67
66 67 14
66 14 61
61 14 15
61 15 16
61 16 44
61 44 10
""", "brass", "tabard", modifiers=[{"type": "SOLIDIFY", "thickness": .0008, "offset": 0}])

part("relic_tabard_gilded_pointed_hem", """
-.153 -.146 .419 0 0
-.109 -.189 .391 .14 0
-.064 -.147 .368 .28 0
-.011 -.185 .337 .42 0
.038 -.142 .346 .56 0
.082 -.187 .379 .70 0
.119 -.151 .414 .84 0
.148 -.143 .434 1 0
-.153 -.146 .431 0 1
-.109 -.190 .403 .14 1
-.064 -.147 .380 .28 1
-.011 -.186 .349 .42 1
.038 -.142 .358 .56 1
.082 -.187 .391 .70 1
.119 -.151 .426 .84 1
.148 -.143 .446 1 1
""", """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
""", "brass", "tabard", modifiers=[{"type": "SUBSURF", "levels": 1}, {"type": "SOLIDIFY", "thickness": .0008, "offset": 0}])

part("relic_tabard_explicit_fringe_tassels", """
-.0015 0 0 0 1
.0015 0 0 1 1
-.0016 -.001 -.015 0 .52
.0014 -.001 -.015 1 .52
-.0010 .001 -.032 .15 0
.0010 .001 -.031 .85 .03
""", """
0 1 3 2
2 3 5 4
""", "brass", "tabard", modifiers=[{"type": "SOLIDIFY", "thickness": .001, "offset": 0}], instances=[
    {"location": [-.148, -.151, .415]}, {"location": [-.137, -.161, .408]},
    {"location": [-.126, -.173, .401]}, {"location": [-.115, -.184, .394]},
    {"location": [-.104, -.185, .386]}, {"location": [-.093, -.175, .380]},
    {"location": [-.082, -.164, .374]}, {"location": [-.071, -.153, .368]},
    {"location": [-.060, -.151, .361]}, {"location": [-.049, -.159, .354]},
    {"location": [-.038, -.167, .348]}, {"location": [-.027, -.175, .341]},
    {"location": [-.016, -.183, .335]}, {"location": [-.005, -.180, .335]},
    {"location": [.006, -.170, .337]}, {"location": [.017, -.160, .339]},
    {"location": [.028, -.150, .341]}, {"location": [.039, -.146, .344]},
    {"location": [.050, -.157, .352]}, {"location": [.061, -.168, .360]},
    {"location": [.072, -.179, .369]}, {"location": [.083, -.186, .378]},
    {"location": [.094, -.176, .388]}, {"location": [.105, -.165, .398]},
    {"location": [.116, -.154, .409]}, {"location": [.127, -.149, .419]},
    {"location": [.138, -.146, .427]}, {"location": [.146, -.144, .432]},
])

document = {
    "schema_version": 1, "component": "relics",
    "reference_notes": [
        "All marks, contours and finite instances are explicit source data. No procedural chains, cloth simulation, curve sweeps, primitive operators, scatter or text generation.",
        "Upper seals hang near X+/-0.17,Z1.53; four belt seals are distributed across the front waist. Parchment surfaces have independently authored bends, offsets and uneven ends.",
        "Ink strokes are deliberately sparse nonsemantic visual marks, not legible prayers or generated lettering. Paper wear and fine writing need painted image textures later.",
        "Nineteen individually positioned alternating chain links connect the approximate left belt anchor to a separately surfaced hollow bowl, open vent posts and contoured pointed canopy nearX.40,Z.60.",
        "Censer is a rigid draft attachment. Cloth trim and fringe follow the current authored front-tabard control folds approximately; full render/animation review must resolve local hover and clearance.",
        "Tabard cross is raised embroidery, not final thread texture. Twenty-eight fringe placements and the pointed hem are authored explicitly.",
        "Slot metadata separates upper chest seals, waist attachments and tabard decoration for later root-owned merging/atlas/binding.",
    ],
    "parts": PARTS,
}
(ROOT / "source" / "relics.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
print(f"relics: {len(PARTS)} authored parts, {sum(len(p['vertices']) for p in PARTS)} control vertices")
