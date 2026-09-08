"""Reimport and render literal exported animation poses; no source proxies."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build
ROOT=build.ROOT


def activate_clip(name,seconds):
    found=False
    for obj in bpy.context.scene.objects:
        data=obj.animation_data
        if not data:continue
        data.action=None
        for track in data.nla_tracks:
            track.mute=track.name!=name
            if not track.mute:found=True
    if not found:raise ValueError(f'Imported clip absent: {name}')
    # Blender's importer places glTF time zero on frame one.
    frame=1+seconds*bpy.context.scene.render.fps
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
    bpy.context.view_layer.update()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--asset',required=True);parser.add_argument('--lod',type=int,default=0)
    parser.add_argument('--clip');parser.add_argument('--times',default='0');parser.add_argument('--inspect',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    path=ROOT/'runtime'/f'{args.asset}_lod{args.lod}.glb'
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(path))
    tracks=[{'object':obj.name,'tracks':[{'name':track.name,'strips':[{'action':strip.action.name,'start':strip.frame_start,'end':strip.frame_end} for strip in track.strips]} for track in obj.animation_data.nla_tracks]} for obj in bpy.context.scene.objects if obj.animation_data]
    if args.inspect:print(json.dumps(tracks,indent=2));return
    if not args.clip:raise ValueError('--clip is required')
    # The importer creates hidden bone-control widgets; those are not GLB art.
    sources=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and not obj.hide_render and obj.visible_get()];snapshots=[];records=[]
    for index,seconds in enumerate(map(float,args.times.split(','))):
        activate_clip(args.clip,seconds);graph=bpy.context.evaluated_depsgraph_get();pose=[]
        for source in sources:
            mesh=bpy.data.meshes.new_from_object(source.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
            for vertex in mesh.vertices:vertex.co=source.matrix_world@vertex.co
            obj=bpy.data.objects.new(f'review.{index}.{source.name}',mesh);bpy.context.scene.collection.objects.link(obj);pose.append(obj)
        minimum=Vector(tuple(min(v.co[axis] for obj in pose for v in obj.data.vertices) for axis in range(3)))
        maximum=Vector(tuple(max(v.co[axis] for obj in pose for v in obj.data.vertices) for axis in range(3)))
        width=max(maximum.x-minimum.x,maximum.y-minimum.y)+1.5
        offset=Vector((index*width,0,0))
        for obj in pose:obj.location=offset
        snapshots.extend(pose);records.append({'seconds':seconds,'bounds_z_up':[list(minimum),list(maximum)]})
    for source in sources:source.hide_render=True;source.hide_set(True)
    bpy.context.view_layer.update()
    output=ROOT/'review'/f'{args.asset}_lod{args.lod}_{args.clip}_motion.png'
    build.set_view(snapshots,output)
    receipt={'asset':args.asset,'lod':args.lod,'clip':args.clip,'glb_sha256':build.sha(path),'poses':records,'image':str(output.relative_to(ROOT)),'image_sha256':build.sha(output),'decision':'pending_visual_review'}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
