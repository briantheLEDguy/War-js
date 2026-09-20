"""Finish the original workshop cages and cut declared receiving sockets."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from review_items import audit,render
SOURCE_PATH=ROOT/'source/items.json';SOURCE=json.loads(SOURCE_PATH.read_text())
COLORS={'oak':(.18,.102,.045,1),'oak_end':(.22,.132,.069,1),'working_oak':(.25,.159,.081,1),'forged_iron':(.039,.045,.048,1),'worked_steel':(.15,.163,.168,1),'hemp':(.30,.231,.129,1),'cut_stone':(.18,.187,.174,1)}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)

def mesh(record,collection,materials,lod):
    data=bpy.data.meshes.new(record['name']+'.original_mesh');data.from_pydata(record['vertices'],[],record['faces']);data.update()
    for material in SOURCE['materials']:data.materials.append(materials[material])
    grain=data.attributes.new(name='piece_grain',type='FLOAT_VECTOR',domain='POINT')
    phase=int(hashlib.sha256(record['name'].encode()).hexdigest()[:8],16)/0xffffffff
    for attribute,value in zip(grain.data,record['grain_coordinates']):attribute.vector=(value[0]+phase,value[1],value[2]+phase*2.7)
    data.uv_layers.new(name='source_uv')
    for polygon,uv,material in zip(data.polygons,record['corner_uv'],record['face_materials']):
        polygon.material_index=SOURCE['materials'].index(material);polygon.use_smooth=record['smooth']
        for index,point in zip(polygon.loop_indices,uv):data.uv_layers['source_uv'].data[index].uv=point
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(record['name'],data);collection.objects.link(obj);obj['source']='source/items.json';obj['source_role']=record['role'];obj['original_piece']=record['name'];obj['lod']=lod
    return obj

def seat_stones(objects):
    stones=sorted([o for o in objects if o['original_piece'].startswith('individually_cut_siege_stone_')],key=lambda o:int(o['original_piece'].rsplit('_',1)[1]));floor=[o for o in objects if o['original_piece'].startswith('crib_floor_board_')];records=[]
    for index,stone in enumerate(stones):
        supports=floor if index<6 else stones[:6];points=[];faces=[];owners=[]
        for support in supports:
            offset=len(points);points.extend(support.matrix_world@v.co for v in support.data.vertices)
            for face in support.data.polygons:faces.append([offset+i for i in face.vertices]);owners.append(support['original_piece'])
        tree=BVHTree.FromPolygons(points,faces,all_triangles=True);samples=[]
        for face in stone.data.polygons:
            if face.normal.z>-.10:continue
            vertices=[stone.matrix_world@stone.data.vertices[v].co for v in face.vertices]
            samples.extend(vertices+[sum(vertices,Vector())/3])
        def measure(matrix):
            gaps=[]
            for original in samples:
                point=matrix@original
                hit,normal,face_index,distance=tree.ray_cast(point+Vector((0,0,.35)),Vector((0,0,-1)),2)
                if hit is not None:gaps.append({'gap':distance-.35,'point':list(point),'support':owners[face_index]})
            return gaps
        pose=[0,0,0,0];centre=sum((v.co for v in stone.data.vertices),Vector())/len(stone.data.vertices)
        def transform(values):return Matrix.Translation(centre+Vector((values[2],values[3],0)))@Euler((values[0],values[1],0)).to_matrix().to_4x4()@Matrix.Translation(-centre)
        if index>=6:
            import itertools
            def rank(values):
                gaps=measure(transform(values));best={}
                for row in gaps:
                    if row['support'] not in best or row['gap']<best[row['support']]['gap']:best[row['support']]=row
                ordered=sorted(best.values(),key=lambda row:row['gap'])
                if len(ordered)<3:return 10
                triangle=[Vector(row['point'][:2]) for row in ordered[:3]];p=Vector((centre.x+values[2],centre.y+values[3]));crosses=[]
                for a,b in zip(triangle,triangle[1:]+triangle[:1]):crosses.append((b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x))
                outside=not(all(v>=-.0005 for v in crosses) or all(v<=.0005 for v in crosses))
                return ordered[2]['gap']-ordered[0]['gap']+(1 if outside else 0)
            best_score=rank(pose)
            for angle_step,position_step in [(.12,.035),(.06,.018),(.03,.009),(.015,.0045),(.0075,.0023)]:
                origin=pose[:]
                for offsets in itertools.product((-1,0,1),repeat=4):
                    candidate=[value+offset*step for value,offset,step in zip(origin,offsets,(angle_step,angle_step,position_step,position_step))]
                    if max(abs(candidate[0]),abs(candidate[1]))>.30 or max(abs(candidate[2]),abs(candidate[3]))>.075:continue
                    score=rank(candidate)
                    if score<best_score:pose=candidate;best_score=score
            if best_score>.012:raise RuntimeError(f'Upper stone needs a stable three-contact packing pose: {stone.name} {best_score}')
        matrix=transform(pose);gaps=measure(matrix)
        if not gaps:raise RuntimeError('Unsupported stone: '+stone.name)
        contact=min(gaps,key=lambda row:row['gap']);delta=-contact['gap']-.00075
        if abs(delta)>.24:raise RuntimeError('Unexpected stone seating displacement: '+stone.name)
        stone.matrix_world=Matrix.Translation(Vector((0,0,delta)))@matrix;bpy.context.view_layer.update()
        nearby=[{'support':r['support'],'gapAfterM':r['gap']+delta,'sample':r['point']} for r in gaps if r['gap']-contact['gap']<.020]
        records.append({'part':stone['original_piece'],'packingPose':{'rotationXY':pose[:2],'offsetXY':pose[2:]},'translationZ':delta,'minimumGapM':contact['gap']+delta,'nearestSupports':sorted(set(r['support'] for r in nearby)),'samples':len(gaps),'contactSamples':nearby[:12]})
    return records

def build(key,lod,preview):
    bpy.ops.wm.read_factory_settings(use_empty=True);definition=SOURCE['assets'][key];records=definition['lods'][lod]['objects'];materials={}
    for name,color in COLORS.items():
        material=bpy.data.materials.new(name+'.source_shape');material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.76 if name not in ('forged_iron','worked_steel') else .48;shader.inputs['Metallic'].default_value=.9 if name in ('forged_iron','worked_steel') else 0;materials[name]=material
    finished=bpy.data.collections.new(key+f'.finished_lod{lod}');bpy.context.scene.collection.children.link(finished)
    retained=bpy.data.collections.new('Retained_original_control_cages_and_cutters');bpy.context.scene.collection.children.link(retained)
    sources={record['name']:mesh(record,retained,materials,lod) for record in records}
    objects=[];cuts=[]
    for record in records:
        if record['role']!='visible':continue
        source=sources[record['name']];obj=source.copy();obj.data=source.data.copy();obj.name=record['name']+'.finished';finished.objects.link(obj);bpy.context.view_layer.objects.active=obj
        for name in record['cutters']:
            modifier=obj.modifiers.new('authored_socket_'+name,'BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=sources[name];bpy.ops.object.modifier_apply(modifier=modifier.name);cuts.append({'part':record['name'],'cutter':name})
        if lod<2 and record['bevelM']:
            bevel=obj.modifiers.new('fitted_edge_finish','BEVEL');bevel.width=record['bevelM']*(1 if lod==0 else .7);bevel.segments=2 if lod==0 else 1;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(33);bevel.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
            if not record['smooth']:
                normal=obj.modifiers.new('preserve_worked_face_normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=50;bpy.ops.object.modifier_apply(modifier=normal.name)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001);bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges));bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();objects.append(obj)
    for source in sources.values():source.hide_render=True;source.hide_set(True)
    stone_supports=seat_stones(objects) if key.endswith('ammunition_cradle') else []
    result=audit(objects);invalid=[row for row in result['meshes'] if row['boundary_edges_after_positional_weld'] or row['multi_face_edges_after_positional_weld'] or row['loose_edges']]
    if invalid:
        save(ROOT/'review'/f'{key}_lod{lod}_topology_failure.json',invalid);raise RuntimeError(f'Source topology failed: {invalid[:3]}')
    path=ROOT/'masters'/f'{key}_lod{lod}.source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path))
    evidence={'asset':key,'lod':lod,'stage':'source construction proof; flat material colors; not exported or accepted','sourceSha256':sha(SOURCE_PATH),'authorSha256':sha(ROOT/'tools/author_items.py'),'builderSha256':sha(Path(__file__)),'master':str(path.relative_to(ROOT)).replace('\\','/'),'masterSha256':sha(path),'triangles':sum(len(o.data.polygons) for o in objects),'audit':result,'cutSockets':cuts,'stoneSupports':stone_supports,'views':{}}
    if preview:
        image=ROOT/'review'/f'{key}_lod{lod}_source.png';camera=render(objects,image);evidence['views']['overall']={'image':image.name,'sha256':sha(image),'camera':camera}
    save(ROOT/'review'/f'{key}_lod{lod}_source.json',evidence);print('WORKSHOP_SOURCE',key,lod,evidence['triangles'],len(cuts),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));parser.add_argument('--lods',default='0');parser.add_argument('--preview',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for key in args.assets.split(','):
        for lod in args.lods.split(','):build(key,int(lod),args.preview)
