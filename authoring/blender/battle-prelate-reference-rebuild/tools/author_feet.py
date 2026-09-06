"""Serialize literal boot, sole, sabaton, heel and strap control meshes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = []


def part(name, points, faces, material="steel", bone="foot_L", modifiers=None,
         closed=False, creases=()):
    rows = [line.split() for line in points.strip().splitlines() if line.strip()]
    data = {"id": name, "slot": "feet", "rigid_bone": bone,
            "mirror_bone": bone.replace("_L", "_R"),
            "vertices": [{"id": f"v{i:03}", "co": [float(v) for v in r[:3]]}
                         for i, r in enumerate(rows)], "faces": [],
            "modifiers": [{"type": "MIRROR", "axis": "X"}] + (modifiers or []),
            "landmarks": {}, "seams": [], "sharp_edges": [],
            "creases": [{"edge": [f"v{a:03}", f"v{b:03}"], "value": value}
                        for a, b, value in creases], "closed": closed,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0],
                          "scale": [1, 1, 1]}}
    for index, line in enumerate(faces.strip().splitlines()):
        ids = [int(v) for v in line.split()]
        data["faces"].append({"id": f"f{index:03}",
            "vertices": [f"v{i:03}" for i in ids],
            "uv": [[float(v) for v in rows[i][3:5]] for i in ids],
            "material": material})
    PARTS.append(data)
    return data


part("boot_contoured_welt_and_sole", """
.120 -.245 .007 0 .19
.132 -.304 .002 .1 .04
.170 -.327 .000 .30 0
.247 -.326 .000 .66 0
.296 -.303 .003 .9 .05
.315 -.245 .008 1 .2
.303 -.111 .013 .95 .50
.288 .078 .004 .86 .92
.250 .100 .000 .70 1
.169 .095 .000 .3 1
.139 .070 .004 .13 .92
.129 -.090 .012 .03 .55
.120 -.245 .034 0 .19
.132 -.304 .032 .1 .04
.170 -.327 .027 .30 0
.247 -.326 .028 .66 0
.296 -.303 .033 .9 .05
.315 -.245 .036 1 .2
.303 -.111 .041 .95 .50
.288 .078 .045 .86 .92
.250 .100 .043 .70 1
.169 .095 .043 .3 1
.139 .070 .044 .13 .92
.129 -.090 .039 .03 .55
""", """
0 1 13 12
1 2 14 13
2 3 15 14
3 4 16 15
4 5 17 16
5 6 18 17
6 7 19 18
7 8 20 19
8 9 21 20
9 10 22 21
10 11 23 22
11 0 12 23
11 10 9 8 7 6 5 4 3 2 1 0
12 13 14 15 16 17 18 19 20 21 22 23
""", "leather", modifiers=[{"type": "BEVEL", "width": .006, "segments": 3}], closed=True)

part("boot_shaped_leather_upper", """
.146 -.307 .034 0 0
.178 -.316 .050 .25 0
.215 -.319 .056 .5 0
.254 -.314 .050 .75 0
.284 -.305 .034 1 0
.122 -.243 .038 0 .2
.162 -.247 .089 .25 .2
.214 -.249 .099 .5 .2
.267 -.246 .090 .75 .2
.313 -.241 .040 1 .2
.128 -.146 .050 0 .5
.165 -.149 .140 .25 .5
.217 -.151 .168 .5 .5
.273 -.147 .130 .75 .5
.308 -.143 .056 1 .5
.146 -.038 .081 0 .78
.165 -.041 .213 .25 .78
.218 -.045 .244 .5 .78
.270 -.038 .205 .75 .78
.293 -.032 .088 1 .78
.155 .080 .063 0 1
.177 .070 .190 .25 1
.220 .065 .214 .5 1
.258 .070 .186 .75 1
.282 .078 .065 1 1
.146 -.307 .028 0 0
.178 -.316 .025 .25 0
.215 -.319 .025 .5 0
.254 -.314 .026 .75 0
.284 -.305 .029 1 0
.310 -.241 .031 1 .2
.301 -.143 .035 1 .5
.287 -.032 .039 1 .78
.281 .078 .039 1 1
.258 .085 .039 .75 1
.220 .088 .039 .5 1
.177 .085 .039 .25 1
.154 .079 .039 0 1
.143 -.038 .035 0 .78
.130 -.146 .031 0 .5
.123 -.243 .029 0 .2
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
10 15 16 11
11 16 17 12
12 17 18 13
13 18 19 14
15 20 21 16
16 21 22 17
17 22 23 18
18 23 24 19
0 1 26 25
1 2 27 26
2 3 28 27
3 4 29 28
4 9 30 29
9 14 31 30
14 19 32 31
19 24 33 32
24 23 34 33
23 22 35 34
22 21 36 35
21 20 37 36
20 15 38 37
15 10 39 38
10 5 40 39
5 0 25 40
40 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39
""", "leather", modifiers=[{"type": "SUBSURF", "levels": 1}], closed=True)

part("sabaton_shaped_toecap", """
.143 -.308 .031 0 0
.176 -.325 .034 .25 0
.215 -.330 .035 .5 0
.258 -.324 .034 .75 0
.290 -.306 .032 1 0
.126 -.282 .038 0 .5
.166 -.289 .089 .25 .5
.214 -.293 .103 .5 .5
.270 -.288 .087 .75 .5
.308 -.280 .041 1 .5
.123 -.239 .040 0 1
.161 -.245 .108 .25 1
.214 -.250 .123 .5 1
.269 -.245 .106 .75 1
.315 -.237 .044 1 1
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
""", bone="toe_L", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .004, "offset": -1}],
    creases=[(0,1,.5),(1,2,.5),(2,3,.5),(3,4,.5),(0,5,.4),(5,10,.4),
             (4,9,.4),(9,14,.4),(10,11,.6),(11,12,.6),(12,13,.6),(13,14,.6)])

part("sabaton_first_articulated_lame", """
.123 -.257 .043 0 0
.162 -.263 .113 .25 0
.214 -.267 .128 .5 0
.270 -.262 .110 .75 0
.314 -.255 .047 1 0
.123 -.225 .046 0 .5
.161 -.231 .132 .25 .5
.215 -.235 .146 .5 .5
.272 -.229 .126 .75 .5
.315 -.221 .050 1 .5
.125 -.197 .052 0 1
.163 -.202 .145 .25 1
.216 -.208 .162 .5 1
.272 -.200 .140 .75 1
.313 -.193 .058 1 1
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
""", bone="toe_L", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .0035, "offset": -1}],
    creases=[(0,1,.8),(1,2,.8),(2,3,.8),(3,4,.8),(0,5,.5),(5,10,.5),
             (4,9,.5),(9,14,.5)])

part("sabaton_second_articulated_lame", """
.126 -.216 .054 0 0
.165 -.222 .149 .25 0
.216 -.226 .166 .5 0
.273 -.218 .142 .75 0
.313 -.211 .060 1 0
.130 -.181 .062 0 .5
.166 -.187 .170 .25 .5
.217 -.192 .188 .5 .5
.274 -.183 .159 .75 .5
.309 -.176 .066 1 .5
.135 -.147 .072 0 1
.168 -.153 .187 .25 1
.217 -.160 .205 .5 1
.272 -.150 .176 .75 1
.305 -.142 .078 1 1
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
""", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .0035, "offset": -1}],
    creases=[(0,1,.8),(1,2,.8),(2,3,.8),(3,4,.8),(0,5,.5),(5,10,.5),
             (4,9,.5),(9,14,.5)])

part("sabaton_instep_articulated_lame", """
.136 -.169 .074 0 0
.168 -.175 .190 .25 0
.218 -.180 .208 .5 0
.273 -.172 .181 .75 0
.304 -.164 .080 1 0
.141 -.129 .085 0 .5
.170 -.136 .211 .25 .5
.218 -.143 .227 .5 .5
.273 -.132 .204 .75 .5
.301 -.123 .093 1 .5
.147 -.091 .098 0 1
.172 -.098 .229 .25 1
.218 -.105 .244 .5 1
.269 -.094 .222 .75 1
.296 -.086 .111 1 1
""", """
0 5 6 1
1 6 7 2
2 7 8 3
3 8 9 4
5 10 11 6
6 11 12 7
7 12 13 8
8 13 14 9
""", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .004, "offset": -1}],
    creases=[(0,1,.8),(1,2,.8),(2,3,.8),(3,4,.8),(0,5,.5),(5,10,.5),
             (4,9,.5),(9,14,.5)])

part("sabaton_brass_toe_rim", """
.142 -.309 .031 0 0
.141 -.307 .040 0 1
.176 -.327 .034 .25 0
.176 -.324 .044 .25 1
.215 -.332 .035 .5 0
.215 -.329 .045 .5 1
.258 -.326 .034 .75 0
.258 -.323 .044 .75 1
.291 -.307 .032 1 0
.292 -.305 .041 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
""", "brass", "toe_L", [{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .002, "offset": 0}])

part("sabaton_brass_instep_border", """
.135 -.171 .074 0 0
.137 -.168 .082 0 1
.168 -.177 .190 .25 0
.168 -.174 .198 .25 1
.218 -.182 .208 .5 0
.218 -.179 .216 .5 1
.273 -.174 .181 .75 0
.273 -.171 .189 .75 1
.305 -.166 .080 1 0
.303 -.163 .088 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
""", "brass", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .002, "offset": 0}])

part("boot_heel_steel_counter", """
.140 -.008 .071 0 0
.151 .063 .054 .2 0
.175 .092 .050 .4 0
.248 .095 .049 .65 0
.286 .072 .052 .8 0
.299 -.011 .081 1 0
.144 -.006 .132 0 .5
.154 .068 .145 .2 .5
.178 .092 .149 .4 .5
.248 .094 .150 .65 .5
.280 .070 .142 .8 .5
.293 -.006 .148 1 .5
.151 -.004 .182 0 1
.161 .060 .207 .2 1
.183 .080 .212 .4 1
.244 .082 .210 .65 1
.272 .061 .201 .8 1
.285 -.002 .195 1 1
""", """
0 6 7 1
1 7 8 2
2 8 9 3
3 9 10 4
4 10 11 5
6 12 13 7
7 13 14 8
8 14 15 9
9 15 16 10
10 16 17 11
""", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .004, "offset": -1}])

part("boot_heel_brass_upper_lip", """
.150 -.005 .182 0 0
.150 -.005 .191 0 1
.160 .061 .207 .2 0
.160 .061 .216 .2 1
.183 .082 .212 .4 0
.183 .082 .221 .4 1
.244 .084 .210 .65 0
.244 .084 .219 .65 1
.273 .063 .201 .8 0
.273 .063 .210 .8 1
.286 -.001 .195 1 0
.286 -.001 .204 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
8 10 11 9
""", "brass", modifiers=[{"type": "SUBSURF", "levels": 1},
    {"type": "SOLIDIFY", "thickness": .002, "offset": 0}])

part("boot_outer_leather_buckle_strap", """
.293 -.098 .078 0 0
.293 -.099 .100 0 1
.300 -.046 .093 .25 0
.300 -.047 .115 .25 1
.298 .011 .100 .5 0
.298 .010 .122 .5 1
.285 .060 .094 .75 0
.285 .059 .116 .75 1
.255 .092 .085 1 0
.255 .091 .107 1 1
""", """
0 2 3 1
2 4 5 3
4 6 7 5
6 8 9 7
""", "leather", modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0}])

part("boot_outer_brass_buckle", """
.304 -.039 .091 0 0
.305 -.038 .126 0 1
.304 .005 .132 1 1
.303 .006 .097 1 0
.306 -.031 .099 .18 .20
.307 -.030 .120 .18 .80
.306 -.003 .124 .82 .80
.305 -.002 .103 .82 .20
""", """
0 1 5 4
1 2 6 5
2 3 7 6
3 0 4 7
""", "brass", modifiers=[{"type": "SOLIDIFY", "thickness": .003, "offset": 0},
    {"type": "BEVEL", "width": .0007, "segments": 2}])

part("boot_buckle_tongue", """
.309 -.020 .096 0 0
.309 -.016 .097 1 0
.310 -.015 .123 1 1
.310 -.019 .123 0 1
""", """
0 1 2 3
""", "brass", modifiers=[{"type": "SOLIDIFY", "thickness": .002, "offset": 0}])

data = {"schema_version": 1, "component": "feet", "reference_notes": [
    "Broad custom leather boot and contoured sole; four explicit overlapping steel sabaton pieces curve over the toe and instep.",
    "Two front plates use toe_L/toe_R; rear instep and heel pieces use foot_L/foot_R for animation-compatible articulation.",
    "Brass toe/instep/heel edging, a steel heel counter and explicitly authored leather strap with an open brass buckle are separate parts.",
    "All control coordinates and face connectivity are literal tables. No primitive meshes, profile sweeps, sampled curves or generated scatter.",
    "Per-corner UV layouts are provisional; root performs final texture packing and evaluated slot budget checks."
], "parts": PARTS}
(ROOT / "source/feet.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Feet: {len(PARTS)} parts, {sum(len(p['vertices']) for p in PARTS)} literal control vertices")
