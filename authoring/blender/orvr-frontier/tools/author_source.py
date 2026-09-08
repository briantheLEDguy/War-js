"""Serialize newly authored frontier joinery and metalwork control cages.

The coordinate tables are the design source. There are no primitive constructors,
surface-of-revolution generators, randomized meshes, or inherited proxy geometry.
The section stitcher only connects successive literal eight-corner cage loops;
finite transforms repeat finished components (wheel joinery, rivets, hinges).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = {}


def cage(name, points, faces, material, finish=None, description=""):
    vertices = [[float(v) for v in row.split()] for row in points.strip().splitlines() if row.strip()]
    topology = [[int(v) for v in row.split()] for row in faces.strip().splitlines() if row.strip()]
    # Stable, explicit corner UV records survive import and all finishing stages.
    # The main face's longest construction direction follows the grain's V axis.
    corners = []
    for face in topology:
        p, q, r = [vertices[i] for i in face[:3]]
        a, b = [q[i]-p[i] for i in range(3)], [r[i]-p[i] for i in range(3)]
        normal = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        axes = [i for i in range(3) if i != max(range(3), key=lambda i: abs(normal[i]))]
        lengths = {axis: max(v[axis] for v in vertices)-min(v[axis] for v in vertices) for axis in axes}
        axes.sort(key=lambda axis: lengths[axis])
        uv = [[round(.025+.95*(vertices[index][axis]-min(v[axis] for v in vertices))/max(lengths[axis],.001),6) for axis in axes] for index in face]
        corners.append(uv)
    PARTS[name] = {"id": name, "description": description, "vertices": vertices, "faces": topology,
                   "corner_uv": corners, "material": material, "finish": finish or [], "source_kind": "literal_authored_control_cage"}
    return name


def stitched(name, points, material, finish=None, closed=True, description=""):
    rows = [row for row in points.strip().splitlines() if row.strip()]
    assert len(rows) % 8 == 0, name
    faces = [f"{i+k} {i+(k+1)%8} {i+8+(k+1)%8} {i+8+k}" for i in range(0,len(rows)-8,8) for k in range(8)]
    if closed:
        faces += ["7 6 5 4 3 2 1 0", " ".join(str(len(rows)-8+i) for i in range(8))]
    return cage(name, points, "\n".join(faces), material, finish, description)


BEVEL = [{"type": "BEVEL", "width": .009, "segments": 3}]
FORGED = [{"type": "BEVEL", "width": .004, "segments": 3}]
SOFT = [{"type": "SUBSURF", "levels": 2}]

# Swept, adzed reach: splayed forward shoulder, curved lower line, keyed ends.
stitched("oak_swept_reach", """
-.100 -1.80 .67
-.065 -1.82 .64
.063 -1.82 .64
.099 -1.80 .67
.104 -1.80 .79
.067 -1.82 .83
-.064 -1.82 .83
-.103 -1.80 .79
-.147 -1.17 .57
-.094 -1.17 .54
.093 -1.17 .54
.144 -1.17 .57
.144 -1.17 .78
.095 -1.17 .82
-.095 -1.17 .82
-.147 -1.17 .78
-.151 .65 .56
-.095 .65 .53
.095 .65 .53
.153 .65 .56
.149 .65 .80
.094 .65 .84
-.096 .65 .84
-.151 .65 .80
-.103 1.65 .67
-.068 1.68 .64
.068 1.68 .64
.106 1.65 .67
.104 1.65 .82
.067 1.68 .86
-.066 1.68 .86
-.103 1.65 .82
""", "aged_oak", BEVEL, description="Adzed oak chassis reach with shouldered axle seats and narrowed pegged tips.")

# Bowed strakes follow the tub's changing breadth. These are fitted planks, not a box body.
cage("wagon_strake", """
.81 -1.56 .92
.91 -.78 .86
.94 .10 .85
.89 1.05 .88
.80 1.59 .96
.91 -1.60 1.17
1.02 -.78 1.12
1.05 .10 1.11
1.01 1.05 1.14
.91 1.61 1.20
.88 -1.56 .93
.98 -.78 .87
1.01 .10 .86
.96 1.05 .89
.87 1.59 .97
.98 -1.60 1.17
1.09 -.78 1.12
1.12 .10 1.11
1.08 1.05 1.14
.98 1.61 1.20
""", """
0 1 6 5
1 2 7 6
2 3 8 7
3 4 9 8
10 15 16 11
11 16 17 12
12 17 18 13
13 18 19 14
0 10 11 1
1 11 12 2
2 12 13 3
3 13 14 4
5 6 16 15
6 7 17 16
7 8 18 17
8 9 19 18
0 5 15 10
4 14 19 9
""", "aged_oak", BEVEL, "Curved overlapping cart strake with intentionally uneven adzed edges.")

cage("deck_plank", """
-.11 -1.53 .91
.10 -1.52 .91
.13 -.74 .87
.12 .15 .87
.11 1.54 .93
-.12 1.56 .93
-.13 .14 .89
-.12 -.72 .88
-.11 -1.53 1.00
.10 -1.52 1.00
.13 -.74 .96
.12 .15 .96
.11 1.54 1.02
-.12 1.56 1.02
-.13 .14 .98
-.12 -.72 .97
""", """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
7 0 8 15
8 9 10 11 12 13 14 15
7 6 5 4 3 2 1 0
""", "aged_oak", BEVEL, "Full-length lightly crowned deck plank with wedge fit and real underside.")

cage("wheel_felloe", """
0 -.092 .610
0 -.092 .746
.193 -.092 .721
.373 -.092 .646
.305 -.092 .528
.158 -.092 .589
0 .092 .610
0 .092 .746
.193 .092 .721
.373 .092 .646
.305 .092 .528
.158 .092 .589
""", """
0 1 2 5
5 2 3 4
6 11 8 7
11 10 9 8
1 7 8 2
2 8 9 3
0 5 11 6
5 4 10 11
0 6 7 1
4 3 9 10
""", "aged_oak", [{"type":"BEVEL","width":.006,"segments":3}], "Individually fitted 30-degree wheel felloe with explicit continuous inner and outer arcs and a full-thickness mortise seat.")

# Proper annular wheel rim patch: front inner/outer and rear outer/inner.
cage("wheel_iron_tire", """
0 -.112 .731
.0954 -.112 .7247
.1892 -.112 .7061
.2797 -.112 .6754
.3655 -.112 .6331
0 -.112 .782
.1021 -.112 .7753
.2024 -.112 .7554
.2993 -.112 .7225
.391 -.112 .6772
0 .112 .731
.0954 .112 .7247
.1892 .112 .7061
.2797 .112 .6754
.3655 .112 .6331
0 .112 .782
.1021 .112 .7753
.2024 .112 .7554
.2993 .112 .7225
.391 .112 .6772
""", """
0 1 6 5
1 2 7 6
2 3 8 7
3 4 9 8
10 15 16 11
11 16 17 12
12 17 18 13
13 18 19 14
5 6 16 15
6 7 17 16
7 8 18 17
8 9 19 18
0 10 11 1
1 11 12 2
2 12 13 3
3 13 14 4
0 5 15 10
4 14 19 9
""", "forged_iron", FORGED, "Forged tire arc with continuous thickness and an exposed hammered rolling surface.")

stitched("wheel_spoke", """
-.050 -.056 .145
.050 -.056 .145
.064 -.035 .145
.064 .035 .145
.050 .056 .145
-.050 .056 .145
-.064 .035 .145
-.064 -.035 .145
-.039 -.043 .34
.039 -.043 .34
.052 -.027 .34
.052 .027 .34
.039 .043 .34
-.039 .043 .34
-.052 .027 .34
-.052 -.027 .34
-.044 -.050 .645
.044 -.050 .645
.054 -.033 .645
.054 .033 .645
.044 .050 .645
-.044 .050 .645
-.054 .033 .645
-.054 -.033 .645
""", "fresh_oak", BEVEL, description="Tapered octagonal oak spoke with thicker mortise shoulders.")

stitched("wheel_hub", """
.130 -.170 0
.092 -.170 .092
0 -.170 .130
-.092 -.170 .092
-.130 -.170 0
-.092 -.170 -.092
0 -.170 -.130
.092 -.170 -.092
.19 -.105 0
.134 -.105 .134
0 -.105 .19
-.134 -.105 .134
-.19 -.105 0
-.134 -.105 -.134
0 -.105 -.19
.134 -.105 -.134
.19 .105 0
.134 .105 .134
0 .105 .19
-.134 .105 .134
-.19 .105 0
-.134 .105 -.134
0 .105 -.19
.134 .105 -.134
.130 .210 0
.092 .210 .092
0 .210 .130
-.092 .210 .092
-.130 .210 0
-.092 .210 -.092
0 .210 -.130
.092 .210 -.092
""", "aged_oak", SOFT, description="Shouldered turned hub with deep spoke seat and projecting axle collar.")

cage("forged_rosette", """
0 -.022 .075
.031 -.022 .031
.075 -.022 0
.031 -.022 -.031
0 -.022 -.075
-.031 -.022 -.031
-.075 -.022 0
-.031 -.022 .031
0 -.051 0
""", """
0 1 8
1 2 8
2 3 8
3 4 8
4 5 8
5 6 8
6 7 8
7 0 8
""", "forged_iron", [{"type":"SOLIDIFY","thickness":.009},{"type":"BEVEL","width":.003,"segments":3}], "Four-petal forged washer and raised clinch fastener.")

cage("cloth_canopy", """
-1.04 -1.66 1.48
-.98 -1.64 2.15
-.74 -1.64 2.59
-.39 -1.62 2.84
0 -1.60 2.91
.40 -1.62 2.83
.74 -1.65 2.59
.99 -1.66 2.12
1.05 -1.67 1.46
-1.11 -.81 1.57
-1.035 -.79 2.13
-.80 -.79 2.55
-.44 -.79 2.78
.025 -.79 2.84
.46 -.79 2.75
.81 -.80 2.52
1.035 -.81 2.10
1.11 -.83 1.55
-1.09 .15 1.48
-1.04 .14 2.17
-.78 .14 2.59
-.40 .14 2.83
0 .14 2.9
.40 .14 2.83
.77 .14 2.59
1.04 .15 2.14
1.09 .15 1.50
-1.12 .94 1.53
-1.07 .94 2.08
-.81 .94 2.52
-.44 .94 2.77
-.02 .94 2.82
.42 .94 2.77
.81 .94 2.53
1.04 .94 2.09
1.11 .94 1.54
-1.02 1.72 1.51
-.99 1.70 2.15
-.74 1.71 2.59
-.40 1.70 2.83
0 1.70 2.91
.40 1.70 2.83
.74 1.71 2.59
.99 1.70 2.15
1.02 1.72 1.50
""", "\n".join(f"{j*9+i} {j*9+i+1} {(j+1)*9+i+1} {(j+1)*9+i}" for j in range(4) for i in range(8)), "campaign_canvas", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.012}], "Tensioned wagon canvas with hand-shaped sag between five bowed ribs; open ends.")
PARTS['cloth_canopy']['corner_uv']=[[[index%9/8,index//9/4] for index in face] for face in PARTS['cloth_canopy']['faces']]

cage("canopy_seam", """
-1.057 -1.68 1.48
-1.01 -1.68 2.15
-.76 -1.68 2.60
-.41 -1.68 2.85
0 -1.68 2.935
.41 -1.68 2.85
.76 -1.68 2.60
1.01 -1.68 2.15
1.057 -1.68 1.48
-1.057 -1.62 1.48
-1.01 -1.62 2.15
-.76 -1.62 2.60
-.41 -1.62 2.85
0 -1.62 2.935
.41 -1.62 2.85
.76 -1.62 2.60
1.01 -1.62 2.15
1.057 -1.62 1.48
""", "\n".join(f"{i} {i+1} {i+10} {i+9}" for i in range(8)), "leather", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.015}], "Raised bound canopy edge and ridge rib reinforcement.")

stitched("carved_drawbar", """
-.10 -1.63 .72
-.062 -1.63 .68
.062 -1.63 .68
.10 -1.63 .72
.10 -1.63 .86
.062 -1.63 .90
-.062 -1.63 .90
-.10 -1.63 .86
-.088 -2.20 .68
-.055 -2.20 .65
.055 -2.20 .65
.088 -2.20 .68
.088 -2.20 .79
.055 -2.20 .83
-.055 -2.20 .83
-.088 -2.20 .79
-.052 -3.45 .93
-.032 -3.45 .91
.032 -3.45 .91
.052 -3.45 .93
.052 -3.45 1.01
.032 -3.45 1.03
-.032 -3.45 1.03
-.052 -3.45 1.01
-.070 -3.59 .98
-.040 -3.59 .94
.040 -3.59 .94
.070 -3.59 .98
.070 -3.59 1.03
.040 -3.59 1.07
-.040 -3.59 1.07
-.070 -3.59 1.03
""", "fresh_oak", BEVEL, description="Bentwood drawbar with narrower spring section and shouldered harness tip.")

stitched("sack", """
-.19 -.21 0
.19 -.21 0
.29 -.13 0
.29 .13 0
.19 .21 0
-.19 .21 0
-.29 .13 0
-.29 -.13 0
-.27 -.29 .20
.24 -.29 .20
.38 -.17 .20
.38 .17 .20
.23 .29 .20
-.27 .29 .20
-.36 .17 .20
-.36 -.17 .20
-.24 -.26 .55
.21 -.24 .57
.29 -.16 .58
.29 .14 .56
.20 .25 .58
-.24 .24 .55
-.30 .13 .56
-.31 -.15 .55
-.035 -.063 .72
.035 -.060 .72
.063 -.033 .72
.060 .039 .72
.025 .060 .72
-.035 .058 .72
-.065 .031 .72
-.062 -.039 .72
-.09 -.075 .79
.075 -.086 .81
.115 -.021 .80
.083 .080 .79
.029 .065 .81
-.069 .081 .79
-.084 .043 .80
-.10 -.028 .80
""", "grain_sacking", SOFT, description="Bulging woven grain sack with asymmetrical settled belly, puckered tied neck and loose gathered mouth.")

stitched("curved_stanchion", """
-.105 -.105 .82
.105 -.105 .82
.145 -.065 .82
.145 .065 .82
.105 .105 .82
-.105 .105 .82
-.145 .065 .82
-.145 -.065 .82
-.11 -.095 1.18
.11 -.095 1.18
.14 -.060 1.18
.14 .060 1.18
.11 .095 1.18
-.11 .095 1.18
-.14 .060 1.18
-.14 -.060 1.18
-.27 -.085 1.70
-.09 -.085 1.70
-.06 -.050 1.70
-.06 .050 1.70
-.09 .085 1.70
-.27 .085 1.70
-.30 .050 1.70
-.30 -.050 1.70
-.43 -.080 2.29
-.27 -.080 2.29
-.24 -.045 2.29
-.24 .045 2.29
-.27 .080 2.29
-.43 .080 2.29
-.46 .045 2.29
-.46 -.045 2.29
""", "aged_oak", BEVEL, description="Continuous naturally crooked oak stanchion with flared shouldered foot and inward upper seat.")

cage("ram_hide_roof", """
-1.35 -1.97 2.35
-.81 -2.05 2.88
0 -2.10 3.19
.80 -2.02 2.88
1.36 -1.98 2.36
-1.37 -1.05 2.41
-.81 -1.05 2.88
.02 -1.05 3.18
.82 -1.05 2.88
1.38 -1.05 2.40
-1.34 .02 2.34
-.83 .02 2.84
-.02 .02 3.13
.81 .02 2.85
1.35 .02 2.34
-1.38 1.03 2.40
-.82 1.03 2.89
0 1.03 3.20
.82 1.03 2.88
1.37 1.03 2.42
-1.35 2.00 2.35
-.81 2.04 2.88
0 2.07 3.19
.81 2.02 2.89
1.35 1.97 2.35
""", "\n".join(f"{j*5+i} {j*5+i+1} {(j+1)*5+i+1} {(j+1)*5+i}" for j in range(4) for i in range(4)), "waxed_hide", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.075}], "Overlapping wet-hide mantlet roof, stitched ridgeline, scalloped exposed edges.")

stitched("ram_trunk", """
.20 -2.36 -.13
.20 -2.36 .13
.11 -2.36 .23
-.11 -2.36 .23
-.20 -2.36 .13
-.20 -2.36 -.13
-.11 -2.36 -.23
.11 -2.36 -.23
.26 -1.40 -.16
.25 -1.40 .17
.13 -1.40 .27
-.14 -1.40 .27
-.26 -1.40 .17
-.27 -1.40 -.16
-.14 -1.40 -.26
.14 -1.40 -.26
.29 .60 -.17
.27 .60 .19
.13 .60 .28
-.16 .60 .29
-.29 .60 .17
-.28 .60 -.18
-.14 .60 -.28
.15 .60 -.26
.22 2.09 -.14
.21 2.09 .15
.11 2.09 .22
-.12 2.09 .22
-.22 2.09 .13
-.21 2.09 -.15
-.10 2.09 -.22
.12 2.09 -.22
""", "fresh_oak", BEVEL, description="Debarked, adzed whole-oak ram trunk: retained uneven growth and tapered impact socket.")

# Hand-shaped ram-mask planes include brow, narrowed muzzle and proud cheek.
stitched("ram_forged_head", """
.225 -2.16 -.15
.235 -2.16 .15
.14 -2.16 .255
-.14 -2.16 .255
-.235 -2.16 .15
-.225 -2.16 -.15
-.12 -2.16 -.245
.12 -2.16 -.245
.33 -2.46 -.19
.37 -2.46 .16
.23 -2.46 .36
-.23 -2.46 .36
-.37 -2.46 .16
-.33 -2.46 -.19
-.16 -2.46 -.32
.16 -2.46 -.32
.21 -2.82 -.16
.25 -2.82 .04
.13 -2.82 .18
-.13 -2.82 .18
-.25 -2.82 .04
-.21 -2.82 -.16
-.13 -2.82 -.23
.13 -2.82 -.23
.17 -2.98 -.14
.18 -2.98 .025
.10 -2.98 .105
-.10 -2.98 .105
-.18 -2.98 .025
-.17 -2.98 -.14
-.10 -2.98 -.185
.10 -2.98 -.185
""", "forged_iron", [{"type":"BEVEL","width":.025,"segments":4}], description="Original broad-brow bull mask, sculpted cheek planes and an armored impact muzzle.")

stitched("forged_horn", """
.22 -2.42 .15
.28 -2.50 .15
.40 -2.50 .21
.44 -2.42 .29
.40 -2.34 .35
.28 -2.34 .35
.22 -2.37 .29
.20 -2.42 .21
.41 -2.32 .29
.45 -2.40 .32
.54 -2.40 .39
.58 -2.32 .46
.54 -2.24 .50
.45 -2.24 .47
.40 -2.27 .41
.38 -2.32 .34
.48 -2.14 .50
.51 -2.18 .52
.55 -2.17 .57
.57 -2.13 .62
.53 -2.09 .63
.50 -2.09 .60
.47 -2.10 .56
.46 -2.13 .53
.40 -2.03 .71
.416 -2.048 .716
.43 -2.046 .731
.434 -2.028 .743
.42 -2.012 .743
.403 -2.012 .735
.392 -2.018 .723
.391 -2.033 .714
""", "burnished_brass", SOFT, description="Swept defensive horn with changing cross-section and inward tip; original bull heraldry.")

cage("hinge_scroll", """
0 -.03 -.07
.54 -.03 -.07
.85 -.03 -.02
1.02 -.03 .13
.99 -.03 .32
.80 -.03 .40
.65 -.03 .30
.69 -.03 .21
.80 -.03 .29
.89 -.03 .27
.91 -.03 .16
.80 -.03 .075
.53 -.03 .07
0 -.03 .07
""", """
0 1 12 13
1 2 11 12
2 3 10 11
3 4 9 10
4 5 8 9
5 6 7 8
""", "forged_iron", [{"type":"SOLIDIFY","thickness":.05},{"type":"BEVEL","width":.009,"segments":3}], "Forged tapering strap hinge with hand-drawn returning volute and separate fasteners.")

# Eight authored horizontal sections retain the cauldron cavity and rolled lip.
stitched("oil_cauldron", """
.12 0 .16
.085 .085 .16
0 .12 .16
-.085 .085 .16
-.12 0 .16
-.085 -.085 .16
0 -.12 .16
.085 -.085 .16
.44 0 .25
.311 .311 .25
0 .44 .25
-.311 .311 .25
-.44 0 .25
-.311 -.311 .25
0 -.44 .25
.311 -.311 .25
.64 0 .70
.45 .45 .70
0 .64 .70
-.45 .45 .70
-.64 0 .70
-.45 -.45 .70
0 -.64 .70
.45 -.45 .70
.56 0 1.03
.396 .396 1.03
0 .56 1.03
-.396 .396 1.03
-.56 0 1.03
-.396 -.396 1.03
0 -.56 1.03
.396 -.396 1.03
.59 0 1.095
.418 .418 1.095
0 .59 1.095
-.418 .418 1.095
-.59 0 1.095
-.418 -.418 1.095
0 -.59 1.095
.418 -.418 1.095
.51 0 1.095
.361 .361 1.095
0 .51 1.095
-.361 .361 1.095
-.51 0 1.095
-.361 -.361 1.095
0 -.51 1.095
.361 -.361 1.095
.49 0 1.01
.346 .346 1.01
0 .49 1.01
-.346 .346 1.01
-.49 0 1.01
-.346 -.346 1.01
0 -.49 1.01
.346 -.346 1.01
.54 0 .68
.382 .382 .68
0 .54 .68
-.382 .382 .68
-.54 0 .68
-.382 -.382 .68
0 -.54 .68
.382 -.382 .68
.34 0 .33
.24 .24 .33
0 .34 .33
-.24 .24 .33
-.34 0 .33
-.24 -.24 .33
0 -.34 .33
.24 -.24 .33
.08 0 .29
.057 .057 .29
0 .08 .29
-.057 .057 .29
-.08 0 .29
-.057 -.057 .29
0 -.08 .29
.057 -.057 .29
""", "sooted_iron", [{"type":"SUBSURF","levels":3}], description="Deep hollow riveted iron cauldron with continuous inner wall, substantial bottom and rolled upper lip.")

cage("cauldron_pouring_spout", """
-.17 -.45 .93
-.22 -.62 .98
-.20 -.77 1.01
-.11 -.80 1.00
0 -.81 .99
.11 -.80 1.00
.20 -.77 1.01
.22 -.62 .98
.17 -.45 .93
-.15 -.46 1.07
-.21 -.62 1.12
-.19 -.79 1.15
-.10 -.85 1.14
0 -.88 1.13
.10 -.85 1.14
.19 -.79 1.15
.21 -.62 1.12
.15 -.46 1.07
""", "\n".join(f"{i} {i+1} {i+10} {i+9}" for i in range(8)), "sooted_iron", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.045}], "Shaped downward-flow pouring spout, rolled to match the cauldron lip.")

cage("cauldron_bracket", """
-.055 -.30 .55
-.055 -.31 .75
-.055 -.11 1.01
-.055 .15 1.04
-.055 .78 1.30
-.055 .95 1.24
-.055 .95 .15
-.055 .81 .15
-.055 .79 .92
-.055 .12 .77
-.055 -.06 .67
.055 -.30 .55
.055 -.31 .75
.055 -.11 1.01
.055 .15 1.04
.055 .78 1.30
.055 .95 1.24
.055 .95 .15
.055 .81 .15
.055 .79 .92
.055 .12 .77
.055 -.06 .67
""", """
0 1 12 11
1 2 13 12
2 3 14 13
3 4 15 14
4 5 16 15
5 6 17 16
6 7 18 17
7 8 19 18
8 9 20 19
9 10 21 20
10 0 11 21
0 10 9 8 7 6 5 4 3 2 1
11 12 13 14 15 16 17 18 19 20 21
""", "forged_iron", FORGED, "Full-thickness swept parapet bracket with curved elbow and raised mounting tongue.")

stitched("catapult_throwing_arm", """
-.18 -.30 .65
.18 -.30 .65
.23 -.21 .68
.23 .21 .68
.18 .30 .65
-.18 .30 .65
-.23 .21 .68
-.23 -.21 .68
-.145 -.16 1.65
.145 -.16 1.65
.18 -.10 1.65
.18 .10 1.65
.145 .16 1.65
-.145 .16 1.65
-.18 .10 1.65
-.18 -.10 1.65
-.09 .25 2.69
.09 .25 2.69
.125 .30 2.69
.125 .47 2.69
.09 .52 2.69
-.09 .52 2.69
-.125 .47 2.69
-.125 .30 2.69
-.13 .40 3.12
.13 .40 3.12
.17 .46 3.12
.17 .61 3.12
.13 .67 3.12
-.13 .67 3.12
-.17 .61 3.12
-.17 .46 3.12
""", "fresh_oak", BEVEL, description="Continuous crooked throwing arm, heavy torsion heel, tapered middle and spoon mounting shoulders.")

cage("catapult_spoon", """
-.10 .37 2.99
-.36 .35 3.21
-.47 .40 3.53
-.36 .47 3.73
0 .49 3.81
.36 .47 3.73
.47 .40 3.53
.36 .35 3.21
.10 .37 2.99
-.04 .60 3.13
-.24 .61 3.28
-.31 .62 3.49
-.24 .63 3.61
0 .65 3.66
.24 .63 3.61
.31 .62 3.49
.24 .61 3.28
.04 .60 3.13
0 .73 3.39
""", """
0 1 10 9
1 2 11 10
2 3 12 11
3 4 13 12
4 5 14 13
5 6 15 14
6 7 16 15
7 8 17 16
8 0 9 17
9 10 18
10 11 18
11 12 18
12 13 18
13 14 18
14 15 18
15 16 18
16 17 18
17 9 18
""", "leather", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.055}], "Concave rawhide projectile spoon with raised lip, tapered heel and a continuous deep pocket.")

stitched("twisted_rope_strand", """
-.031 -.95 .01
-.017 -.95 -.024
.017 -.95 -.024
.031 -.95 .01
.024 -.95 .034
.006 -.95 .044
-.020 -.95 .037
-.035 -.95 .022
.007 -.47 .042
.041 -.47 .027
.045 -.47 -.007
.011 -.47 -.021
-.013 -.47 -.014
-.023 -.47 .004
-.016 -.47 .030
-.001 -.47 .045
.052 .05 .008
.038 .05 -.026
.004 .05 -.030
-.010 .05 .004
-.003 .05 .028
.015 .05 .038
.041 .05 .031
.056 .05 .016
.010 .52 -.025
-.024 .52 -.011
-.028 .52 .023
.006 .52 .037
.030 .52 .030
.040 .52 .012
.033 .52 -.014
.018 .52 -.029
-.027 .99 .009
-.013 .99 .043
.021 .99 .047
.035 .99 .013
.028 .99 -.011
.010 .99 -.021
-.016 .99 -.014
-.031 .99 .001
""", "rope", [{"type":"SUBSURF","levels":2}], description="Individually laid rope strand with literal changing section orientations and slight load sag.")

cage("ram_suspension_sling", """
.22 -.07 2.89
.24 -.07 2.39
.33 -.07 1.74
.30 -.07 1.43
.18 -.07 1.34
0 -.07 1.32
-.18 -.07 1.34
-.30 -.07 1.43
-.33 -.07 1.74
-.24 -.07 2.39
-.22 -.07 2.89
.22 .07 2.89
.24 .07 2.39
.33 .07 1.74
.30 .07 1.43
.18 .07 1.34
0 .07 1.32
-.18 .07 1.34
-.30 .07 1.43
-.33 .07 1.74
-.24 .07 2.39
-.22 .07 2.89
""", "\n".join(f"{i} {i+1} {i+12} {i+11}" for i in range(10)), "leather", [{"type":"SUBSURF","levels":2},{"type":"SOLIDIFY","thickness":.025}], "Continuous U-shaped load-bearing leather sling under the ram trunk, rising to its roof suspension beam.")

stitched("joinery_collar", """
-.108 -.121 0
.108 -.121 0
.158 -.076 0
.158 .076 0
.108 .121 0
-.108 .121 0
-.158 .076 0
-.158 -.076 0
-.113 -.126 .16
.113 -.126 .16
.164 -.080 .16
.164 .080 .16
.113 .126 .16
-.113 .126 .16
-.164 .080 .16
-.164 -.080 .16
""", "forged_iron", [{"type":"SOLIDIFY","thickness":.016},{"type":"BEVEL","width":.006,"segments":3}], closed=False, description="Open-ended forged octagonal joinery band with flared upper edge and substantial steel wall.")

cage("gate_oak_leaf", """
0 -.16 .08
.42 -.17 .05
.48 -.16 1.50
.46 -.17 3.20
.43 -.16 4.71
.22 -.16 4.79
.01 -.16 4.72
-.015 -.17 3.20
-.012 -.16 1.50
0 .16 .08
.42 .17 .05
.48 .16 1.50
.46 .17 3.20
.43 .16 4.71
.22 .16 4.79
.01 .16 4.72
-.015 .17 3.20
-.012 .16 1.50
""", """
0 1 10 9
1 2 11 10
2 3 12 11
3 4 13 12
4 5 14 13
5 6 15 14
6 7 16 15
7 8 17 16
8 0 9 17
0 8 7 6 5 4 3 2 1
9 10 11 12 13 14 15 16 17
""", "aged_oak", [{"type":"BEVEL","width":.018,"segments":3}], "Full oak gate plank with cambers, sloping weathered top and nonuniform lower edge.")

cage("gate_crest", """
0 -.21 3.12
-.49 -.21 3.37
-.62 -.21 3.93
-.53 -.21 4.47
0 -.21 4.75
.53 -.21 4.47
.62 -.21 3.93
.49 -.21 3.37
0 -.28 3.30
-.36 -.28 3.47
-.48 -.28 3.96
-.40 -.28 4.36
0 -.28 4.59
.40 -.28 4.36
.48 -.28 3.96
.36 -.28 3.47
0 -.36 4.02
""", """
0 1 9 8
1 2 10 9
2 3 11 10
3 4 12 11
4 5 13 12
5 6 14 13
6 7 15 14
7 0 8 15
8 9 16
9 10 16
10 11 16
11 12 16
12 13 16
13 14 16
14 15 16
15 8 16
""", "burnished_brass", [{"type":"SOLIDIFY","thickness":.055},{"type":"BEVEL","width":.014,"segments":3}], "Original elongated kite boss, repoussé centre and raised continuous brass border.")


def inst(part, location=(0,0,0), rotation=(0,0,0), scale=(1,1,1), name=None, parent=None):
    record = {"part": part, "location": list(location), "rotation_degrees": list(rotation), "scale": list(scale)}
    if name: record["name"] = name
    if parent: record["parent"] = parent
    return record


ANGLES = [0,30,60,90,120,150,180,210,240,270,300,330]


def wheels(locations, size=1):
    result=[]
    for number, location in enumerate(locations):
        group=f"wheel_{number}"
        result.append({"group":group,"location":list(location),"rotation_degrees":[0,0,90],"scale":[size,size,size]})
        result.append(inst("wheel_hub", parent=group))
        for angle in ANGLES:
            for part in ("wheel_felloe","wheel_iron_tire","wheel_spoke"):
                result.append(inst(part,rotation=(0,angle,0),parent=group))
        for offset in (-.23,.23):
            result.append(inst("forged_rosette",location=(0,offset,0),rotation=(0,0,180 if offset>0 else 0),scale=(1.5,1.5,1.5),parent=group))
    return result


def chassis(wheel_scale=1, wheel_y=1.15):
    result=[inst("oak_swept_reach",location=(x,0,0)) for x in (-.75,.75)]
    axle_height=.79*wheel_scale
    result += [inst("oak_swept_reach",location=(0,y,.06-(.79-axle_height)),rotation=(0,0,90),scale=(1,.91,1)) for y in (-wheel_y,wheel_y)]
    result += wheels([(-1.47,-wheel_y,axle_height),(1.47,-wheel_y,axle_height),(-1.47,wheel_y,axle_height),(1.47,wheel_y,axle_height)],wheel_scale)
    return result


wagon=chassis()
wagon += [inst("deck_plank",location=(x,0,0)) for x in (-.78,-.52,-.26,0,.26,.52,.78)]
for side in (-1,1):
    for height, width in ((0,1),(.245,1.105),(.49,1.21)):
        wagon.append(inst("wagon_strake",location=(0,0,height),scale=(side*width,1,1)))
    for y in (-1.35,0,1.37):
        wagon.append(inst("curved_stanchion",location=(side*1.09,y,0),scale=(side*.36,.42,.65)))
        for z in (1.06,1.30,1.55):
            wagon.append(inst("forged_rosette",location=(side*1.21,y,z),rotation=(0,0,90*side),scale=(.72,.72,.72)))
wagon += [inst("cloth_canopy")]
wagon += [inst("canopy_seam",location=(0,y,0)) for y in (0,3.36)]
wagon += [inst("carved_drawbar",location=(x,0,0)) for x in (-.61,.61)]
wagon += [inst("sack",location=p,rotation=(0,0,r)) for p,r in [((-.45,-.4,1.03),12),((.26,-.3,1.03),-18),((-.42,.5,1.03),25),((.33,.6,1.03),-35),((0,.10,1.55),6)]]

ram=chassis(.86,1.31)
ram += [inst("curved_stanchion",location=(side*1.05,y,-.33),scale=(side,1,1.4)) for side in (-1,1) for y in (-1.5,1.5)]
ram += [inst("ram_hide_roof"),inst("ram_trunk",location=(0,0,1.63)),inst("ram_forged_head",location=(0,0,1.63))]
ram += [inst("forged_horn",location=(0,0,1.63),scale=(side,1,1)) for side in (-1,1)]
ram += [inst("ram_suspension_sling",location=(0,y,0)) for y in (-1.13,1.24)]
ram += [inst("oak_swept_reach",location=(0,y,2.61),rotation=(0,0,90),scale=(.65,.47,.30)) for y in (-1.13,1.24)]
ram += [inst("deck_plank",location=(x,0,-.06),scale=(1,1.14,1)) for x in (-.71,-.45,.45,.71)]
ram += [inst("forged_rosette",location=(side*1.31,y,2.47),rotation=(0,55*side,0),scale=(.70,.70,.70)) for side in (-1,1) for y in (-1.61,-.53,.56,1.61)]
ram += [inst("forged_rosette",location=(side*.28,-2.70,1.80),rotation=(0,0,side*18),scale=(.80,.80,.38)) for side in (-1,1)]
ram += [inst("joinery_collar",location=(side*1.05,y,.90),scale=(side,1,1)) for side in (-1,1) for y in (-1.5,1.5)]

oil=[inst("oil_cauldron")]
oil += [inst("cauldron_bracket",location=(x,0,0)) for x in (-.65,.65)]
for x in (-.67,.67):
    trunnion=inst("wheel_hub",location=(x,0,.82),rotation=(0,0,90),scale=(.62,.75,.62))
    trunnion['material_override']='forged_iron'
    oil.append(trunnion)
oil += [inst("forged_rosette",location=(x,-.42,z),scale=(.65,.65,.65)) for x in (-.30,0,.30) for z in (.48,.75)]

catapult=chassis(.86,1.30)
catapult += [inst("curved_stanchion",location=(side*.86,-.05,0),scale=(side,1,1.0)) for side in (-1,1)]
catapult += [inst("catapult_throwing_arm",name="throwing_arm"),inst("catapult_spoon",name="projectile_spoon")]
catapult += [inst("twisted_rope_strand",location=(0,-.02,.88+z),rotation=(0,0,90),scale=(1,1.12,1)) for z in (-.14,-.08,-.02,.04,.10,.16)]
for side in (-1,1):
    bearing=inst("wheel_hub",location=(side*1.03,0,.91),rotation=(0,0,90),scale=(1.3,1.4,1.3)); bearing['material_override']='forged_iron'; catapult.append(bearing)
    catapult += [inst("joinery_collar",location=(side*.86,-.05,.88)),inst("joinery_collar",location=(side*.79,-.05,1.45),scale=(1,.91,1))]
    catapult += [inst("forged_rosette",location=(side*.81,-.18,1.52))]
catapult += [inst("oak_swept_reach",location=(0,-.01,1.46),rotation=(0,0,90),scale=(.70,.71,.42))]
catapult += [inst("sack",location=(-.57,1.19,.89),scale=(.8,.8,.8)),inst("sack",location=(.46,1.18,.91),scale=(.8,.8,.8))]

gate=[]
for side in (-1,1):
    group=f"gate_leaf_{'right' if side>0 else 'left'}"
    gate.append({"group":group,"location":[side*2.85,0,0],"rotation_degrees":[0,0,0],"scale":[1,1,1]})
    gate += [inst("gate_oak_leaf",location=(-side*x,0,0),scale=(side,1,1),parent=group) for x in (.48,.96,1.44,1.92,2.40,2.88)]
    gate += [inst("hinge_scroll",location=(-side*.12,-.19,z),scale=(-side*2.25,1,2.0),parent=group) for z in (.69,2.15,3.61)]
    gate += [inst("gate_crest",location=(-side*1.41,0,-.36),parent=group)]
    gate += [inst("ram_forged_head",location=(-side*1.41,.62,3.64),scale=(.45,.45,.45),parent=group)]
    gate += [inst("forged_horn",location=(-side*1.41,.62,3.64),scale=(horn_side*.45,.45,.45),parent=group) for horn_side in (-1,1)]
    gate += [inst("forged_rosette",location=(-side*x,-.28,z),scale=(1.2,1.2,1.2),parent=group) for x in (.20,.77,1.34,1.91,2.41) for z in (.69,2.15,3.61)]

ASSETS = {
    "frontier_supply_wagon": {"name":"Sunmeadow covered supply wagon","instances":wagon,"collision_hint":{"width":3.5,"depth":5.4,"height":3.0},"limitations":["Named wheel pivots are exported, but no draft animal or skeletal locomotion rig is included; caravan movement must not imply approved animal coverage."]},
    "frontier_battering_ram": {"name":"Bull-brow mantlet ram","instances":ram,"collision_hint":{"width":3.5,"depth":5.2,"height":3.3},"limitations":["Ram suspension requires gameplay-driven animation; this package provides named parts, not combat animation clips."]},
    "frontier_oil_cauldron": {"name":"Parapet tipping oil cauldron","instances":oil,"collision_hint":{"width":1.7,"depth":1.6,"height":1.3},"limitations":["Oil liquid and fire effects are runtime systems; no liquid surface is exported."]},
    "frontier_field_catapult": {"name":"Frontier torsion field catapult","instances":catapult,"collision_hint":{"width":3.5,"depth":3.7,"height":3.9},"limitations":["Named throwing assembly pivot and wheel pivots are exported; release/reload animation still requires implementation."]},
    "frontier_keep_gate": {"name":"Oak and scroll-iron double keep gate","instances":gate,"collision_hint":{"width":5.9,"depth":.6,"height":4.9},"limitations":["Includes two hinged leaves only; keep masonry and broken gate state are separate future assets."]},
}

MATERIALS = {
    "aged_oak":{"basecolor":[105,72,43],"roughness":.78,"metallic":0,"paint":"wood"},
    "fresh_oak":{"basecolor":[157,114,63],"roughness":.68,"metallic":0,"paint":"wood"},
    "forged_iron":{"basecolor":[48,55,62],"roughness":.46,"metallic":.92,"paint":"metal"},
    "sooted_iron":{"basecolor":[29,34,37],"roughness":.68,"metallic":.88,"paint":"metal"},
    "burnished_brass":{"basecolor":[165,117,46],"roughness":.36,"metallic":.85,"paint":"metal"},
    "campaign_canvas":{"basecolor":[70,91,105],"roughness":.89,"metallic":0,"paint":"cloth"},
    "grain_sacking":{"basecolor":[162,136,88],"roughness":.95,"metallic":0,"paint":"cloth"},
    "leather":{"basecolor":[66,39,25],"roughness":.69,"metallic":0,"paint":"leather"},
    "waxed_hide":{"basecolor":[80,58,36],"roughness":.61,"metallic":0,"paint":"leather"},
    "rope":{"basecolor":[169,139,83],"roughness":.94,"metallic":0,"paint":"cloth"},
}


def main():
    (ROOT/"source").mkdir(parents=True,exist_ok=True)
    source={"schema_version":1,"units":"metres","up":"Z","front":"-Y","source_policy":"Literal newly authored control cages and finite finished-part placements. No generated primitives.",
            "parts":PARTS,"assets":ASSETS,"materials":MATERIALS,"review_status":"unreviewed_source"}
    (ROOT/"source"/"frontier_collection.json").write_text(json.dumps(source,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"parts":len(PARTS),"assets":len(ASSETS),"control_vertices":sum(len(p["vertices"]) for p in PARTS.values())}))


if __name__=="__main__": main()
