"""Surveyed passerine surfaces and closed feather vanes, in metres.

All forms are authored cross-sections or bounded feather surfaces. The wing's
rigid feather fields follow its humerus, ulna and hand; no opaque tube stands
in for the folded flight-feather stack.
"""
import math
from mathutils import Vector

BODY = [
    [0, .051, .066, .002, .003, 'pelvis'],
    [0, .036, .072, .013, .012, 'pelvis'],
    [0, .019, .081, .023, .025, 'pelvis'],
    [0, .000, .087, .027, .030, 'chest'],
    [0, -.014, .094, .022, .028, 'chest'],
    [0, -.024, .108, .014, .023, 'neck'],
    [0, -.031, .122, .014, .019, 'head'],
    [0, -.041, .124, .017, .019, 'head'],
    [0, -.050, .124, .015, .016, 'head'],
    [0, -.058, .120, .009, .008, 'head'],
    [0, -.060, .119, .005, .004, 'head'],
]
WING = [( .021, -.010, .100), (.060, .006, .100), (.104, -.010, .101), (.139, .007, .098)]
LEG = [(.016, .011, .062), (.017, -.005, .055), (.017, .011, .031), (.017, -.001, .005)]


def atlas(u, v, tile):
    return ((tile % 4 + .015 + .97*u) / 4, (tile // 4 + .015 + .97*v) / 2)


class Surface:
    def __init__(self):
        self.vertices, self.faces, self.uv, self.weights, self.parts = [], [], [], [], []

    def add(self, name, vertices, faces, uv, weights):
        offset = len(self.vertices)
        assert len(vertices) == len(weights) and len(faces) == len(uv), name
        self.vertices.extend([list(v) for v in vertices])
        self.faces.extend([[i+offset for i in face] for face in faces])
        self.uv.extend(uv)
        self.weights.extend(weights)
        self.parts.append({'name': name, 'first_vertex': offset, 'vertices': len(vertices), 'faces': len(faces)})


def blend_weights(a, b, t):
    names = set(a) | set(b)
    return {name: a.get(name, 0)*(1-t)+b.get(name, 0)*t for name in names
            if a.get(name, 0)*(1-t)+b.get(name, 0)*t > 1e-8}


def loft(surface, name, sections, lod, tile=0, upright=False):
    sides, steps = [(32, 4), (20, 3), (12, 2)][lod]
    rings = []
    for index, (a, b) in enumerate(zip(sections, sections[1:])):
        previous, following = sections[max(0, index-1)], sections[min(len(sections)-1, index+2)]
        for step in range(steps):
            t = step / steps
            row = []
            for axis in range(5):
                p0, p1, p2, p3 = previous[axis], a[axis], b[axis], following[axis]
                value = .5*(2*p1+(p2-p0)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                row.append(max(.00002, value) if axis >= 3 else value)
            row.append(blend_weights(a[5], b[5], t))
            rings.append(row)
    rings.append(sections[-1])
    vertices, coordinates, weights = [], [], []
    for index, row in enumerate(rings):
        center = Vector(row[:3])
        tangent = (Vector(rings[min(index+1, len(rings)-1)][:3])-Vector(rings[max(0, index-1)][:3])).normalized()
        if upright:
            lateral, up = Vector((1, 0, 0)), Vector((0, 0, 1))
        else:
            reference = Vector((1, 0, 0)) if abs(tangent.x) < .8 else Vector((0, 1, 0))
            lateral = (reference-tangent*reference.dot(tangent)).normalized()
            up = tangent.cross(lateral).normalized()
        for side in range(sides):
            angle = math.tau*side/sides
            vertices.append(center + lateral*(row[3]*math.cos(angle)) + up*(row[4]*math.sin(angle)))
            coordinates.append(atlas(side/sides, index/(len(rings)-1), tile))
            weights.append(row[5])
    faces, uv = [], []
    for ring in range(len(rings)-1):
        for side in range(sides):
            face = [ring*sides+side, ring*sides+(side+1)%sides, (ring+1)*sides+(side+1)%sides, (ring+1)*sides+side]
            faces.append(face)
            uv.append([atlas(side/sides, ring/(len(rings)-1), tile), atlas((side+1)/sides, ring/(len(rings)-1), tile), atlas((side+1)/sides, (ring+1)/(len(rings)-1), tile), atlas(side/sides, (ring+1)/(len(rings)-1), tile)])
    for ring, reverse in [(0, True), (len(rings)-1, False)]:
        face = list(range(ring*sides, (ring+1)*sides))
        if reverse: face.reverse()
        faces.append(face)
        uv.append([atlas(.5+.4*math.cos(math.tau*(i % sides)/sides), .5+.4*math.sin(math.tau*(i % sides)/sides), tile) for i in face])
    surface.add(name, vertices, faces, uv, weights)


def feather(surface, name, path, width, lod, bone, tile=7, normal=(0, 0, 1)):
    """Closed, tapered asymmetric vane with real thickness and a subtle shaft."""
    rows = [0, .08, .20, .36, .54, .72, .87, .96, 1] if lod == 0 else [0, .16, .40, .68, .88, 1]
    columns = [-1, -.65, -.2, 0, .2, .65, 1] if lod == 0 else [-1, -.4, 0, .4, 1] if lod == 1 else [-1, 0, 1]
    a, b, c = map(Vector, path)
    forward = (c-a).normalized()
    normal = Vector(normal)
    lateral = forward.cross(normal).normalized()
    normal = lateral.cross(forward).normalized()
    vertices, coordinates = [], []
    for underside in [False, True]:
        for t in rows:
            center = a*(1-t)**2+b*(2*t*(1-t))+c*t*t
            taper = max(.008, math.sin(math.pi*(.045+t*.955))**.55)
            for across in columns:
                half_width = width*(.76 if across < 0 else 1)
                shaft = .00012*math.exp(-(across/.14)**2)*math.sin(math.pi*t)
                camber = width*.09*(1-across*across)*math.sin(math.pi*t)
                thickness = (-1 if underside else 1)*.000055
                vertices.append(center+lateral*(across*half_width*taper)+normal*(camber+shaft+thickness))
                coordinates.append(atlas((across+1)/2, t, tile))
    columns_count, panel = len(columns), len(rows)*len(columns)
    faces = []
    for layer in [0, 1]:
        for row in range(len(rows)-1):
            for column in range(columns_count-1):
                a = layer*panel+row*columns_count+column
                face = [a, a+1, a+1+columns_count, a+columns_count]
                faces.append(face[::-1] if layer else face)
    perimeter = list(range(columns_count))+[r*columns_count+columns_count-1 for r in range(1, len(rows))]
    perimeter += list(range(panel-2, panel-columns_count-1, -1))+[r*columns_count for r in range(len(rows)-2, 0, -1)]
    for index, a in enumerate(perimeter):
        b = perimeter[(index+1) % len(perimeter)]
        faces.append([a, b, b+panel, a+panel])
    surface.add(name, vertices, faces, [[coordinates[i] for i in face] for face in faces], [{bone: 1} for _ in vertices])


def bone_records():
    bones = [
        {'name': 'root', 'head': (0, 0, 0), 'tail': (0, 0, .04)},
        {'name': 'pelvis', 'head': (0, .015, .077), 'tail': (0, -.005, .088), 'parent': 'root'},
        {'name': 'chest', 'head': (0, -.005, .088), 'tail': (0, -.023, .109), 'parent': 'pelvis'},
        {'name': 'neck', 'head': (0, -.023, .109), 'tail': (0, -.036, .123), 'parent': 'chest'},
        {'name': 'head', 'head': (0, -.036, .123), 'tail': (0, -.059, .120), 'parent': 'neck'},
        {'name': 'jaw', 'head': (0, -.054, .118), 'tail': (0, -.074, .1155), 'parent': 'head'},
        {'name': 'tail', 'head': (0, .039, .073), 'tail': (0, .106, .057), 'parent': 'pelvis'},
    ]
    for side, label in [(1, 'L'), (-1, 'R')]:
        for chain, points, parent in [(['wing_upper', 'wing_lower', 'wing_hand'], WING, 'chest'), (['thigh', 'ankle', 'tarsus'], LEG, 'pelvis')]:
            for index, name in enumerate(chain):
                a, b = points[index:index+2]
                bones.append({'name': name+'_'+label, 'head': (a[0]*side, *a[1:]), 'tail': (b[0]*side, *b[1:]), 'parent': parent if index == 0 else chain[index-1]+'_'+label})
        bones.append({'name': 'foot_'+label, 'head': (.017*side, -.001, .005), 'tail': (.017*side, -.025, .004), 'parent': 'tarsus_'+label})
    return bones


def anatomy(lod):
    surface = Surface()
    loft(surface, 'continuous_body_neck_head', [[*row[:5], {row[5]: 1}] for row in BODY], lod, upright=True)
    for side, label in [(1, 'L'), (-1, 'R')]:
        def reflect(point): return (point[0]*side, *point[1:])
        # Ordered follicles along the ulna and hand. Closed overlapping vanes
        # carry both dorsal and ventral surfaces without alpha cards.
        for i in range([10, 8, 6][lod]):
            t = i/([10, 8, 6][lod]-1)
            base = (.103+t*.035, -.008+t*.016, .101-t*.003)
            tip = (.176-.024*t*t, .009+.063*t, .096-.010*t)
            middle = tuple((a+b)*.5 for a, b in zip(base, tip))
            feather(surface, f'primary_{label}_{i}', list(map(reflect, [base, middle, tip])), [.0075, .009, .012][lod], lod, 'wing_hand_'+label)
        for i in range([9, 7, 5][lod]):
            t = i/([9, 7, 5][lod]-1)
            base = (.048+t*.055, .010-t*.018, .100)
            tip = (.061+t*.050, .075-t*.010, .087)
            middle = ((base[0]+tip[0])*.5, (base[1]+tip[1])*.5, .098)
            feather(surface, f'secondary_{label}_{i}', list(map(reflect, [base, middle, tip])), [.0083, .010, .013][lod], lod, 'wing_lower_'+label, tile=3)
        for row in range(3 if lod < 2 else 2):
            count = [12, 8, 5][lod]
            for i in range(count):
                t = i/(count-1)
                x = .036+t*.079
                base = (x, .001-t*.008+row*.010, .102+row*.00045)
                end = (x+.010, base[1]+.024+row*.005, .100)
                mid = ((base[0]+end[0])*.5, (base[1]+end[1])*.5, .105)
                bone = 'wing_upper_' if x < .058 else 'wing_lower_' if x < .098 else 'wing_hand_'
                feather(surface, f'covert_{label}_{row}_{i}', list(map(reflect, [base, mid, end])), [.0058, .0075, .012][lod], lod, bone+label, tile=6)
        # Scapular contour feathers conceal the humeral insertion naturally.
        for i in range([8, 6, 4][lod]):
            t = i/([8, 6, 4][lod]-1)
            feather(surface, f'scapular_{label}_{i}', list(map(reflect, [(.019+t*.011, -.015+t*.008, .110), (.026+t*.008, .010+t*.009, .118), (.023+t*.006, .029+t*.010, .106)])), .006, lod, 'chest', tile=6)
        leg = [[*reflect(p), w, d, {bone+'_'+label: 1}] for p, w, d, bone in zip(LEG, [.0035, .0024, .0019, .0015], [.0045, .0025, .0020, .0014], ['thigh', 'ankle', 'tarsus', 'foot'])]
        loft(surface, 'scaly_leg_'+label, leg, lod, tile=5)
        loft(surface, 'tibial_feather_cuff_'+label, [
            [*reflect((.017, -.005, .055)), .005, .0055, {'ankle_'+label: 1}],
            [*reflect((.017, .001, .046)), .004, .0048, {'ankle_'+label: 1}],
            [*reflect((.017, .008, .036)), .0024, .0025, {'ankle_'+label: 1}],
        ], lod, tile=0)
        for toe in range(4):
            start = Vector((.017*side, -.001, .005))
            end = start+Vector(((toe-1)*.007*side, -.023 if toe < 3 else .021, -.0018))
            mid = start.lerp(end, .5)+Vector((0, 0, .0009))
            bone = {'foot_'+label: 1}
            loft(surface, f'toe_{label}_{toe}', [list(start)+[.0012, .0012, bone], list(mid)+[.00095, .00105, bone], list(end)+[.0006, .00065, bone]], lod, tile=5)
            direction = (end-start).normalized()
            claw_tip = end+direction*(.009 if toe == 3 else .004)+Vector((0, 0, -.0014))
            loft(surface, f'claw_{label}_{toe}', [list(end)+[.00065, .00065, bone], list(end.lerp(claw_tip, .55)+Vector((0, 0, .0003)))+[.00045, .00042, bone], list(claw_tip)+[.00004, .00004, bone]], lod, tile=2)
    for i in range([12, 10, 8][lod]):
        t = i/([12, 10, 8][lod]-1)
        x = (t-.5)*.031
        feather(surface, f'rectrix_{i}', [(x*.4, .037, .073), (x*.8, .078, .070), (x, .106-.003*abs(t-.5), .056)], [.0045, .0055, .007][lod], lod, 'tail', tile=1 if i in [0, [12, 10, 8][lod]-1] else 7)
    for i in range([17, 11, 7][lod]):
        t = i/([17, 11, 7][lod]-1)
        x = (t-.5)*.018
        y = -.040+.007*math.sin(i*2.37)
        height = .141+.009*(1-abs(2*t-1))+.0015*math.sin(i*1.73)
        feather(surface, f'crest_{i}', [(x, y, .139-.002*abs(2*t-1)), (x*.8, y+.008, height), (x*.65, y+.018, height-.001)], [.0018, .0026, .0035][lod], lod, 'head', tile=6)
    loft(surface, 'upper_bill', [[0, -.058, .120, .006, .004, {'head': 1}], [0, -.066, .118, .004, .0025, {'head': 1}], [0, -.076, .1158, .00006, .00006, {'head': 1}]], lod, tile=5, upright=True)
    loft(surface, 'lower_bill', [[0, -.058, .1165, .0055, .0015, {'jaw': 1}], [0, -.067, .1156, .0031, .001, {'jaw': 1}], [0, -.0757, .11565, .00005, .00005, {'jaw': 1}]], lod, tile=5, upright=True)
    return surface
