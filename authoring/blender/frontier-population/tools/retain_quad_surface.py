"""Retain the source's continuous quad anatomy, with fitting helpers removed."""
import bpy
import bmesh
import gzip
import json
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for family in ['civic_humanoid_v2_m','civic_humanoid_v2_f','mire_brutish_v1_m']:
    source=ROOT/'foundations'/f'{family}.source.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    body=bpy.data.objects['body_'+family]
    bpy.ops.object.select_all(action='DESELECT');body.hide_set(False);body.select_set(True)
    bpy.context.view_layer.objects.active=body
    if body.data.shape_keys:bpy.ops.object.shape_key_remove(all=True,apply_mix=True)
    body_group=body.vertex_groups['body'].index
    retained={v.index for v in body.data.vertices if any(g.group==body_group and g.weight>0 for g in v.groups)}
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in retained],context='VERTS')
    bm.to_mesh(body.data);bm.free()
    vertices=[list(body.matrix_world@v.co) for v in body.data.vertices]
    data={'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':'metres','upAxis':'Z',
          'vertices':vertices,'faces':[list(f.vertices) for f in body.data.polygons],
          'faceUvs':[[list(body.data.uv_layers.active.data[i].uv) for i in face.loop_indices] for face in body.data.polygons],
          'vertexGroups':{str(g.index):g.name for g in body.vertex_groups},
          'weights':[[[g.group,g.weight] for g in v.groups] for v in body.data.vertices]}
    path=ROOT/'foundations'/f'{family}.quad-surface.json.gz'
    path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    print('RETAINED_QUADS',family,len(vertices),len(data['faces']),flush=True)
