"""Import explicit cages, retain masters, bake PBR atlases, export actual GLBs.

The Battle Prelate atlas utility is reused as a renderer; no character or city
geometry is imported. Export reports contain measurements, never approval claims.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE_PATH=ROOT/'source'/'frontier_collection.json'
SOURCE=json.loads(SOURCE_PATH.read_text())
BAKER_PATH=ROOT.parent/'battle-prelate-reference-rebuild'/'tools'/'bake_atlas.py'
spec=importlib.util.spec_from_file_location('frontier_atlas_baker',BAKER_PATH)
baker=importlib.util.module_from_spec(spec); spec.loader.exec_module(baker)
spec=importlib.util.spec_from_file_location('frontier_mechanical_animation',ROOT/'tools'/'mechanical_animation.py')
mechanics=importlib.util.module_from_spec(spec); spec.loader.exec_module(mechanics)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_material(name,record):
    material=bpy.data.materials.new(f'frontier.source.{name}'); material.use_nodes=True
    tree=material.node_tree; shader=tree.nodes.get('Principled BSDF')
    material.diffuse_color=(*[v/255 for v in record['basecolor']],1)
    uv=tree.nodes.new('ShaderNodeUVMap'); uv.uv_map='authored_uv'
    for channel,input_name in (('basecolor','Base Color'),('roughness','Roughness'),('metallic','Metallic')):
        texture=tree.nodes.new('ShaderNodeTexImage')
        texture.image=bpy.data.images.load(str(ROOT/'textures'/'source'/f'{name}_{channel}.png'),check_existing=True)
        texture.image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        tree.links.new(uv.outputs['UV'],texture.inputs['Vector']); tree.links.new(texture.outputs['Color'],shader.inputs[input_name])
    height=tree.nodes.new('ShaderNodeTexImage'); height.image=bpy.data.images.load(str(ROOT/'textures'/'source'/f'{name}_height.png'),check_existing=True)
    height.image.colorspace_settings.name='Non-Color'; tree.links.new(uv.outputs['UV'],height.inputs['Vector'])
    bump=tree.nodes.new('ShaderNodeBump'); bump.inputs['Distance'].default_value=.004 if record['paint']=='wood' else .0014
    bump.inputs['Strength'].default_value=.45; tree.links.new(height.outputs['Color'],bump.inputs['Height']); tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    return material


def apply_modifiers(obj,record,lod):
    for entry in record['finish']:
        mod=obj.modifiers.new(f"authored_{entry['type'].lower()}",entry['type'])
        if entry['type']=='BEVEL':
            mod.width=entry['width']; mod.segments=max(1,entry['segments']-lod)
            mod.limit_method='ANGLE'; mod.angle_limit=.45
        elif entry['type']=='SUBSURF':
            mod.levels=max(1,entry['levels']-lod); mod.render_levels=mod.levels
        elif entry['type']=='SOLIDIFY': mod.thickness=entry['thickness']; mod.offset=0
    if not any(entry['type']=='SUBSURF' for entry in record['finish']):
        mod=obj.modifiers.new('construction_corner_normals','WEIGHTED_NORMAL'); mod.keep_sharp=True; mod.weight=50


def setup_asset(asset_id,lod=0):
    collection=bpy.data.collections.new(f'{asset_id}.source_lod{lod}'); bpy.context.scene.collection.children.link(collection)
    materials={name:make_material(name,record) for name,record in SOURCE['materials'].items()}
    groups={}; objects=[]
    for number,instance in enumerate(SOURCE['assets'][asset_id]['instances']):
        if 'group' in instance:
            obj=bpy.data.objects.new(f"source.{instance['group']}",None); collection.objects.link(obj); groups[instance['group']]=obj
        else:
            part=SOURCE['parts'][instance['part']]
            mesh=bpy.data.meshes.new(f"{part['id']}.authored_cage.{number}"); mesh.from_pydata(part['vertices'],[],part['faces']); mesh.update()
            uv=mesh.uv_layers.new(name='authored_uv')
            window=instance.get('uv_window',{'scale':[1,1],'offset':[0,0]})
            for polygon,coords in zip(mesh.polygons,part['corner_uv']):
                for loop_index,corner in zip(polygon.loop_indices,coords):
                    uv.data[loop_index].uv=[corner[axis]*window['scale'][axis]+window['offset'][axis] for axis in range(2)]
            bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
            mesh.materials.append(materials[instance.get('material_override',part['material'])])
            for polygon in mesh.polygons: polygon.use_smooth=True
            obj=bpy.data.objects.new('source.'+instance.get('name',f"{part['id']}.{number:03}"),mesh); collection.objects.link(obj)
            obj['authored_part']=part['id']; obj['source_policy']=part['source_kind']; obj['construction_note']=part['description']
            if instance.get('rigid_group'): obj['rigid_group']=instance['rigid_group']
            elif instance.get('parent'): obj['rigid_group']=instance['parent']
            elif asset_id=='frontier_battering_ram' and (part['id'] in ('ram_trunk','ram_forged_head','forged_horn') or part['id']=='forged_rosette' and instance['location'][1]<-2):
                obj['rigid_group']='ram_striker'
            elif asset_id=='frontier_field_catapult' and part['id'] in ('catapult_throwing_arm','catapult_spoon'):
                obj['rigid_group']='throwing_assembly'
            elif asset_id=='frontier_oil_cauldron' and part['id'] in ('oil_cauldron','forged_rosette'): obj['rigid_group']='tipping_cauldron'
            else: obj['rigid_group']='body'
            apply_modifiers(obj,part,lod)
            if instance.get('parent'): obj.parent=groups[instance['parent']]
            objects.append(obj)
        obj.location=instance['location']; obj.rotation_euler=[math.radians(v) for v in instance['rotation_degrees']]; obj.scale=instance['scale']
    bpy.context.view_layer.update()
    # Weld only the finished iron arc repetitions before beveling. This keeps a
    # continuous rolled tire, avoiding shading seams at its finite patch joins.
    for group in groups.values():
        tires=[obj for obj in objects if obj.parent==group and obj.get('authored_part')=='wheel_iron_tire']
        if not tires: continue
        bpy.ops.object.select_all(action='DESELECT')
        for obj in tires: obj.modifiers.clear(); obj.select_set(True)
        bpy.context.view_layer.objects.active=tires[0]; bpy.ops.object.join(); tire=tires[0]
        bm=bmesh.new(); bm.from_mesh(tire.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0015)
        # Remove the coincident internal arc-end faces after welding.
        bm.verts.index_update()
        seen={}; duplicate=[]
        for face in bm.faces:
            key=tuple(sorted(vertex.index for vertex in face.verts))
            if key in seen:
                duplicate.append(face)
                if seen[key] not in duplicate: duplicate.append(seen[key])
            else: seen[key]=face
        if duplicate: bmesh.ops.delete(bm,geom=duplicate,context='FACES')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(tire.data); bm.free()
        apply_modifiers(tire,SOURCE['parts']['wheel_iron_tire'],lod)
        objects=[obj for obj in objects if obj==tire or obj not in tires]
    cover=next((obj for obj in objects if obj.get('authored_part') in ('cloth_canopy','ram_hide_roof')),None)
    fitting_surface=None
    if cover:
        fitting_surface=cover.copy();fitting_surface.data=cover.data.copy();collection.objects.link(fitting_surface)
        fitting_surface.name='construction.cover_fitting_surface'
        for modifier in list(fitting_surface.modifiers):
            if modifier.type!='SUBSURF':fitting_surface.modifiers.remove(modifier)
            else:modifier.levels=modifier.render_levels=2
        fitting_surface.hide_render=True;fitting_surface.hide_set(True)
    for obj in objects:
        kind=obj.get('authored_part','')
        fitted=kind in ('cloth_canopy','canopy_seam','ram_hide_roof','canvas_repair_patch') or kind.startswith(('canvas_panel_seam_','hide_overlap_'))
        if fitted:
            for modifier in obj.modifiers:
                if modifier.type=='SUBSURF': modifier.levels=modifier.render_levels=2
        if cover and obj!=cover and (kind=='canvas_repair_patch' or kind.startswith(('canvas_panel_seam_','hide_overlap_'))):
            wrap=obj.modifiers.new('fit_seam_to_finished_cover','SHRINKWRAP')
            cover_depth=sum(modifier.thickness for modifier in cover.modifiers if modifier.type=='SOLIDIFY')
            wrap.target=fitting_surface;wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.wrap_mode='ABOVE_SURFACE';wrap.offset=cover_depth/2+.012
            first_solidify=next((i for i,modifier in enumerate(obj.modifiers) if modifier.type=='SOLIDIFY'),len(obj.modifiers)-1)
            obj.modifiers.move(len(obj.modifiers)-1,first_solidify)
        if lod:
            reduction=obj.modifiers.new('construction_aware_distance_reduction','DECIMATE')
            reduction.ratio=(.78 if lod==1 else .42) if kind.startswith('wheel_') else (1 if lod==1 else .82) if fitted else (.86 if lod==1 else .53)
    bpy.context.view_layer.update()
    return collection,objects


def evaluated_join(objects,name):
    bpy.ops.object.select_all(action='DESELECT'); evaluated=[]; graph=bpy.context.evaluated_depsgraph_get()
    for source in objects:
        mesh=bpy.data.meshes.new_from_object(source.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        obj=bpy.data.objects.new(source.name+'.evaluated',mesh); bpy.context.scene.collection.objects.link(obj); obj.matrix_world=source.matrix_world
        group=obj.vertex_groups.new(name=f"rigid.{source.get('rigid_group','body')}"); group.add(list(range(len(mesh.vertices))),1,'REPLACE')
        obj.select_set(True); evaluated.append(obj)
    bpy.context.view_layer.objects.active=evaluated[0]; bpy.ops.object.join(); joined=bpy.context.object; joined.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return joined


def split_rigid_nodes(obj,asset_id):
    """Keep shared baked atlas UVs while restoring useful mechanical pivots."""
    pivots={'body':(0,0,0),'ram_striker':(0,0,1.63),'throwing_assembly':(0,0,.88),'tipping_cauldron':(0,0,.82)}
    pivots.update(SOURCE['assets'][asset_id].get('mechanical_pivots',{}))
    for instance in SOURCE['assets'][asset_id]['instances']:
        if 'group' in instance: pivots[instance['group']]=tuple(instance['location'])
    pieces=[]; contract=[]
    for group in obj.vertex_groups:
        if not group.name.startswith('rigid.'): continue
        component=group.name[6:]
        keep={vertex.index for vertex in obj.data.vertices if any(item.group==group.index and item.weight>.5 for item in vertex.groups)}
        if not keep: continue
        piece=obj.copy(); piece.data=obj.data.copy(); bpy.context.scene.collection.objects.link(piece); piece.name=component
        if piece.name!=component: raise ValueError(f'Mechanical node name collision: {component}')
        bm=bmesh.new(); bm.from_mesh(piece.data); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[vertex for vertex in bm.verts if vertex.index not in keep],context='VERTS')
        bm.to_mesh(piece.data); bm.free()
        pivot=Vector(pivots.get(component,(0,0,0)))
        piece.data.transform(Matrix.Translation(-pivot));piece.matrix_world=Matrix.Identity(4)
        if component!='body' and component!='realm_standard':
            anchor=bpy.data.objects.new('pivot.'+component,None);bpy.context.scene.collection.objects.link(anchor)
            anchor.location=pivot;piece.parent=anchor
            if component=='haul_rope':
                anchor.rotation_euler.x=math.atan2(.95,.92)
                piece.data.transform(Matrix.Diagonal((1,1,math.hypot(.95,.92),1)))
        piece['mechanical_component']=component
        pieces.append(piece)
        contract.append({'node':component,'pivot_node':piece.parent.name if piece.parent else None,'pivot_z_up':list(pivot),'motion':'rotate_x' if component.startswith(('wheel_','suspension_')) or component in ('throwing_assembly','tipping_cauldron','winding_drum') else 'rotate_z' if component.startswith('gate_leaf_') else 'translate_y' if component=='ram_striker' else 'stretch_rotate_x' if component=='haul_rope' else 'static'})
    bpy.context.view_layer.update()
    return pieces,contract


def set_view(objects,output):
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=32
    scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    if not scene.world: scene.world=bpy.data.worlds.new('frontier_review_world')
    scene.world.color=(.20,.20,.20)
    coordinates=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
    lower=Vector(tuple(min(p[i] for p in coordinates) for i in range(3))); upper=Vector(tuple(max(p[i] for p in coordinates) for i in range(3)))
    centre=(lower+upper)/2; extent=max(upper-lower)
    camera_data=bpy.data.cameras.new('review_camera'); camera=bpy.data.objects.new('review_camera',camera_data); scene.collection.objects.link(camera)
    camera.location=centre+Vector((extent*1.15,-extent*1.55,extent*.92)); camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO'; scene.camera=camera
    camera_inverse=camera.rotation_euler.to_matrix().transposed()
    projected=[camera_inverse@(p-centre) for p in coordinates]
    width=max(p.x for p in projected)-min(p.x for p in projected)
    height=max(p.y for p in projected)-min(p.y for p in projected)
    camera_data.ortho_scale=max(width,height*scene.render.resolution_x/scene.render.resolution_y)*1.16
    for name,offset,power,size,color in [('key',(-4,-5,7),1800,5,(1,.87,.70)),('fill',(5,-2,4),1200,4,(.72,.84,1)),('rim',(0,5,6),2100,3,(1,.93,.80))]:
        light_data=bpy.data.lights.new(name,'AREA'); light_data.energy=power*(extent/5)**2; light_data.shape='DISK'; light_data.size=size*(extent/5); light_data.color=color
        light=bpy.data.objects.new(name,light_data); scene.collection.objects.link(light); light.location=centre+Vector(offset)*(extent/5); light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'; scene.render.filepath=str(output)
    bpy.ops.render.render(write_still=True)
    return {'minimum':list(lower),'maximum':list(upper),'dimensions':list(upper-lower)}


def build(asset_id,args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection,source_objects=setup_asset(asset_id,0)
    master=ROOT/'masters'/f'{asset_id}.blend'; master.parent.mkdir(exist_ok=True)
    source_bounds=set_view(source_objects,ROOT/'review'/f'{asset_id}_source.png') if args.source_render else None
    for image in bpy.data.images:
        if image.source=='FILE': image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    high=evaluated_join(source_objects,f'{asset_id}.high_source')
    for obj in source_objects: obj.hide_render=True; obj.hide_set(True)
    high.hide_render=True; high.hide_set(True)
    record={'asset_id':asset_id,'source_sha256':sha(SOURCE_PATH),'builder_sha256':sha(Path(__file__)),'mechanics_sha256':sha(ROOT/'tools/mechanical_animation.py'),'baker_sha256':sha(BAKER_PATH),
            'paint_record_sha256':sha(ROOT/'textures'/'paint_records.json'),
            'source_texture_sha256':{str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in sorted((ROOT/'textures'/'source').glob('*.png'))},
            'master':str(master.relative_to(ROOT)),'master_sha256':sha(master),
            'source_bounds':source_bounds,'authoring_policy':'literal_authored_control_cage','approval':'pending_visual_review','limitations':SOURCE['assets'][asset_id]['limitations'],'lods':[]}
    for lod in args.lods:
        if lod==0:
            low=high.copy(); low.data=high.data.copy(); bpy.context.scene.collection.objects.link(low); low.hide_set(False)
        else:
            lod_collection,parts=setup_asset(asset_id,lod)
            low=evaluated_join(parts,f'{asset_id}.lod{lod}')
            for obj in parts: bpy.data.objects.remove(obj,do_unlink=True)
            bpy.data.collections.remove(lod_collection)
        low.name=f'{asset_id}_lod{lod}'; low.hide_render=False; low.hide_set(False)
        bpy.context.view_layer.objects.active=low
        pieces,contract=split_rigid_nodes(low,asset_id)
        low.hide_render=True; low.hide_set(True)
        texture_paths={}; wheel_mesh=None
        for piece in pieces:
            component=piece.name
            if component.startswith('wheel_') and wheel_mesh is not None:
                piece.data=wheel_mesh
                continue
            resolution=1024 if asset_id=='frontier_oil_cauldron' else 2048
            if lod==2: resolution//=2
            if component=='ram_striker': resolution=1024
            if component=='realm_standard': resolution=512 if lod<2 else 256
            # Retain evaluated curvature and authored bump without casting rays
            # through neighboring construction shells into unrelated surfaces.
            texture_paths[component]=baker.bake_module_atlas(piece,f'{asset_id}_lod{lod}_{component}',ROOT/'textures'/'baked',resolution=resolution)
            piece.data.materials[0].name=f'frontier.atlas.{asset_id}.lod{lod}.{component}'
            triangulate=piece.modifiers.new('stable_runtime_triangles','TRIANGULATE')
            bpy.context.view_layer.objects.active=piece; bpy.ops.object.modifier_apply(modifier=triangulate.name)
            if component.startswith('wheel_'): wheel_mesh=piece.data
        bpy.ops.object.select_all(action='DESELECT')
        for piece in pieces:
            piece.select_set(True)
            if piece.parent:piece.parent.select_set(True)
        sockets=[]
        for name,position in SOURCE['assets'][asset_id].get('sockets',{}).items():
            socket=bpy.data.objects.new('socket.'+name,None);bpy.context.scene.collection.objects.link(socket)
            socket.location=position
            parent_name=SOURCE['assets'][asset_id].get('socket_parents',{}).get(name)
            if parent_name:
                parent=next(piece for piece in pieces if piece.name==parent_name)
                socket.parent=parent;socket.location=parent.matrix_world.inverted()@Vector(position)
            socket.select_set(True);sockets.append(socket)
        low.hide_render=True; low.hide_set(True)
        runtime=ROOT/'runtime'/f'{asset_id}_lod{lod}.glb'
        clips=mechanics.author_mechanical_actions(pieces,asset_id)
        bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,export_frame_range=False,export_tangents=True,export_texcoords=True,export_normals=True)
        if lod==0:
            animated_master=ROOT/'masters'/f'{asset_id}_animated.blend'
            bpy.ops.wm.save_as_mainfile(filepath=str(animated_master))
            record['animated_master']=str(animated_master.relative_to(ROOT));record['animated_master_sha256']=sha(animated_master)
        bounds={'minimum':[min((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)],'maximum':[max((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)]}
        triangle_count=sum(len(piece.data.polygons) for piece in pieces)
        record['lods'].append({'level':lod,'path':str(runtime.relative_to(ROOT)),'sha256':sha(runtime),'bytes':runtime.stat().st_size,'triangles':triangle_count,'vertices':sum(len(piece.data.vertices) for piece in pieces),'materials':len({material.name for piece in pieces for material in piece.data.materials}),'bounds_z_up':bounds,'textures':texture_paths,'rigid_nodes':contract,'clips':clips})
        for piece in pieces:
            piece.hide_render=True; piece.hide_set(True); piece.name=f'staged_lod{lod}.{piece.name}'
            if piece.parent:piece.parent.name=f'staged_lod{lod}.{piece.parent.name}'
        for socket in sockets:bpy.data.objects.remove(socket,do_unlink=True)
        low.hide_render=True; low.hide_set(True)
        (ROOT/'review'/f'{asset_id}_build.json').write_text(json.dumps(record,indent=2)+'\n')
        print(f'FRONTIER_EXPORTED {asset_id} LOD{lod} triangles={triangle_count} bytes={runtime.stat().st_size}',flush=True)
    return record


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--assets',default=','.join(SOURCE['assets'])); parser.add_argument('--lods',default='0,1,2'); parser.add_argument('--source-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []); args.lods=[int(v) for v in args.lods.split(',')]
    for directory in ('runtime','review','textures'): (ROOT/directory).mkdir(exist_ok=True)
    records=[build(asset,args) for asset in args.assets.split(',')]
    (ROOT/'review'/'latest_build.json').write_text(json.dumps({'source_sha256':sha(SOURCE_PATH),'assets':records,'visual_approval':False},indent=2)+'\n')


if __name__=='__main__': main()
