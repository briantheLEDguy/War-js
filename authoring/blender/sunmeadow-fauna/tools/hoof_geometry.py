"""Authored cloven horn walls, bevelled soles and fitted coronary profiles."""
import math


def add_deer_hoof(cage, foot, side, label, limb, lod, atlas):
    # Literal sole boundary, heel to pointed toe. The cleft is a real separation
    # between medial walls; the tapered crown continues inside the furred pastern.
    outline = [(-.005, .019), (.004, .020), (.010, .013), (.011, -.003),
               (.009, -.019), (.005, -.033), (.0005, -.042), (-.005, -.038),
               (-.009, -.025), (-.010, -.008), (-.009, .008)]
    outline.reverse()
    profiles = [(.001, .87, 1.00, .000), (.005, 1.00, 1.00, .000),
                (.019, .98, .88, .004), (.032, .89, .66, .009),
                (.046, .64, .41, .013), (.055, .45, .24, .014)]
    around_steps = [4, 2, 1][lod]; vertical_steps = [3, 2, 1][lod]
    perimeter = []
    for index in range(len(outline)):
        a, b, c, d = [outline[(index+offset)%len(outline)] for offset in [-1, 0, 1, 2]]
        for step in range(around_steps):
            t = step/around_steps
            perimeter.append([.5*(2*b[k]+(c[k]-a[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(2)])
    rings = []
    for index, (a, b) in enumerate(zip(profiles, profiles[1:])):
        for step in range(vertical_steps):
            t = step/vertical_steps
            rings.append([a[k]*(1-t)+b[k]*t for k in range(4)])
    rings.append(profiles[-1])
    count = len(perimeter)
    for toe in [-1, 1]:
        vertices, faces, coordinates = [], [], []
        for z, width, length, rearward in rings:
            for px, py in perimeter:
                local_x = px*width
                local_y = py*length+rearward
                angle = toe*.055
                x = foot[0]*side+toe*.0095+local_x*math.cos(angle)-local_y*math.sin(angle)
                y = foot[1]+local_y*math.cos(angle)+local_x*math.sin(angle)
                coronary = max(0, (z-.032)/.023)*max(0, py/.020)*.003
                vertices.append((x, y, z+coronary))
        for ring in range(len(rings)-1):
            for column in range(count):
                faces.append([ring*count+column, ring*count+(column+1)%count, (ring+1)*count+(column+1)%count, (ring+1)*count+column])
                coordinates.append([atlas(column/count, ring/(len(rings)-1), 7), atlas((column+1)/count, ring/(len(rings)-1), 7), atlas((column+1)/count, (ring+1)/(len(rings)-1), 7), atlas(column/count, (ring+1)/(len(rings)-1), 7)])
        for ring, reverse in [(0, True), (len(rings)-1, False)]:
            face = list(range(ring*count, (ring+1)*count))
            if reverse: face.reverse()
            faces.append(face)
            coordinates.append([atlas(.5+.4*math.cos(index/count*math.tau), .5+.4*math.sin(index/count*math.tau), 7) for index in range(count)])
        bone = f'hoof_{limb}_{label}'
        cage.add(f'cloven_hoof_{limb}_{label}_{toe}', vertices, faces, coordinates, [{bone: 1} for _ in vertices])
