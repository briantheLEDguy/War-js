"""Actual exported GLB review, positional topology and measured distance views."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def render(objects,path,distance=None,detail=False):
    scene=bpy.context.scene
    for item in list(scene.objects):
        if item.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(item,do_unlink=True)
    points=[obj.matrix_world@v.co for obj in objects for v in obj.data.vertices]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);centre=(lo+hi)/2;extent=max(hi-lo)
    scene.render.engine='CYCLES';scene.cycles.samples=20 if not distance else 12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1280 if distance else 1400;scene.render.resolution_y=720 if distance else 1050;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('neutral_export_review');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.25,.25,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    data=bpy.data.cameras.new('measured_review_camera');camera=bpy.data.objects.new('measured_review_camera',data);scene.collection.objects.link(camera);scene.camera=camera
    if detail:
        if extent>7:centre=Vector((-.2,-.4,4.3));frame=2.7
        elif hi.z>3:centre=Vector((.18,-.5,2.45));frame=1.5
        elif hi.z>1.8:centre=Vector((-1,-.9,1.35));frame=2.2
        else:centre=Vector((.3,-.35,.42));frame=1.35
    if distance:
        camera.location=Vector((centre.x+extent*.2,centre.y-distance,1.8+min(2.2,extent*.1)));target=Vector((centre.x,centre.y,centre.z));data.type='PERSP';data.lens=38;data.clip_end=1000
    else:
        camera.location=centre+Vector((extent*.8,-extent*1.6,extent*.38));target=centre;data.type='ORTHO'
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    if not distance:
        inverse=camera.rotation_euler.to_matrix().transposed();projected=[inverse@(p-centre) for p in points];width=max(p.x for p in projected)-min(p.x for p in projected);height=max(p.y for p in projected)-min(p.y for p in projected)
        data.ortho_scale=frame if detail else max(width,height*1400/1050)*1.14
    for name,delta,power in [('key',(-4,-6,8),1200),('fill',(6,-3,5),900),('rim',(0,6,8),1100)]:
        light_data=bpy.data.lights.new(name,'AREA');light_data.energy=power*(extent/7)**2;light_data.shape='DISK';light_data.size=5*extent/7
        light=bpy.data.objects.new(name,light_data);scene.collection.objects.link(light);light.location=(lo+hi)/2+Vector(delta)*extent/7;light.rotation_euler=((lo+hi)/2-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return {'distance_m':distance,'projection':data.type,'lens_mm':38 if distance else None,'camera_position_z_up':list(camera.location),'target_z_up':list(target),'resolution':[scene.render.resolution_x,scene.render.resolution_y],'lighting':'neutral white lights; original exported PBR; no image retouching'}

def audit(objects):
    rows=[];allpoints=[]
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
        boundary=sum(e.is_boundary for e in bm.edges);multi=sum(len(e.link_faces)>2 for e in bm.edges);loose=sum(len(e.link_faces)==0 for e in bm.edges)
        rows.append({'mesh':obj.name,'boundary_edges_after_positional_weld':boundary,'multi_face_edges_after_positional_weld':multi,'loose_edges':loose,'faces':len(bm.faces)})
        bm.free();allpoints.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    return {'meshes':rows,'bounds_z_up':{'minimum':[min(p[i] for p in allpoints) for i in range(3)],'maximum':[max(p[i] for p in allpoints) for i in range(3)]},'totalBoundaryEdges':sum(r['boundary_edges_after_positional_weld'] for r in rows),'totalMultiFaceEdges':sum(r['multi_face_edges_after_positional_weld'] for r in rows),'totalLooseEdges':sum(r['loose_edges'] for r in rows)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets');parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for build in sorted((ROOT/'review').glob('*_build.json')):
        record=json.loads(build.read_text());key=record['asset_id']
        if args.assets and key not in args.assets.split(','):continue
        for lod in record['lods']:
            if str(lod['level']) not in args.lods.split(','):continue
            path=ROOT/'runtime'/lod['model'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
            evidence={'model':path.name,'sha256':sha(path),'reviewer_sha256':sha(Path(__file__)),'audit':audit(objects),'views':{}}
            modes=['neutral','gameplay']+(['detail'] if lod['level']==0 else [])
            for mode in modes:
                image=path.stem+'_'+mode+'.png';distance=([18,45,100] if 'alder' in key else [8,22,50])[lod['level']] if mode=='gameplay' else None
                camera=render(objects,ROOT/'review'/image,distance,mode=='detail');evidence['views'][mode]={'image':image,'sha256':sha(ROOT/'review'/image),'camera':camera}
            (ROOT/'review'/f'{path.stem}_reimport.json').write_text(json.dumps(evidence,indent=2)+'\n');print('NATURE_REIMPORTED',path.name,evidence['audit']['totalBoundaryEdges'],evidence['audit']['totalMultiFaceEdges'],flush=True)
