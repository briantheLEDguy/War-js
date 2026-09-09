"""Original feather pigment, closed-vane barb relief, and horn/scute atlases."""
from pathlib import Path
import math
import bpy
import numpy as np


def material(root, lod):
    tile_size = [512, 256, 128][lod]
    y, x = np.mgrid[:tile_size, :tile_size].astype(np.float32)
    u, v = x/(tile_size-1), y/(tile_size-1)
    color = np.zeros((tile_size*2, tile_size*4, 3), dtype=np.float32)
    normal = np.zeros_like(color)
    orm = np.zeros_like(color)
    for tile in range(8):
        rgb = np.zeros((tile_size, tile_size, 3), dtype=np.float32)
        relief = np.zeros_like(u)
        rough = np.full_like(u, .83)
        if tile == 0:
            rgb[:] = [.185, .124, .068]
            belly = np.exp(-((u-.75)/.18)**4)
            belly *= np.clip((v-.08)/.14, 0, 1)*np.clip((.94-v)/.20, 0, 1)
            rgb = rgb*(1-belly[..., None])+np.array([.43, .37, .27])*belly[..., None]
            rng = np.random.default_rng(719)
            streaks = np.zeros_like(u)
            for _ in range(270):
                cx, cy = rng.uniform(0, 1), rng.uniform(0, 1)
                width, length = rng.uniform(.002, .005), rng.uniform(.010, .027)
                dv = (v-cy)/length
                taper = np.clip(1-dv*.5, .15, 1.5)
                streaks += np.exp(-((u-cx-.02*(v-cy))/(width*taper))**2-dv**4)
            clean_belly = belly*np.clip((.44-v)/.18, 0, 1)
            rgb *= 1-np.minimum(.68, streaks*.65*(1-clean_belly))[..., None]
            relief = .004*np.sin(u*430+v*37)*np.sin(v*617-u*23)
        elif tile in [1, 3, 6, 7]:
            rgb[:] = [.080, .052, .028] if tile != 1 else [.47, .43, .34]
            edges = np.clip((np.abs(u-.5)-.32)/.15, 0, 1)**1.4
            if tile == 6:
                edges = np.maximum(edges, np.clip((v-.79)/.19, 0, 1))
            rgb = rgb*(1-edges[..., None]*.76)+np.array([.265, .185, .106])*edges[..., None]*.76
            shaft = np.exp(-((u-.5)/.010)**2)
            barb_phase = v*295+np.abs(u-.5)*95+np.sin(v*61)*.08
            barbs = np.sin(barb_phase*math.tau)
            rgb *= (1+.045*barbs)[..., None]
            rgb += shaft[..., None]*np.array([.022, .016, .009])
            relief = .0013*barbs + .009*shaft
            if tile == 3:
                trailing = np.clip((v-.958)/.033, 0, 1)
                rgb = rgb*(1-trailing[..., None])+np.array([.43, .40, .32])*trailing[..., None]
        elif tile == 2:
            rgb[:] = [.032, .021, .013]
            rough[:] = .57
        elif tile == 4:
            radius = np.sqrt(((u-.5)/.48)**2+((v-.5)/.48)**2)
            iris = np.clip((radius-.56)/.22, 0, 1)
            rgb[:] = [.0035, .0028, .002]
            rgb += iris[..., None]*np.array([.020, .012, .005])
            rough[:] = .19
        else:
            rgb[:] = [.19, .115, .060]
            scutes = np.exp(-((np.mod(v*17, 1)-.03)/.09)**2)
            rgb *= (1-scutes*.20)[..., None]
            relief = -.0025*scutes
            rough[:] = .64
        gy, gx = np.gradient(relief)
        normals = np.stack([-gx*tile_size*.3, -gy*tile_size*.3, np.ones_like(u)], axis=-1)
        normals /= np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-8)
        row, col = (tile//4)*tile_size, (tile%4)*tile_size
        color[row:row+tile_size, col:col+tile_size] = np.clip(rgb, 0, 1)
        normal[row:row+tile_size, col:col+tile_size] = normals*.5+.5
        orm[row:row+tile_size, col:col+tile_size] = np.stack([np.ones_like(u), rough, np.zeros_like(u)], axis=-1)
    images = {}
    for channel, pixels in [('basecolor', color), ('normal', normal), ('orm', orm)]:
        image = bpy.data.images.new(f'skylark_v2_lod{lod}_{channel}', width=tile_size*4, height=tile_size*2, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        rgba = np.ones((tile_size*2, tile_size*4, 4), dtype=np.float32)
        rgba[:, :, :3] = pixels
        image.pixels.foreach_set(rgba.ravel())
        image.file_format = 'PNG'
        image.filepath_raw = str(root/'textures'/f'skylark_v2_lod{lod}_{channel}.png')
        image.save()
        image.pack()
        images[channel] = image
    mat = bpy.data.materials.new(f'skylark_v2_plumage_lod{lod}')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    base = nodes.new('ShaderNodeTexImage'); base.image = images['basecolor']
    links.new(base.outputs['Color'], shader.inputs['Base Color'])
    packed = nodes.new('ShaderNodeTexImage'); packed.image = images['orm']
    separate = nodes.new('ShaderNodeSeparateColor')
    links.new(packed.outputs['Color'], separate.inputs[0])
    links.new(separate.outputs['Green'], shader.inputs['Roughness'])
    links.new(separate.outputs['Blue'], shader.inputs['Metallic'])
    normal_image = nodes.new('ShaderNodeTexImage'); normal_image.image = images['normal']
    normal_node = nodes.new('ShaderNodeNormalMap')
    normal_node.inputs['Strength'].default_value = .6
    links.new(normal_image.outputs['Color'], normal_node.inputs['Color'])
    links.new(normal_node.outputs[0], shader.inputs['Normal'])
    return mat
