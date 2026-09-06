"""Gothic exterior details, in Blender Z-up metres; hall collision stays separate."""
import math
import bpy
from mathutils import Vector


def decorate_citadel(materials, box):
    def mesh(name, vertices, faces, material):
        data = bpy.data.meshes.new(name)
        data.from_pydata(vertices, [], faces)
        data.update()
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        data.materials.append(materials[material])
        # Match the box/roof UV layer so joining meshes cannot orphan these UVs.
        uv = data.uv_layers.new(name='UVMap')
        for face in data.polygons:
            axis = max(range(3), key=lambda a: abs(face.normal[a]))
            axes = [a for a in range(3) if a != axis]
            for loop in face.loop_indices:
                v = data.vertices[data.loops[loop].vertex_index].co
                uv.data[loop].uv = (v[axes[0]] / 4, v[axes[1]] / 4)
        return obj

    def rod(name, a, b, width=.16, material='limestone'):
        direction = Vector(b) - Vector(a)
        obj = box(name, (Vector(a) + Vector(b)) / 2,
                  (width, width, direction.length), material)
        obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        return obj

    def taper(name, x, y, base, height, radius, top=0, material='slate'):
        vertices = [(x + r * math.cos(i * math.pi / 4 + math.pi / 8),
                     y + r * math.sin(i * math.pi / 4 + math.pi / 8), z)
                    for z, r in [(base, radius), (base + height, max(top, .035))]
                    for i in range(8)]
        faces = [(i, (i + 1) % 8, (i + 1) % 8 + 8, i + 8) for i in range(8)]
        faces += [tuple(reversed(range(8))), tuple(range(8, 16))]
        return mesh(name, vertices, faces, material)

    def spire(x, y, base, radius, height, elaborate=False):
        # A splayed stone shoulder carries an octagonal lantern and needle roof.
        taper('spire_shoulder', x, y, base, height * .1, radius * 1.12, radius * .88, 'limestone')
        taper('spire_lantern', x, y, base + height * .1, height * .22,
              radius * .88, radius * .88, 'stone')
        for z, r in [(base + height * .1, radius * 1.06),
                     (base + height * .32, radius * .94)]:
            taper('spire_cornice', x, y, z, .5, r, r, 'limestone')
        start = base + height * .32
        taper('slender_slate_needle', x, y, start, height * .66, radius * .91)
        rod('spire_finial', (x, y, base + height * .95),
            (x, y, base + height + 1), .16, 'copper')
        for i in range(8):
            angle = i * math.pi / 4 + math.pi / 8
            dx, dy = math.cos(angle), math.sin(angle)
            rod('lantern_corner_shaft', (x + dx * radius * .9, y + dy * radius * .9, base + height * .1),
                (x + dx * radius * .9, y + dy * radius * .9, start), .22)
            if elaborate or i % 2 == 0:
                rod('needle_hip_rib', (x + dx * radius * .92, y + dy * radius * .92, start),
                    (x, y, base + height * .98), .13, 'copper')
        if elaborate:
            face = radius * .814
            for dx, dy, angle in [(0, -face, 0), (0, face, math.pi),
                                  (-face, 0, -math.pi/2), (face, 0, math.pi/2)]:
                lancet(x + dx, y + dy, base + height * .115, radius * .65, height * .17, angle)
            for z, factor in [(.48, .68), (.66, .42), (.82, .2)]:
                taper('needle_collar', x, y, base + height * z, .32,
                      radius * factor, radius * factor, 'limestone')

    def profile(width, height):
        r = width / 2
        spring = height - math.sqrt(3) * r
        left = [(r + 2 * r * math.cos(math.pi - i * math.pi / 18),
                 spring + 2 * r * math.sin(math.pi - i * math.pi / 18)) for i in range(7)]
        return [(-r, 0)] + left + [(-x, z) for x, z in reversed(left[:-1])] + [(r, 0)]

    def lancet(x, y, bottom, width, height, rotation=0):
        # Raised masonry surrounds a dark setback; glazing is never a glowing strip.
        def world(p, depth):
            u, z = p
            return (x + u * math.cos(rotation) - depth * math.sin(rotation),
                    y + u * math.sin(rotation) + depth * math.cos(rotation), bottom + z)
        outer = profile(width + .7, height + .48)
        inner = [(u, z + .25) for u, z in profile(width, height)]
        n = len(outer)
        vertices = [world(p, d) for d in [-.32, .12] for path in [outer, inner] for p in path]
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces += [(i, j, n + j, n + i), (i, 2*n+i, 2*n+j, j),
                      (n+i, n+j, 3*n+j, 3*n+i)]
        mesh('carved_pointed_window_reveal', vertices, faces, 'limestone')
        mesh('recessed_leaded_glass', [world(p, -.08) for p in inner],
             [tuple(reversed(range(n)))], 'citadel_glass')
        rod('window_mullion', world((0, .25), -.38), world((0, height - .18), -.38), .12, 'stone')
        for z in [height * .3, height * .58]:
            rod('window_transom', world((-width/2, z), -.38), world((width/2, z), -.38), .1, 'stone')

    glass = bpy.data.materials.new('aegis_citadel_leaded_glass')
    glass.use_nodes = True
    shader = glass.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.045, .085, .095, 1)
    shader.inputs['Metallic'].default_value = .25
    shader.inputs['Roughness'].default_value = .3
    materials['citadel_glass'] = glass

    # The central tower is the single dominant vertical, framed by unequal pairs.
    before_crossing = set(bpy.context.scene.objects)
    box('high_crossing_tower', (0, 0, 52), (17, 20, 32), 'limestone')
    for z in [39, 52, 67.5]:
        box('crossing_string_course', (0, 0, z), (18, 21, .7), 'stone')
    for x in [-8, 8]:
        for y in [-9.5, 9.5]:
            box('crossing_corner_shaft', (x, y, 52), (1.3, 1.3, 33), 'stone')
            spire(x, y, 68, 1.4, 13)
    for x in [-4.3, 0, 4.3]:
        lancet(x, -10.1, 49, 2.2, 14)
        lancet(x, 10.1, 49, 2.2, 14, math.pi)
    for x, angle in [(-8.6, -math.pi/2), (8.6, math.pi/2)]:
        for y in [-5, 0, 5]: lancet(x, y, 49, 2.2, 14, angle)
    spire(0, 0, 68, 8.7, 57, True)
    for obj in set(bpy.context.scene.objects) - before_crossing: obj.location.y -= 18

    for x in [-44, 44]:
        for y in [-46, 10]:
            spire(x, y, 44, 5.65, 34 if y < 0 else 43, True)
            for dx in [-4.7, 4.7]:
                box('tower_edge_buttress', (x + dx, y - 5.55, 23), (.9, .7, 42), 'limestone')
            for z in [12, 28]: lancet(x, y - 5.58, z, 2.2, 9)

    for x in [-31, -21, -11, 11, 21, 31]:
        # Stepped buttresses stay within the pre-existing front-wall footprint.
        box('buttress_upper_shaft', (x, -50, 34), (1.65, 2.2, 10), 'limestone')
        for z, width, depth in [(10, 2.7, 3), (23, 2.5, 2.8), (32, 2.1, 2.5)]:
            box('buttress_weathered_cap', (x, -50, z), (width, depth, .45), 'limestone')
        spire(x, -50, 39, 1.35, 12 if abs(x) == 21 else 15)
    for x in [-26, -16, 16, 26]:
        lancet(x, -49.05, 7, 3.25, 12)
        lancet(x, -49.05, 22, 3.25, 11)
    for x, angle in [(-36.05, -math.pi/2), (36.05, math.pi/2)]:
        for y in [-43, -34, -25, -16, -7, 2, 9]: lancet(x, y, 16, 2.4, 14, angle)

    # A deep, pointed entrance crown preserves the full rectangular gate opening.
    for layer in range(3):
        for side in [-1, 1]:
            rod('portal_arch_order', (side * (6.3 + layer * .5), -50.4 + layer * .3, 13),
                (0, -50.4 + layer * .3, 23 + layer * .6), .55, 'limestone')
    lancet(0, -49.05, 25, 4.8, 8)
    for x in [-7, 7]: spire(x, -50, 14, .85, 12)

    # High flying braces cast real shadows without occupying the playable court.
    for side in [-1, 1]:
        for y in [-44, 8]:
            rod('flying_buttress_upper', (side*43, y, 42), (side*34, y, 35), .85)
            rod('flying_buttress_lower', (side*43, y, 37), (side*34, y, 32), .65)
    for x in [-28, -20, 20, 28]:
        for y in [-34, -2]: spire(x, y, 46.7 - abs(x) * 11 / 37.5, 1.7, 19)
