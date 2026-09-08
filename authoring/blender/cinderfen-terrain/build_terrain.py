"""Author Cinderfen's sixteen landscape sectors from the shared survey grid.

No Blender primitive operators: explicit surface topology, shared-border normals,
world-scaled UVs and separately authored road ribbons. Run with Blender --background.
"""
import bpy, json, math, hashlib, struct, argparse, sys
import numpy as np
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK))
from road_junctions import connected_junctions, transition_polygons
SOURCE = json.loads((WORK / 'terrain-source.json').read_text())
JUNCTIONS = connected_junctions(SOURCE['paths'])
N, SIZE, H = SOURCE['segments'], SOURCE['size'], SOURCE['heights']
STEP = SIZE / N
for folder in ['runtime', 'masters', 'review', 'textures/cinderfen_terrain']:
    (WORK / folder).mkdir(parents=True, exist_ok=True)

def height(x, z):
    u, v = max(0, min(N, (x+SIZE/2)/STEP)), max(0, min(N, (z+SIZE/2)/STEP))
    ix, iz = min(N-1, int(u)), min(N-1, int(v))
    a, b = u-ix, v-iz
    at = lambda i, j: H[j*(N+1)+i]
    return (at(ix,iz)*(1-a)+at(ix+1,iz)*a)*(1-b)+(at(ix,iz+1)*(1-a)+at(ix+1,iz+1)*a)*b

def normal(x,z):
    e = .5
    return Vector((-(height(x+e,z)-height(x-e,z))/(2*e), (height(x,z+e)-height(x,z-e))/(2*e), 1)).normalized()

