"""Author fitted trestle joinery and four original polearms from explicit surfaces."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesh_authoring import explicit,plate,loft,strand,cut_socket,finish,BEAM
from export_tangents import repair_export_tangents
KEY='frontier_field_arms_rack'

def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def save(file,value):
    temp=file.with_suffix(file.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(file)
def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {'minimum':[min(v[i] for v in points) for i in range(3)],'maximum':[max(v[i] for v in points) for i in range(3)]}
def audit(objects):
    records=[]
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        records.append({'part':obj.name,'boundary':sum(e.is_boundary for e in bm.edges),
          'multi':sum(len(e.link_faces)>2 for e in bm.edges),'loose':sum(not e.link_faces for e in bm.edges),
          'triangles':sum(len(f.verts)-2 for f in bm.faces)})
        bm.free()
    return {**{field:sum(r[field] for r in records) for field in ('boundary','multi','loose','triangles')},
            'meshes':records,'boundsZUp':bounds(objects)}

def materials(lod):
    result={}
    for name in ('oak','iron','brass','leather','steel'):
        mat=bpy.data.materials.new('supply_rack.'+name);mat.use_nodes=True;mat.use_backface_culling=True
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
        for channel in ('basecolor','normal','orm'):
            im=bpy.data.images.load(str(ROOT/'textures'/f'{name}_lod{lod}_{channel}.png'))
            im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
            node=nodes.new('ShaderNodeTexImage');node.image=im;links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
        links.new(maps['basecolor'].outputs['Color'],shader.inputs['Base Color'])
        normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';normal.inputs['Strength'].default_value=.2 if name=='steel' else .65
        links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        separate=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],separate.inputs[0])
        links.new(separate.outputs['Green'],shader.inputs['Roughness']);links.new(separate.outputs['Blue'],shader.inputs['Metallic'])
        result[name]=mat
    return result

def build(lod):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
    mats=materials(lod);parts=[];joints=[]
    original=bpy.data.collections.new('Editable_original_construction');bpy.context.scene.collection.children.link(original)
    def hold(obj):parts.append(obj);return obj
    def retain(obj):
        copy=obj.copy();copy.data=obj.data.copy();copy.name='cage_'+obj.name;original.objects.link(copy);copy.hide_render=True;copy.hide_set(True)
    def socket(receiver,cutter):
        retain(cutter);cut_socket(receiver,cutter)
    def contact(a,b):joints.append({'part':a.name,'support':b.name})
    def pin(name,centre,axis,length,diameter,material='iron'):
        a=Vector(centre)-Vector(axis)*length/2;b=Vector(centre)+Vector(axis)*length/2
        return hold(strand(name,[a,a.lerp(b,.13),a.lerp(b,.87),b],diameter,mats[material],lod))
    feet=[];posts=[]
    for sx in(-1,1):
        # Broad, planed trestle feet with relieved underside and a pegged receiving mortise.
        foot=hold(plate(f'shaped_ground_skid_{sx}',[(-.43,0),(-.24,0),(-.20,.025),(.20,.025),(.24,0),(.43,0),(.43,.048),(.36,.11),(-.35,.11),(-.43,.065)],.165,mats['oak'],'X',sx*.71,.003))
        post=hold(plate(f'pegged_upright_{sx}',[(sx*.71-.060,.060),(sx*.71+.060,.060),(sx*.71+.060,1.36),(sx*.71+.085,1.45),(sx*.71+.075,1.525),(sx*.71,1.565),(sx*.71-.075,1.525),(sx*.71-.085,1.45),(sx*.71-.060,1.36)],.115,mats['oak'],'Y',.035,.003))
        cutter=post.copy();cutter.data=post.data.copy();bpy.context.scene.collection.objects.link(cutter);cutter.name=f'foot_receiving_mortise_{sx}';cutter.scale.x=1.0008;cutter.scale.y=1.01;socket(foot,cutter);contact(post,foot)
        pin(f'foot_cross_peg_{sx}',(sx*.71,.035,.087),(0,1,0),.18,.014,'oak')
        feet.append(foot);posts.append(post)
    rail=hold(loft('pierced_upper_weapon_rest',[(-.785,.035,1.315,.150,.115),(-.73,.035,1.315,.153,.16),(-.65,.035,1.315,.150,.16),(.65,.035,1.315,.150,.16),(.73,.035,1.315,.153,.16),(.785,.035,1.315,.150,.115)],mats['oak'],bevel=.002))
    heel=hold(loft('pierced_lower_heel_rest',[(-.785,.005,.215,.225,.115),(-.71,.005,.215,.235,.15),(.71,.005,.215,.235,.15),(.785,.005,.215,.225,.115)],mats['oak'],bevel=.002))
    for post in posts:
        for timber in(rail,heel):
            cutter=timber.copy();cutter.data=timber.data.copy();bpy.context.scene.collection.objects.link(cutter);cutter.name=post.name+'_'+timber.name+'_mortise';cutter.scale.y=1.008;socket(post,cutter);contact(post,timber)
    # Cut the receiving rests from the same centre lines used by the racked polearms.
    for index,x in enumerate((-.45,-.15,.15,.45)):
        z0=.16;tip=(2.19,2.38,2.30,2.13)[index];slope=(.055,.05,.06,.047)[index]
        def centre(z):return Vector((x,-.014+(z-z0)*slope,z))
        radius=.0205;cy=centre(1.315).y
        outline=[(x-radius,-.23),(x+radius,-.23),(x+radius,cy)]+[(x+radius*math.cos(t),cy+radius*math.sin(t)) for t in [i*math.pi/(16 if lod==0 else 10 if lod==1 else 8) for i in range(1,(16 if lod==0 else 10 if lod==1 else 8)+1)]]
        socket(rail,plate(f'upper_rest_slot_{index}',outline,.24,mats['oak'],'Z',1.315,0))
        socket(heel,loft(f'heel_receiving_bore_{index}',[(*centre(z),.046,.046) for z in(.16,.17,.25,.32)],mats['oak'],section=[(math.cos(i*math.tau/16)*.5,math.sin(i*math.tau/16)*.5) for i in range(16)],smooth=True,bevel=0))
        shaft=hold(loft(f'tapered_ash_shaft_{index}',[(*centre(z),d,d) for z,d in[(z0,.032),(.24,.038),(.75,.037),(1.35,.034),(tip-.35,.030),(tip-.27,.028)]],mats['oak'],section=[(math.cos(i*math.tau/(20,14,10)[lod])*.5,math.sin(i*math.tau/(20,14,10)[lod])*.5) for i in range((20,14,10)[lod])],smooth=True,bevel=0))
        contact(shaft,heel);contact(shaft,rail)
        # Hollow ferrule/socket profiles follow the actual tapered shaft, not floating caps.
        def collar(name,z,length,outer,inner,material):
            n=(24,16,10)[lod];verts=[];faces=[];uv=[]
            for dz,r in[(0,outer),(.008,outer*1.07),(length-.008,outer*1.03),(length,outer),(length,inner),(0,inner)]:
                c=centre(z+dz)
                for i in range(n):
                    a=i*math.tau/n;verts.append((c.x+math.cos(a)*r,c.y+math.sin(a)*r,c.z))
            for row in range(6):
                for i in range(n):
                    j=(i+1)%n;q=(row+1)%6;faces.append([row*n+i,row*n+j,q*n+j,q*n+i]);uv.append([(i/n,row/6),((i+1)/n,row/6),((i+1)/n,(row+1)/6),(i/n,(row+1)/6)])
            return hold(explicit(name,verts,faces,mats[material],uv,True,0))
        ferrule=collar(f'forged_heel_ferrule_{index}',z0,.10,.022,.016,'iron');contact(ferrule,shaft);contact(ferrule,heel)
        neck=collar(f'forged_blade_socket_{index}',tip-.38,.155,.024,.014,'iron');contact(neck,shaft)
        band=collar(f'socket_braze_ring_{index}',tip-.258,.022,.0255,.023,'brass');contact(band,neck)
        # Leaf blades have a central forged ridge, bevelled cutting margins and a real tip.
        section=[(-1,0),(-.92,-.17),(-.30,-.72),(0,-1),(.30,-.72),(.92,-.17),(1,0),(.92,.17),(.30,.72),(0,1),(-.30,.72),(-.92,.17)]
        proportions=[(0,.18),(.17,.75),(.42,1),(.65,.68),(.86,.32),(1,.018)]
        verts=[];faces=[];uv=[];width=(.045,.056,.048,.041)[index]
        for t,w in proportions:
            c=centre(tip-.25+t*.25)
            for a,b in section:verts.append((c.x+a*width*w,c.y+b*(.005*(1-t)+.0007),c.z))
        n=len(section)
        for row in range(len(proportions)-1):
            for j in range(n):
                k=(j+1)%n;faces.append([row*n+j,row*n+k,(row+1)*n+k,(row+1)*n+j]);uv.append([(j/n,row/5),((j+1)/n,row/5),((j+1)/n,(row+1)/5),(j/n,(row+1)/5)])
        faces.extend([list(reversed(range(n))),list(range(5*n,6*n))]);uv.extend([list(reversed(section)),list(section)])
        blade=hold(explicit(f'forged_leaf_blade_{index}',verts,faces,mats['steel'],uv,False,0));contact(blade,neck)
        # The overlapping spiral is an actual closed leather strip with continuous winding.
        steps=(220,132,70)[lod];rings=[]
        gripRadius=.0195/math.cos(math.pi/(steps/10))
        for j in range(steps+1):
            t=j/steps;z=.70+t*.24;a=t*math.tau*10;c=centre(z)
            rings.append((c.x+math.cos(a)*gripRadius,c.y+math.sin(a)*gripRadius,z,.002,.027))
        grip=hold(loft(f'continuous_leather_grip_{index}',rings,mats['leather'],smooth=True,bevel=0,guide=(0,0,1)));contact(grip,shaft)
        for z in(.692,.932):
            cuff=collar(f'grip_end_binding_{index}_{z}',z,.017,.0215,.018,'leather');contact(cuff,shaft)
    # Front/rear brace plates bridge the pegged joints; rivets pierce timber on both sides.
    for sx in(-1,1):
        for sy in(-1,1):
            points=[(sx*.71,.08),(sx*.69,.14),(sx*.59,.27),(sx*.58,.33),(sx*.65,.32),(sx*.76,.18),(sx*.78,.11)]
            brace=hold(plate(f'forged_foot_brace_{sx}_{sy}',points,.005,mats['iron'],'Y',.035+sy*.061,.001));contact(brace,posts[0 if sx<0 else 1]);contact(brace,heel)
            for x,z in[(sx*.714,.135),(sx*.617,.290)]:pin(f'brace_clench_rivet_{sx}_{sy}_{z}',(x,.035+sy*.064,z),(0,1,0),.018,.013)
        for z in(.215,1.315):pin(f'tenon_cross_peg_{sx}_{z}',(sx*.71,.035,z),(0,1,0),.176,.016,'oak')
    for obj in parts:
        if obj.name.startswith(('shaped_ground_skid',)):
            for loop in obj.data.uv_layers[0].data:loop.uv=(loop.uv.y,loop.uv.x)
        retain(obj)
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    source=ROOT/'masters'/f'{KEY}_lod{lod}.source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source))
    finish(parts,lod);result=audit(parts)
    save(ROOT/'review'/f'{KEY}_lod{lod}_source-audit.json',result)
    if any(result[k] for k in ('boundary','multi','loose')):raise RuntimeError('Construction topology failed')
    # All visible geometry lies within this measured enclosure. Below-body space remains open.
    if lod==0:
        b=result['boundsZUp'];lo=b['minimum'];hi=b['maximum']
        skids=[o for o in parts if o.name.startswith('shaped_ground_skid')]
        posts=[o for o in parts if o.name.startswith('pegged_upright')]
        masses={'racked_arms_and_rest_rails':[o for o in parts if o not in skids+posts]}
        masses.update({o.name:[o] for o in skids+posts})
        measurements=[{'name':name,'parts':[o.name for o in objects],'boundsZUp':bounds(objects)} for name,objects in masses.items()]
        colliders=[]
        for group in measurements:
            a=group['boundsZUp']['minimum'];b=group['boundsZUp']['maximum']
            colliders.append({'x':(a[0]+b[0])/2,'z':-(a[1]+b[1])/2,'width':b[0]-a[0],'depth':b[1]-a[1],'minY':max(0,a[2]),'maxY':b[2]})
        front={'minimum':[-.9,0,.47],'maximum':[.9,2,1.7]}
        save(ROOT/'builder-contract.json',{'schemaVersion':1,'runtimeReady':False,'assets':{KEY:{'label':'Field Arms Rack','group':'Universal Town Logistics','kind':'field_arms_rack','model':KEY+'_lod0.glb','defaultScale':{'x':1,'y':1,'z':1},'colliderSpace':'model','sourceMasterSha256':sha(source),'boundsYUp':{'minimum':[lo[0],lo[2],-hi[1]],'maximum':[hi[0],hi[2],-lo[1]]},'footprint':{'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'chainAxis':'x'},'colliders':colliders,'collisionMeasurements':measurements,'walkableSurfaces':[],'cameraSolid':True,'standingPoint':{'x':0,'y':0,'z':1.02},'workingFront':front,'approachSource':{'minimum':[-.9,-1.7,0],'maximum':[.9,-.47,2]},'placementDatum':'Two planed skids at Y0. Racked static weapons; no pickup or equipment interaction.'}}})
    batches={}
    for obj in parts:batches.setdefault(obj.data.materials[0].name,[]).append(obj)
    exports=[]
    for name,objects in batches.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=objects[0];obj.name=KEY+'.'+name.split('.')[-1]
        # Boolean interiors and endgrain get independent noncollapsed planar charts.
        obj.data.calc_tangents(uvmap='authored_uv');invalid={loop.index for loop in obj.data.loops if loop.tangent.length<.99 or abs(loop.tangent.dot(obj.data.corner_normals[loop.index].vector))>.001};obj.data.free_tangents()
        for face in obj.data.polygons:
            if not any(i in invalid for i in face.loop_indices):continue
            points=[obj.data.vertices[i].co for i in face.vertices];a,b=max(((0,1),(1,2),(2,0)),key=lambda pair:(points[pair[1]]-points[pair[0]]).length)
            edge=points[b]-points[a];side=edge.normalized();up=face.normal.cross(side).normalized()
            heights=[(point-points[a]).dot(up)/edge.length for point in points]
            scale=max(1,.008/max(max(heights)-min(heights),1e-12))
            for loop,point in zip(face.loop_indices,points):obj.data.uv_layers[0].data[loop].uv=((point-points[a]).dot(side)/edge.length,(point-points[a]).dot(up)/edge.length*scale)
        obj.data.update();obj.data.calc_tangents(uvmap='authored_uv')
        if any(loop.tangent.length>.01 and abs(loop.tangent.dot(obj.data.corner_normals[loop.index].vector))>.001 for loop in obj.data.loops):raise RuntimeError('Nonorthogonal authored tangent '+name)
        obj.data.free_tangents();exports.append(obj)
    final=ROOT/'masters'/f'{KEY}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(final))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:obj.select_set(True)
    bpy.context.view_layer.objects.active=exports[0]
    target=ROOT/'runtime'/f'{KEY}_lod{lod}.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True)
    tangentRepair=repair_export_tangents(target);save(ROOT/'review'/f'{KEY}_lod{lod}_tangent-repair.json',tangentRepair)
    record={'tangentRepair':tangentRepair,'key':KEY,'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':result['triangles'],'parts':len(parts),'materials':len(exports),'joints':joints,'sourceMaster':str(source.relative_to(ROOT)).replace('\\','/'),'sourceMasterSha256':sha(source),'master':str(final.relative_to(ROOT)).replace('\\','/'),'masterSha256':sha(final),'audit':result,'sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p)} for p in sorted((ROOT/'tools').glob('*.py'))]+[{'path':'textures/sources.json','sha256':sha(ROOT/'textures/sources.json')}]}
    save(ROOT/'review'/f'{KEY}_lod{lod}_build.json',record);print('RACK_EXPORTED',lod,result['triangles'],len(parts),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for lod in map(int,args.lods.split(',')):build(lod)
