"""Original street furnishings and infill architecture for the Aegis kit."""
import bpy
import math
import random

KINDS = ['rowhouse_1', 'rowhouse_2', 'lean_to', 'courtyard_tree', 'planter',
         'crate_stack', 'barrel_cluster', 'handcart', 'awning_1', 'awning_2',
         'washing_line', 'noticeboard', 'fountain']


def build_detail(kind, materials, box, beam, roof, house):
    def cylinder(name, position, radius, depth, material, vertices=16):
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=position)
        ob = bpy.context.object
        ob.name = name
        ob.data.materials.append(materials[material])
        bevel = ob.modifiers.new('rounded_edges', 'BEVEL')
        bevel.width = .035
        bevel.segments = 3
        return ob

    def foliage(position, scale, seed):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=position)
        ob = bpy.context.object
        ob.name = 'irregular_foliage'
        rng = random.Random(seed)
        for v in ob.data.vertices:
            v.co *= rng.uniform(.85, 1.13)
        ob.scale = scale
        ob.data.materials.append(materials['foliage'])
        for poly in ob.data.polygons:
            poly.use_smooth = True

    if kind.startswith('rowhouse'):
        house(1 if kind.endswith('1') else 4)
        sx, sy, sz = (.8, .72, 1.12) if kind.endswith('1') else (.95, .72, 1.23)
        for ob in bpy.context.scene.objects:
            for i, scale in enumerate((sx, sy, sz)):
                ob.location[i] *= scale
                ob.scale[i] *= scale
        return
    if kind == 'lean_to':
        box('workshop_room', (0, 0, 1.65), (4.6, 3.5, 3.3), 'plaster_lime')
        roof(5.1, 4, 1.6, 3.3, 'terracotta', 'plaster_lime')
        for x in [-1.6, 0, 1.6]:
            box('lean_to_post', (x, -1.82, 1.65), (.16, .16, 3.3), 'oak')
        box('workshop_door', (-.85, -1.83, 1.2), (1.1, .12, 2.4), 'oak')
        box('workshop_window', (.9, -1.83, 2), (.9, .12, 1), 'glow')
    elif kind == 'courtyard_tree':
        cylinder('tree_trunk', (0, 0, 2.4), .28, 4.8, 'oak')
        for i, (x, y, z) in enumerate([(-1, 0, 4.5), (1, .4, 5), (0, -.8, 5.8), (.2, .8, 6.3)]):
            beam('tree_branch', (0, 0, 3), (x, y, z), .18)
            foliage((x, y, z), (1.45, 1.3, 1.7), 30 + i)
        for x in [-1.05, 1.05]:
            box('tree_guard', (x, 0, .3), (.15, 2.2, .6), 'iron')
    elif kind == 'planter':
        box('planter_soil', (0, 0, .4), (2.1, 1.2, .8), 'oak')
        for x in [-1.1, 1.1]:
            box('planter_end', (x, 0, .5), (.15, 1.4, 1), 'limestone')
        for y in [-.65, .65]:
            box('planter_side', (0, y, .5), (2.3, .15, 1), 'limestone')
        for i, x in enumerate([-.65, 0, .65]):
            foliage((x, 0, 1), (.5, .45, .65), i)
    elif kind == 'crate_stack':
        for x, y, z in [(-.6, 0, .55), (.6, 0, .55), (0, 0, 1.65), (.8, 1, .45)]:
            box('shipping_crate', (x, y, z), (1.05, .95, 1.05), 'oak')
            for dx in [-.43, .43]:
                box('crate_banding', (x + dx, y - .49, z), (.12, .08, 1.07), 'iron')
            beam('crate_diagonal', (x - .45, y - .52, z - .45), (x + .45, y - .52, z + .45), .09)
    elif kind == 'barrel_cluster':
        for x, y in [(-.55, 0), (.6, .3), (-.3, 1)]:
            cylinder('oak_barrel', (x, y, .65), .48, 1.3, 'oak')
            for z in [.2, 1.1]:
                cylinder('barrel_hoop', (x, y, z), .5, .12, 'iron')
    elif kind == 'handcart':
        box('cart_bed', (0, 0, .65), (1.5, 2.2, .2), 'oak')
        for x in [-.75, .75]:
            box('cart_side', (x, 0, 1.05), (.12, 2.2, .7), 'oak')
            beam('cart_handle', (x, -.8, .7), (x, -2.2, 1), .1)
        box('cart_end', (0, 1.1, 1.05), (1.5, .12, .7), 'oak')
        for x in [-.95, .95]:
            wheel = cylinder('cart_wheel', (x, .35, .48), .48, .14, 'iron')
            wheel.rotation_euler.y = math.pi / 2
        for x in [-.35, .35]:
            box('cargo_sack', (x, .2, 1.1), (.6, .8, .65), 'canvas_gold', .15)
    elif kind.startswith('awning'):
        canvas = 'canvas_gold' if kind.endswith('1') else 'canvas_red'
        box('merchant_counter', (0, 0, 1), (3, 1.4, .9), 'oak')
        for x in [-1.6, 1.6]:
            for y in [-1, 1]:
                box('awning_post', (x, y, 1.65), (.13, .13, 3.3), 'oak')
        for i in range(8):
            box('striped_canvas', (-1.55 + i * .44, 0, 3.15), (.45, 2.5, .1), canvas if i % 2 else 'plaster_lime')
        for x in [-1, 0, 1]:
            box('market_goods', (x, 0, 1.65), (.65, .7, .5), 'canvas_gold', .14)
    elif kind == 'washing_line':
        for x in [-2.4, 2.4]:
            box('wash_post', (x, 0, 1.6), (.12, .12, 3.2), 'oak')
        beam('clothes_rope', (-2.4, 0, 3), (2.4, 0, 3), .035)
        for i, x in enumerate([-1.5, -.2, 1.2]):
            box('hanging_linen', (x, 0, 2.3), (.8, .04, 1.4), ['plaster_lime', 'canvas_red', 'canvas_gold'][i], .01)
    elif kind == 'noticeboard':
        for x in [-.9, .9]:
            box('notice_post', (x, 0, 1.2), (.16, .18, 2.4), 'oak')
        box('notice_back', (0, 0, 1.9), (2.2, .2, 1.5), 'oak')
        for x, z in [(-.6, 2.1), (.1, 1.65), (.65, 2.15)]:
            box('posted_notice', (x, -.12, z), (.45, .02, .55), 'plaster_lime', .005)
        roof(2.7, .8, .5, 2.8)
    elif kind == 'fountain':
        cylinder('fountain_plinth', (0, 0, .12), 2.1, .24, 'limestone', 24)
        cylinder('fountain_water', (0, 0, .4), 1.8, .14, 'copper', 24)
        for i in range(16):
            angle = i * math.tau / 16
            ob = box('basin_stone', (math.cos(angle) * 1.85, math.sin(angle) * 1.85, .45), (.72, .35, .7), 'limestone')
            ob.rotation_euler.z = angle + math.pi / 2
        cylinder('fountain_column', (0, 0, 1.2), .25, 2.2, 'stone')
        cylinder('fountain_bowl', (0, 0, 2.25), .85, .22, 'limestone')
