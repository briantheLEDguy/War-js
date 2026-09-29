"""Bake opaque portal materials for interchange; retain editable sculpt sources.

Run with Blender --background --python. Writes a separate baked candidate folder.
This is preparation, not art, collision, animation or native approval.
"""
import bpy
import bmesh
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'artifacts/unreal/portal-models'
OUT=SOURCE/'baked'
OUT.mkdir(exist_ok=True)
records=[]


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj


for name in ('Aegis','Riftbound'):
    source=SOURCE/(name+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=8
    scene.render.bake.use_pass_direct=False
    scene.render.bake.use_pass_indirect=False
    scene.render.bake.use_pass_color=True
    scene.render.bake.margin=12
    opaque=[]
    for obj in scene.objects:
        if obj.type!='MESH':continue
        shader=obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
        if shader.inputs['Emission Strength'].default_value==0:opaque.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in opaque:obj.select_set(True)
    bpy.context.view_layer.objects.active=opaque[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    frame=bpy.context.object;frame.name=name+'_OpaqueStructure'
    geometry=bmesh.new();geometry.from_mesh(frame.data)
    # Bevels at needle tips create sub-0.5mm slivers whose UV derivatives collapse.
    # Weld below that physical tolerance before computing tangent-space atlases.
    bmesh.ops.remove_doubles(geometry,verts=list(geometry.verts),dist=.0005)
    bmesh.ops.dissolve_degenerate(geometry,edges=list(geometry.edges),dist=.00001)
    bmesh.ops.delete(geometry,geom=[face for face in geometry.faces if face.calc_area()<1e-10],context='FACES')
    geometry.to_mesh(frame.data);geometry.free();frame.data.update()
    triangles=frame.modifiers.new('Portable tangent triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangles.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    original_materials=list(frame.data.materials)
    images={}
    for channel in ('Color','Normal','Roughness','Metallic'):
        image=bpy.data.images.new(name+'_'+channel,width=2048,height=2048,alpha=False)
        if channel!='Color':image.colorspace_settings.name='Non-Color'
        overrides=[]
        for mat in original_materials:
            nodes=mat.node_tree.nodes;links=mat.node_tree.links
            target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target
            if channel in ('Color','Roughness','Metallic'):
                shader=nodes.get('Principled BSDF')
                output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
                old_link=output.inputs['Surface'].links[0]
                old_node,old_socket=old_link.from_node,old_link.from_socket
                emitter=nodes.new('ShaderNodeEmission')
                source_input=shader.inputs['Base Color' if channel=='Color' else channel]
                if source_input.is_linked:
                    links.new(source_input.links[0].from_socket,emitter.inputs['Color'])
                elif channel=='Color':
                    emitter.inputs['Color'].default_value=source_input.default_value
                else:
                    scalar=source_input.default_value
                    emitter.inputs['Color'].default_value=(scalar,scalar,scalar,1)
                links.new(emitter.outputs[0],output.inputs['Surface'])
                overrides.append((mat,emitter,old_socket,output))
        activate(frame)
        # A diffuse pass loses metallic albedo. Emission captures the actual PBR
        # input without lighting or the diffuse/specular energy split.
        bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
        for mat,emitter,old_socket,output in overrides:
            mat.node_tree.links.new(old_socket,output.inputs['Surface'])
            mat.node_tree.nodes.remove(emitter)
        image.filepath_raw=str(OUT/(name+'_'+channel+'.png'));image.file_format='PNG';image.save();image.pack()
        images[channel]=image
    baked=bpy.data.materials.new(name+'_BakedStructure');baked.use_nodes=True
    nodes=baked.node_tree.nodes;links=baked.node_tree.links;shader=nodes.get('Principled BSDF')
    for channel,image in images.items():
        texture=nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(texture.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],shader.inputs['Normal'])
        else:links.new(texture.outputs['Color'],shader.inputs['Base Color' if channel=='Color' else channel])
    for polygon in frame.data.polygons:polygon.material_index=0
    frame.data.materials.clear();frame.data.materials.append(baked)
    activate(frame)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'_Structure.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in scene.objects:
        if obj.type=='MESH' and obj!=frame:obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'_Effects.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in scene.objects:
        if obj.type=='MESH':obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,export_apply=True,export_tangents=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
    records.append(dict(name=name,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        glbSha256=hashlib.sha256((OUT/(name+'.glb')).read_bytes()).hexdigest(),
        fbx={part:hashlib.sha256((OUT/(name+'_'+part+'.fbx')).read_bytes()).hexdigest() for part in ('Structure','Effects')},
        textures={channel:hashlib.sha256((OUT/(name+'_'+channel+'.png')).read_bytes()).hexdigest() for channel in images},
        nativeApproved=False,artApproved=False,collisionApproved=False))
    (OUT/'materials.json').write_text(json.dumps(records,indent=2)+'\n')
    print('PORTAL_MATERIALS_BAKED='+name,flush=True)
