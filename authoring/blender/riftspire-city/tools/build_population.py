"""Riftbound inhabitants: new fitted headgear, silhouettes and faction dress.

Uses the project's reviewed human anatomy/rigs; keeps that provenance separate
from the independently authored crater architecture.
"""
import bpy,bmesh,math,json,hashlib,numpy as np,sys
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
for kind,source in [('chaos','chr_aegis_city_guard_standard.glb'),('dark_elf','chr_aegis_people_courtier_lod1.glb'),('greenskin','chr_npc_greenskin_m_ambient_m.glb')]:
 if any(a.startswith('--assets=') for a in sys.argv) and kind not in next(a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--assets=')):continue
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/assets/models'/source))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 body=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
 for ob in list(bpy.context.scene.objects):
  if ob.type=='MESH' and ob!=body and not any(m.type=='ARMATURE' for m in ob.modifiers):bpy.data.objects.remove(ob,do_unlink=True)
 if kind=='greenskin':
  bpy.ops.object.select_all(action='DESELECT')
  for ob in bpy.context.scene.objects:
   if ob.type=='MESH':ob.select_set(True)
  bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
 # Remove the inherited realm's metal insignia. The remaining outfit gets
 # dedicated materials, while source face/eye textures retain anatomical detail.
 remove={i for i,m in enumerate(body.data.materials) if 'brass' in m.name or 'Civic gold' in m.name}
 bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in remove],context='FACES');bm.to_mesh(body.data);bm.free()
 for mat in body.data.materials:
  mat.name='riftbound_'+kind+'_'+mat.name
  if not mat.use_nodes:continue
  p=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not p:continue
  name=mat.name.lower()
  if kind=='greenskin' and 'cloth' in name:
   for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
   p.inputs['Base Color'].default_value=(.095,.072,.045,1);p.inputs['Roughness'].default_value=.9
  if kind=='chaos' and any(s in name for s in ['steel','crimson','parchment']):
   for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
   p.inputs['Base Color'].default_value=(.09,.065,.12,1) if 'crimson' in name else (.055,.065,.075,1)
   p.inputs['Roughness'].default_value=.56
  if kind=='dark_elf':
   if 'hair' in name:
    for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
    p.inputs['Base Color'].default_value=(.61,.66,.70,1)
   elif p.inputs['Base Color'].is_linked and ('cauasian' in name or 'baked' in name):
    node=p.inputs['Base Color'].links[0].from_node
    if node.type=='TEX_IMAGE':
     im=node.image.copy();pixels=np.array(im.pixels[:]).reshape(-1,4)
     pixels[:,:3]*=np.array([.45,.59,.78] if 'cauasian' in name else [.52,.23,.57])
     im.pixels.foreach_set(pixels.astype(np.float32).ravel());im.filepath_raw=str(WORK/'textures'/f'population_{kind}_{len(bpy.data.images)}.png');im.file_format='PNG';im.save();im.pack();node.image=im
 def material(name,color,metal=0):
  m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.48;return m
 iron=material('riftbound_forged_black_iron',(.035,.043,.058),.8)
 trim=material('riftbound_worn_silver',(.28,.29,.34),.8)
 skin=material('riftbound_dusk_skin',(.23,.28,.4))
 if kind=='greenskin':
  cloth=material('riftbound_patched_work_tunic',(.09,.075,.055))
  body.data.materials.append(cloth);cloth_index=len(body.data.materials)-1
  for face in body.data.polygons:
   center=body.matrix_world@(sum((body.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices))
   if '.body' in body.data.materials[face.material_index].name and .85<center.z<1.42:face.material_index=cloth_index
 def part(name,verts,faces,mat,bone='head'):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(mat)
  uv=mesh.uv_layers.new();
  for face in mesh.polygons:
   for li in face.loop_indices:
    v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v.x*3,v.z*3)
  ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
  group=ob.vertex_groups.new(name=bone);group.add(list(range(len(verts))),1,'REPLACE')
  mod=ob.modifiers.new('body_rig','ARMATURE');mod.object=rig;return ob
 def horn(name,points,radius,bone='head',mat=None):
  verts=[]
  for i,p in enumerate(points):
   r=radius*(1-i/(len(points)-.1))
   q=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).to_track_quat('Z','Y')
   verts.extend(tuple(Vector(p)+q@Vector((r*math.cos(j*math.pi/4),r*math.sin(j*math.pi/4),0))) for j in range(8))
  return part(name,verts,[(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(len(points)-1) for j in range(8)],mat or iron,bone)
 if kind=='chaos':
  # Hollow fitted visor with separate cheek flanges and an open eye slit.
  for side in [-1,1]:
   part('split_war_mask',[(side*.015,-.19,1.68),(side*.14,-.14,1.69),(side*.16,-.10,1.79),(side*.02,-.2,1.78),(side*.015,-.20,1.80),(side*.16,-.12,1.81),(side*.12,-.10,1.90),(side*.02,-.20,1.91)],[(0,1,2,3),(4,5,6,7)],iron)
   horn('swept_helm_horn',[(side*.13,-.02,1.87),(side*.22,.02,1.98),(side*.27,.08,2.13),(side*.20,.06,2.23)],.075)
   horn('pauldron_spike',[(side*.32,0,1.46),(side*.44,.02,1.57),(side*.50,.05,1.71)],.075,'chest' if 'chest' in rig.data.bones else 'spine')
  horn('rift_crown',[(0,-.16,1.9),(0,-.14,2.03),(0,-.13,2.14)],.035)
 elif kind=='greenskin':
  ivory=material('worn_tusk_ivory',(.65,.58,.39))
  green=material('mire_ear_skin',(.22,.26,.10))
  for side in [-1,1]:
   horn('lower_jaw_tusk',[(side*.045,-.112,1.88),(side*.048,-.155,1.92),(side*.043,-.16,1.97)],.018,mat=ivory)
   part('mire_pointed_ear',[(side*.075,0,1.96),(side*.17,.01,2.03),(side*.105,.015,1.91),(side*.095,-.025,1.95)],[(0,1,3),(1,2,3),(2,0,3),(0,2,1)],green)
 elif kind=='dark_elf':
  for side in [-1,1]:
   part('sculpted_pointed_ear',[(side*.075,-.02,1.68),(side*.145,.012,1.75),(side*.105,.015,1.63),(side*.095,-.035,1.68)],[(0,1,3),(1,2,3),(2,0,3),(0,2,1)],skin)
   horn('dusk_circlet',[(side*.09,-.08,1.74),(side*.07,-.12,1.79),(0,-.13,1.78)],.012)
 body.name='Riftbound_'+kind;rig.name='Riftbound_'+kind+'_rig'
 bpy.data.libraries.write(str(WORK/'sources'/f'population_{kind}.blend'),{bpy.context.scene},fake_user=True,compress=True)
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for ob in meshes:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.data.calc_loop_triangles()
 base_mesh=body.data.copy();triangles=len(body.data.loop_triangles)
 lods=[]
 for lod,factor in enumerate([1,.55,.25]):
  body.data=base_mesh.copy();dec=body.modifiers.new('runtime_budget','DECIMATE');dec.ratio=min(1,28500/max(triangles,1))*factor
  bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=dec.name)
  bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True)
  file=WORK/'runtime'/f'chr_riftspire_{kind}{"_lod"+str(lod) if lod else ""}.glb'
  bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,export_animations=True,export_tangents=True)
  data=file.read_bytes();doc=json.loads(data[20:20+int.from_bytes(data[12:16],'little')]);tris=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
  lods.append({'level':lod,'model':file.name,'triangles':tris,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 (WORK/f'population_{kind}-report.json').write_text(json.dumps({'kind':kind,'source':source,'lods':lods},indent=2))
