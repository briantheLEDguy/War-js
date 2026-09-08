"""Regional head derivative with retained authored topology, UVs and paint.

The Prelate face cage and Arcanist hair cages supply editable construction,
not a pre-approved character. The artisan changes facial proportions, nose,
neck, hair color and beard silhouette, and must pass its own export review.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[2]
PRELATE = ROOT / 'authoring/blender/battle-prelate-reference-rebuild'
ARCANIST = ROOT / 'authoring/blender/ember-arcanist-reference-rebuild'


def retained(path):
    target = WORK / 'foundations' / ('prelate-' if PRELATE in path.parents else 'arcanist-') / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    source = path.read_bytes()
    if target.exists() and target.read_bytes() != source:
        raise RuntimeError('Authored input changed: ' + str(path))
    if not target.exists(): target.write_bytes(source)
    return target


def painted(name, folder, tint=None):
    mat = bpy.data.materials.new('artisan_authored_' + name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value = .74
    palette = {'eye_white':(.49,.455,.387), 'iris':(.085,.06,.035), 'pupil':(.006,.005,.004),
               'brow':(.065,.038,.020), 'skin':(.28,.16,.095),'skin_ear':(.28,.16,.095)}
    shader.inputs['Base Color'].default_value = (*palette.get(name, (.12,.06,.028)),1)
    for channel,socket in [('basecolor','Base Color'),('roughness','Roughness')]:
        path=folder/f'{name}_{channel}.png'
        if not path.exists(): continue
        path=retained(path)
        img=bpy.data.images.load(str(path),check_existing=True)
        if tint and channel=='basecolor':
            # Retain the painted strand field while giving the artisan his own hair palette.
            img=img.copy(); img.name='artisan_chestnut_hair_albedo'
            values=np.array(img.pixels[:],dtype=np.float32).reshape(-1,4)
            values[:,:3]*=np.array(tint)[None,:]
            img.pixels.foreach_set(values.ravel())
        img.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        img.pack()
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img
        mat.node_tree.links.new(tex.outputs['Color'],shader.inputs[socket])
    # Runtime normals are image data, so the GLB retains the source relief.
    height_path=folder/f'{name}_height.png'
    if height_path.exists():
        source=bpy.data.images.load(str(retained(height_path)),check_existing=True)
        source.colorspace_settings.name='Non-Color'
        width,height=source.size
        values=np.array(source.pixels[:],dtype=np.float32).reshape(height,width,4)[:,:,0]
        gy,gx=np.gradient(values)
        normal=np.stack((-gx*16,-gy*16,np.ones_like(gx)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        rgba=np.ones((height,width,4),dtype=np.float32);rgba[:,:,:3]=normal*.5+.5
        image=bpy.data.images.new('artisan_'+name+'_normal',width=width,height=height,alpha=True)
        image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(rgba.ravel());image.pack()
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        node=mat.node_tree.nodes.new('ShaderNodeNormalMap');node.uv_map='UVMap'
        mat.node_tree.links.new(tex.outputs['Color'],node.inputs['Color'])
        mat.node_tree.links.new(node.outputs['Normal'],shader.inputs['Normal'])
    return mat


def build_head(make, morph, race):
    shape=lambda p:morph(p,race)
    materials={name:painted(name,PRELATE/'textures/source') for name in
               ['skin','skin_ear','eye_white','iris','pupil','brow']}
    materials['hair']=hair_material()
    records=[]

    def face_shape(p):
        x,y,z=p
        head=max(0,min(1,(z-1.56)/.10));head=head*head*(3-2*head)
        # Broad cheeks, a rounded working nose and a less pinched chin distinguish
        # this civilian from the stern Prelate source silhouette.
        cheek=math.exp(-((z-1.701)/.058)**2)
        nose=math.exp(-((x/.030)**2+((z-1.711)/.034)**2))*max(0,min(1,(-y-.09)/.04))
        x*=1.13+.08*cheek
        y=y*1.03-.025*head-.006*nose
        if z<1.62:z-=.045*max(0,min(1,(1.62-z)/.03))
        return shape((x,y,z))

    for path in [PRELATE/'source/head.json',ARCANIST/'source/hair.json']:
        raw=retained(path);document=json.loads(raw.read_text())
        records.append({'source':str(path.relative_to(ROOT)),'retained':str(raw.relative_to(WORK)),
                        'sha256':hashlib.sha256(raw.read_bytes()).hexdigest()})
        for part in document['parts']:
            if document['component']=='hair' and part['id']!='auburn_scalp':continue
            lookup={v['id']:i for i,v in enumerate(part['vertices'])}
            faces=[[lookup[v] for v in f['vertices']] for f in part['faces']]
            def part_shape(co):
                if document['component']!='hair':return face_shape(co)
                x,y,z=co
                x*=.86;y*=.87;z=1.78+(z-1.78)*.86-.003
                if part['id']=='temple_and_nape_lock' and z<1.78:z=1.78+(z-1.78)*.55
                return face_shape((x,y,z))
            vertices=[]
            for vertex in part['vertices']:
                co=list(vertex['co'])
                if part['id']=='head_skin':
                    if vertex['id'] in ['E1','E2','E3']:co[2]+=.0045
                    if vertex['id'] in ['E6','E7','E8']:co[2]-=.0012
                if part['id']=='eyebrows':co[2]+=.003
                vertices.append(part_shape(co))
            names=list(dict.fromkeys(f['material'] for f in part['faces']))
            obj=make('artisan_'+part['id'],vertices,faces,materials[names[0]],'head')
            obj['retained_source_sha256']=records[-1]['sha256']
            for name in names[1:]:obj.data.materials.append(materials[name])
            for face,source_face in zip(obj.data.polygons,part['faces']):
                face.material_index=names.index(source_face['material'])
                for loop,uv in zip(face.loop_indices,source_face['uv']):obj.data.uv_layers.active.data[loop].uv=uv
            edges={tuple(sorted(edge.vertices)):edge.index for edge in obj.data.edges}
            if part.get('creases'):
                values=obj.data.attributes.new('crease_edge','FLOAT','EDGE')
                for crease in part['creases']:
                    values.data[edges[tuple(sorted(lookup[v] for v in crease['edge']))]].value=crease['value']
            for spec in part.get('modifiers',[]):
                mod=obj.modifiers.new('Authored_'+spec['type'],spec['type'])
                if mod.type=='MIRROR':
                    mod.use_axis=(True,False,False);mod.use_clip=True;mod.merge_threshold=.000001
                elif mod.type=='SUBSURF':mod.levels=mod.render_levels=spec['levels']
                elif mod.type=='SOLIDIFY':mod.thickness=spec['thickness'];mod.offset=0
            # Evaluate mirrored skin before subdivision and rig deformation. Applying
            # in authoring order prevents a half-head from reaching the runtime join.
            bpy.context.view_layer.objects.active=obj
            for mod in list(obj.modifiers):
                if mod.type=='ARMATURE':continue
                if document['component']=='hair' and mod.type=='SOLIDIFY':continue
                while list(obj.modifiers).index(mod)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
                bpy.ops.object.modifier_apply(modifier=mod.name)
    (WORK/'review/artisan-head-derivation.json').write_text(json.dumps({'state':'draft','inputs':records},indent=2))
    bpy.context.view_layer.update()
    head=bpy.data.objects['artisan_head_skin']
    tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
    scalp=bpy.data.objects['artisan_auburn_scalp']
    for vertex in scalp.data.vertices:
        hit,normal,_,_=tree.find_nearest(vertex.co)
        vertex.co=hit+normal*.006
    scalp.data.update()
    build_swept_hair(make,face_shape,materials['hair'],tree)
    return materials['hair'],face_shape,tree


def build_swept_hair(make,shape,hair,tree):
    """Rounded locks grow from the fitted cap and curl across the forehead."""
    paths=[
        [( .070,.055,1.827),(.056,.024,1.857),(.025,-.018,1.865),(-.020,-.059,1.851),(-.057,-.094,1.821),(-.074,-.091,1.787)],
        [( .040,.074,1.848),(.018,.040,1.867),(-.016,.003,1.865),(-.048,-.045,1.847),(-.074,-.069,1.807),(-.077,-.060,1.774)],
        [( .083,.020,1.804),(.071,-.021,1.839),(.044,-.060,1.851),(.006,-.092,1.832),(-.034,-.110,1.806),(-.062,-.109,1.775)],
        [( .030,.093,1.826),(-.005,.062,1.854),(-.043,.027,1.851),(-.070,-.010,1.824),(-.080,-.024,1.784)],
    ]
    for index,path in enumerate(paths):
        centers=[];normals=[]
        for p in path:
            hit,normal,_,_=tree.find_nearest(shape(p));centers.append(hit);normals.append(normal)
        vertices=[];sides=10
        for r,(center,normal) in enumerate(zip(centers,normals)):
            t=r/(len(path)-1);envelope=math.sin(math.pi*t)**.6
            width=.003+(.019 if index!=1 else .023)*envelope
            depth=.001+.008*envelope
            tangent=(centers[min(r+1,len(path)-1)]-centers[max(0,r-1)]).normalized()
            lateral=tangent.cross(normal).normalized()
            for c in range(sides):
                a=c/sides*math.tau
                vertices.append(center+normal*(.003+depth*.7+depth*math.cos(a))+lateral*width*math.sin(a))
        faces=[(r*sides+c,r*sides+(c+1)%sides,(r+1)*sides+(c+1)%sides,(r+1)*sides+c)
               for r in range(len(path)-1) for c in range(sides)]
        faces.extend([tuple(reversed(range(sides))),tuple((len(path)-1)*sides+c for c in range(sides))])
        ob=make('artisan_volumetric_swept_lock_'+str(index),vertices,faces,hair,'head')
        for face in ob.data.polygons:
            for loop in face.loop_indices:
                v=ob.data.loops[loop].vertex_index;ob.data.uv_layers.active.data[loop].uv=((v%sides)/sides,(v//sides)/(len(path)-1))
        sub=ob.modifiers.new('Rounded_lock_flow','SUBSURF');sub.levels=sub.render_levels=2


def hair_material():
    """Directionally painted locks with fine strand normals, retained in the GLB."""
    size=1024;v,u=np.mgrid[0:size,0:size]/size
    drift=.006*np.sin(v*math.tau*1.5)+.003*np.sin(v*math.tau*4.5)
    phase=(u+drift)*math.tau
    broad=.12*np.sin(phase*19)+.08*np.sin(phase*31+.8)
    fine=.07*np.sin(phase*211+.8*np.sin(v*16))+.045*np.sin(phase*379+v*7)
    tone=.86+broad+fine+.06*np.sin(v*7+u*21)
    color=np.array([.105,.059,.028])[None,None,:]*tone[:,:,None]
    # A few desaturated strands break the pigment uniformly through each lock.
    grey=np.maximum(0,np.sin(phase*47)-.97)*3
    color+=grey[:,:,None]*np.array([.16,.13,.10])[None,None,:]
    relief=.30*np.sin(phase*211)+.15*np.sin(phase*379+v*7)+.2*np.sin(phase*31)
    gy,gx=np.gradient(relief);normal=np.stack((-gx*3,-gy*3,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    mat=bpy.data.materials.new('artisan_chestnut_directional_hair');mat.use_nodes=True
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.76
    for channel,values in [('basecolor',color),('normal',normal*.5+.5)]:
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=values
        image=bpy.data.images.new('artisan_hair_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(WORK/'textures'/f'artisan_hair_{channel}.png')
        image.file_format='PNG';image.save();image.pack()
        texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='normal':
            node=mat.node_tree.nodes.new('ShaderNodeNormalMap');node.uv_map='UVMap';node.inputs['Strength'].default_value=.35
            mat.node_tree.links.new(texture.outputs['Color'],node.inputs['Color'])
            mat.node_tree.links.new(node.outputs['Normal'],shader.inputs['Normal'])
        else:mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    return mat


def build_beard(make, face_shape, hair, tree):
    """A short full beard with authored cheek, chin and underside cross sections."""
    # Profile values are width, center-front depth, side depth, front height and
    # side rise. Closed rings curve around the mandible, avoiding a flat panel.
    profiles=[(.081,-.112,-.018,1.660,.060),(.084,-.126,-.008,1.636,.065),
              (.080,-.132,.003,1.602,.062),(.070,-.123,.012,1.570,.052),
              (.052,-.110,.014,1.548,.035),(.024,-.081,.016,1.546,.021)]
    verts=[];segments=48
    for r,(width,front,back,z,rise) in enumerate(profiles):
        for c in range(segments):
            angle=c/segments*math.tau
            x=width*math.sin(angle)
            facing=(1+math.cos(angle))*.5
            y=back+(front-back)*facing
            zz=z+rise*(abs(math.sin(angle))**1.2)+.022*(1-facing)
            if r>=4:zz+=.006*math.cos(angle*5)*(r-3)/2*facing
            # Sculpt shallow coherent locks into the volume; no stray wire hairs.
            ripple=.0025*math.cos(angle*9+r*.6)*math.sin(r/(len(profiles)-1)*math.pi)
            y-=ripple*facing
            point=face_shape((x,y,zz))
            if r<2:
                hit,normal,_,_=tree.find_nearest(point)
                point=point.lerp(hit+normal*.002,1 if r==0 else .55)
            verts.append(point)
    faces=[(r*segments+c,r*segments+(c+1)%segments,(r+1)*segments+(c+1)%segments,(r+1)*segments+c)
           for r in range(len(profiles)-1) for c in range(segments)]
    faces.append(tuple((len(profiles)-1)*segments+c for c in reversed(range(segments))))
    obj=make('artisan_rounded_jaw_beard',verts,faces,hair,'head')
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            index=obj.data.loops[loop].vertex_index;r=index//segments;c=index%segments
            obj.data.uv_layers.active.data[loop].uv=(c/segments,r/(len(profiles)-1))
    sub=obj.modifiers.new('Jaw_groom_surface','SUBSURF');sub.levels=sub.render_levels=2
    # Mustache lobes have real curved volume and meet the jaw under the mouth.
    for side in [-1,1]:
        path=[(.005,-.151,1.682,.007,.005),(.020,-.153,1.681,.009,.007),
              (.040,-.145,1.675,.010,.007),(.058,-.126,1.663,.009,.006),(.070,-.103,1.650,.003,.003)]
        vertices=[];cross=10
        for x,y,z,ry,rz in path:
            center=face_shape((side*x,y,z))
            hit=tree.ray_cast(Vector((center.x,-2,center.z)),Vector((0,1,0)))[0]
            if hit is not None:center.y=hit.y-.002
            for c in range(cross):
                a=c/cross*math.tau;vertices.append(center+Vector((0,ry*math.cos(a),rz*math.sin(a))))
        faces=[(r*cross+c,r*cross+(c+1)%cross,(r+1)*cross+(c+1)%cross,(r+1)*cross+c)
               for r in range(len(path)-1) for c in range(cross)]
        faces.extend([tuple(reversed(range(cross))),tuple((len(path)-1)*cross+c for c in range(cross))])
        ob=make('artisan_curved_mustache_'+str(side),vertices,faces,hair,'head')
        for face in ob.data.polygons:
            for loop in face.loop_indices:
                index=ob.data.loops[loop].vertex_index
                ob.data.uv_layers.active.data[loop].uv=((index%cross)/cross,(index//cross)/(len(path)-1))
        sub=ob.modifiers.new('Mustache_flow','SUBSURF');sub.levels=sub.render_levels=2