def material(name, image, road=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    p = n.get('Principled BSDF'); p.inputs['Roughness'].default_value = .96
    tex = n.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(str(WORK/'textures/source'/image), check_existing=True)
    tex.image.scale(1024,1024)
    col = n.new('ShaderNodeVertexColor'); col.layer_name = 'SurveyColor'
    mul = n.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    l.new(tex.outputs['Color'], mul.inputs[1]); l.new(col.outputs['Color'], mul.inputs[2]); l.new(mul.outputs[0], p.inputs['Base Color'])
    # Bind the same SurveyColor set for RGB and alpha, so glTF exports authored
    # verge opacity in COLOR_0 instead of an unused second color attribute.
    # Analytical sub-millimetre surface relief, independent from the diffuse source.
    # This is a material-detail normal, not a claimed high-poly transfer bake.
    side=512; z,x=np.mgrid[0:side,0:side]/side*2*math.pi
    relief=(np.sin(x*83+np.sin(z*13))*np.sin(z*71+x*3)+.45*np.sin(x*127-z*97))
    if not road: relief += .8*np.sin(x*41+z*29+np.sin(z*17))
    gy,gx=np.gradient(relief);strength=.18 if road else .28
    normals=np.stack((-gx*strength,-gy*strength,np.ones_like(x)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    pixels=np.concatenate((normals*.5+.5,np.ones((side,side,1))),axis=-1).astype(np.float32)
    detail=bpy.data.images.new(name+'_microrelief',width=side,height=side,alpha=False)
    detail.colorspace_settings.name='Non-Color';detail.pixels.foreach_set(pixels.ravel())
    detail.filepath_raw=str(WORK/'textures/source'/(name+'_normal.png'));detail.file_format='PNG';detail.save()
    normaltex=n.new('ShaderNodeTexImage');normaltex.image=detail
    normalnode=n.new('ShaderNodeNormalMap');l.new(normaltex.outputs['Color'],normalnode.inputs['Color']);l.new(normalnode.outputs['Normal'],p.inputs['Normal'])
    if road:
        m.surface_render_method = 'DITHERED'
        l.new(col.outputs['Alpha'],p.inputs['Alpha'])
    return m

def mesh_object(name, verts, faces, colors, mat, cx, cz):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata([(x-cx,-(z-cz),y) for x,z,y in verts], [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='Metres_2m')
    color = mesh.color_attributes.new(name='SurveyColor', type='FLOAT_COLOR', domain='CORNER')
    # Creating a CustomData layer invalidates earlier RNA layer pointers in Blender 5.
    uv = mesh.uv_layers['Metres_2m']
    for loop in mesh.loops:
        x,z,_ = verts[loop.vertex_index]
        uv.data[loop.index].uv = (x/2, -z/2)
        color.data[loop.index].color = colors[loop.vertex_index]
    for poly in mesh.polygons: poly.use_smooth = True
    mesh.normals_split_custom_set_from_vertices([normal(x,z) for x,z,_ in verts])
    obj['source_sha256'] = SOURCE['sourceSha256']; obj['construction'] = 'authored survey surface; no primitive operators'
    return obj

def land(chunk, lod, mat):
    cx,cz = chunk['x'],chunk['z']; left,top = cx-150,cz-150
    # LOD0: 1.5625m samples. LOD1: 6.25m. LOD2: 12.5m with full LOD0 boundaries.
    stride = [1,4,8][lod]; cells = 192
    verts, faces, colors, lookup = [],[],[],{}
    def vertex(ix,iz):
        key=(ix,iz)
        if key in lookup: return lookup[key]
        x,z=left+ix*STEP/4,top+iz*STEP/4
        i=len(verts);lookup[key]=i;verts.append((x,z,height(x,z)))
        tint=.87+.07*math.sin(x*.016+z*.009)+.035*math.cos(z*.042-x*.011)
        colors.append((tint,tint, tint*.96,1));return i
    for iz in range(0,cells,stride):
        for ix in range(0,cells,stride):
            if stride == 1:
                a,b,c,d=vertex(ix,iz),vertex(ix,iz+1),vertex(ix+1,iz+1),vertex(ix+1,iz)
                faces.extend([(a,b,c),(a,c,d)])
            else:
                # Retain all perimeter survey samples, including along coarser LOD edges.
                ring=[]
                for dx in range(stride if iz==0 else 1): ring.append(vertex(ix+dx,iz))
                for dz in range(stride if ix+stride==cells else 1): ring.append(vertex(ix+stride,iz+dz))
                for dx in range(stride if iz+stride==cells else 1): ring.append(vertex(ix+stride-dx,iz+stride))
                for dz in range(stride if ix==0 else 1): ring.append(vertex(ix,iz+stride-dz))
                center=vertex(ix+stride/2,iz+stride/2)
                for j in range(len(ring)): faces.append((center,ring[(j+1)%len(ring)],ring[j]))
    return mesh_object(chunk['assetKey']+f'_surface_LOD{lod}',verts,faces,colors,mat,cx,cz)

def clip(poly, axis, limit, positive):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        inside_a = (a[axis]>=limit) if positive else (a[axis]<=limit)
        inside_b = (b[axis]>=limit) if positive else (b[axis]<=limit)
        if inside_a: result.append(a)
        if inside_a != inside_b:
            t=(limit-a[axis])/(b[axis]-a[axis]);result.append(tuple(a[i]+(b[i]-a[i])*t for i in range(4)))
    return result

def roads(chunk,mat):
    verts,faces,colors=[],[],[];cx,cz=chunk['x'],chunk['z']
    def patch(poly):
        for axis,limit,positive in [(0,cx-150,True),(0,cx+150,False),(1,cz-150,True),(1,cz+150,False)]:
            if poly:poly=clip(poly,axis,limit,positive)
        if len(poly)<3:return
        signed=sum(poly[j][0]*poly[(j+1)%len(poly)][1]-poly[(j+1)%len(poly)][0]*poly[j][1] for j in range(len(poly)))
        if abs(signed)<1e-10:return
        if signed>0:poly.reverse()
        base=len(verts)
        for x,z,y,alpha in poly:verts.append((x,z,y));colors.append((1,1,1,alpha))
        for j in range(1,len(poly)-1):faces.append((base,base+j,base+j+1))
    for path_index,path in enumerate(SOURCE['paths']):
        pts=path['points']; half=path['width']/2
        def join(index):
            normals=[]
            for j in [index-1,index]:
                if j<0 or j>=len(pts)-1:continue
                dx,dz=pts[j+1]['x']-pts[j]['x'],pts[j+1]['z']-pts[j]['z'];length=math.hypot(dx,dz)
                if length>.001:normals.append((-dz/length,dx/length))
            if len(normals)==1:return normals[0]
            a,b=normals;denom=max(.5,1+a[0]*b[0]+a[1]*b[1]);return ((a[0]+b[0])/denom,(a[1]+b[1])/denom)
        for segment,(a,b) in enumerate(zip(pts,pts[1:])):
            dx,dz=b['x']-a['x'],b['z']-a['z'];length=math.hypot(dx,dz)
            if length<.001:continue
            nx,nz=-dz/length,dx/length;count=math.ceil(length/3.125)
            start_normal,end_normal=join(segment),join(segment+1)
            bands=[(-half-.65,0),(-half+.5,1),(half-.5,1),(half+.65,0)]
            for i in range(count):
                for band in range(3):
                    poly=[]
                    for t,k in [(i/count,band),((i+1)/count,band),((i+1)/count,band+1),(i/count,band+1)]:
                        width,alpha=bands[k]
                        nx=start_normal[0]*(1-t)+end_normal[0]*t;nz=start_normal[1]*(1-t)+end_normal[1]*t
                        x=a['x']+dx*t+nx*width;z=a['z']+dz*t+nz*width
                        poly.append((x,z,height(x,z)+.045+path_index*.0005,alpha))
                    patch(poly)
    for junction in JUNCTIONS:
        # A submillimetre separation from every touching ribbon avoids coplanar alpha flicker.
        offset=.045+(max(junction['paths'])+1)*.0005
        for polygon in transition_polygons(junction):
            patch([(x,z,height(x,z)+offset,alpha) for x,z,alpha in polygon])
    if verts:return mesh_object(chunk['assetKey']+'_roads',verts,faces,colors,mat,cx,cz)


def water_material():
    mat=bpy.data.materials.new('Cinderfen_shallow_peat_water');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(.045,.065,.044,1)
    shader.inputs['Roughness'].default_value=.22
    shader.inputs['Metallic'].default_value=.12
    shader.inputs['IOR'].default_value=1.333
    side=512;z,x=np.mgrid[0:side,0:side]/side*math.tau
    dx=.025*np.cos(x*7+z*3)+.012*np.cos(x*3-z*5)
    dz=.025*3/7*np.cos(x*7+z*3)-.012*5/3*np.cos(x*3-z*5)
    normal=np.stack((-dx,-dz,np.ones_like(x)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    pixels=np.concatenate((normal*.5+.5,np.ones((side,side,1))),axis=-1).astype(np.float32)
    detail=bpy.data.images.new('Cinderfen_water_ripples',width=side,height=side,alpha=False)
    detail.colorspace_settings.name='Non-Color';detail.pixels.foreach_set(pixels.ravel())
    detail.filepath_raw=str(WORK/'textures/source/Cinderfen_water_ripples.png');detail.file_format='PNG';detail.save()
    texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=detail
    mapping=mat.node_tree.nodes.new('ShaderNodeNormalMap')
    mat.node_tree.links.new(texture.outputs['Color'],mapping.inputs['Color'])
    mat.node_tree.links.new(mapping.outputs['Normal'],shader.inputs['Normal'])
    return mat


def water(chunk,mat):
    # Clip each surveyed triangle at the water table: causeways and raised pads
    # remain dry, and neighboring sectors share the exact shoreline samples.
    cx,cz=chunk['x'],chunk['z'];level=SOURCE['waterLevel'];step=STEP/2
    verts,faces,colors=[],[],[]
    cells=round(300/step)
    for iz in range(cells):
        for ix in range(cells):
            points=[(cx-150+(ix+dx)*step,cz-150+(iz+dz)*step) for dx,dz in [(0,0),(0,1),(1,1),(1,0)]]
            corners=[(x,z,height(x,z),1) for x,z in points]
            for indices in [(0,1,2),(0,2,3)]:
                polygon=clip([corners[i] for i in indices],2,level,False)
                if len(polygon)<3:continue
                area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1]))
                if abs(area)<1e-8:continue
                base=len(verts)
                for x,z,_,_ in polygon:verts.append((x,z,level));colors.append((1,1,1,1))
                faces.extend((base,base+i,base+i+1) for i in range(1,len(polygon)-1))
    if not verts:return
    obj=mesh_object(chunk['assetKey']+'_peat_water',verts,faces,colors,mat,cx,cz)
    obj.data.normals_split_custom_set_from_vertices([(0,0,1)]*len(verts))
    obj['noGroundSupport']=True
    obj['waterLevel']=level
    return obj


def externalize(file):
    data=file.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);binary=data[28+n:];skip=set()
    # Blender 5 still emits the linked opacity as COLOR_1. glTF renderers use
    # COLOR_0, so preserve the authored RGBA there and discard the white filler.
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            material_name=doc['materials'][primitive['material']]['name']
            if material_name=='Cinderfen_limestone_road' and 'COLOR_1' in primitive['attributes']:
                primitive['attributes']['COLOR_0']=primitive['attributes'].pop('COLOR_1')
    used=set()
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            used.update(primitive['attributes'].values());used.add(primitive['indices'])
    accessor_map={old:new for new,old in enumerate(sorted(used))}
    doc['accessors']=[doc['accessors'][old] for old in sorted(used)]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            primitive['attributes']={key:accessor_map[value] for key,value in primitive['attributes'].items()}
            primitive['indices']=accessor_map[primitive['indices']]
    for im in doc.get('images',[]):
        idx=im.pop('bufferView');skip.add(idx);v=doc['bufferViews'][idx];raw=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
        name=hashlib.sha256(raw).hexdigest()[:20]+'.png';(WORK/'textures/cinderfen_terrain'/name).write_bytes(raw);im['uri']='../textures/cinderfen_terrain/'+name
    used_views={accessor['bufferView'] for accessor in doc['accessors']}
    skip.update(index for index in range(len(doc['bufferViews'])) if index not in used_views)
    views=[];remap={};result=bytearray()
    for i,v in enumerate(doc['bufferViews']):
        if i in skip:continue
        result.extend(b'\0'*((-len(result))%4));remap[i]=len(views);views.append({**v,'byteOffset':len(result)})
        start=v.get('byteOffset',0);result.extend(binary[start:start+v['byteLength']])
    for a in doc['accessors']:
        if 'bufferView' in a:a['bufferView']=remap[a['bufferView']]
    doc['bufferViews']=views;doc['buffers'][0]['byteLength']=len(result)
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);result+=b'\0'*((-len(result))%4)
    file.write_bytes(struct.pack('<III',0x46546c67,2,28+len(raw)+len(result))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(result),0x004e4942)+result)

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
grass=material('Cinderfen_short_grass','peat_albedo.png');roadmat=material('Cinderfen_limestone_road','causeway_albedo.png',True)
watermat=water_material()
parser=argparse.ArgumentParser();parser.add_argument('--chunks',default='')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
selected=set(args.chunks.split(',')) if args.chunks else None
report_file=WORK/'build-report.json'
previous={item['key']:item for item in json.loads(report_file.read_text())} if selected and report_file.exists() else {}
report=[]
for chunk in SOURCE['terrain']['chunks']:
    if selected and chunk['assetKey'] not in selected and '_'.join(chunk['assetKey'].split('_')[-2:]) not in selected:
        if chunk['assetKey'] in previous:report.append(previous[chunk['assetKey']])
        continue
    record={'key':chunk['assetKey'],'collisionKey':chunk['collisionAssetKey'],'x':chunk['x'],'z':chunk['z'],'lods':[],
            'buildToolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'junctionToolSha256':hashlib.sha256((WORK/'road_junctions.py').read_bytes()).hexdigest()}
    for lod in range(3):
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        surface=land(chunk,lod,grass);roads(chunk,roadmat);water(chunk,watermat)
        if lod==0:bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'masters'/(chunk['assetKey']+'.blend')))
        filename=chunk['assetKey']+('' if lod==0 else f'_lod{lod}')+'.glb';file=WORK/'runtime'/filename
        bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',export_yup=True,export_normals=True,export_tangents=True,export_texcoords=True,export_attributes=False,export_extras=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
        externalize(file)
        triangles=sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH')
        record['lods'].append({'level':lod,'model':filename,'triangles':triangles,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    report.append(record)
    print('COMPLETE',chunk['assetKey'],flush=True)
report_file.write_text(json.dumps(report,indent=2)+'\n')
print('Selected authored terrain sectors exported.' if selected else 'Sixteen authored terrain sectors exported.')

