"""Author a joined, iron-bound logistics chest from explicit construction surfaces."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesh_authoring import explicit,plate,loft,strand,cut_socket,finish,BEAM
KEY='frontier_field_supply_chest'

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
    for name in ('oak','iron','brass','leather'):
        mat=bpy.data.materials.new('supply_chest.'+name);mat.use_nodes=True;mat.use_backface_culling=True
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
        for channel in ('basecolor','normal','orm'):
            im=bpy.data.images.load(str(ROOT/'textures'/f'{name}_lod{lod}_{channel}.png'))
            im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
            node=nodes.new('ShaderNodeTexImage');node.image=im;links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
        links.new(maps['basecolor'].outputs['Color'],shader.inputs['Base Color'])
        normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';normal.inputs['Strength'].default_value=.65
        links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        separate=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],separate.inputs[0])
        links.new(separate.outputs['Green'],shader.inputs['Roughness']);links.new(separate.outputs['Blue'],shader.inputs['Metallic'])
        result[name]=mat
    return result

def arch(y):return .648+.132*(max(0,1-(y/.365)**2))

def lid_band(name,route,width,thickness,material):
    # A fixed transverse axis prevents a frame flip where the strap turns upright.
    vertices=[];faces=[];uv=[]
    for i,point in enumerate(route):
        tangent=(Vector(route[min(len(route)-1,i+1)])-Vector(route[max(0,i-1)])).normalized()
        side=Vector((1,0,0));normal=tangent.cross(side).normalized()
        for a,b in BEAM:vertices.append(list(Vector(point)+side*a*width+normal*b*thickness))
    n=len(BEAM)
    for r in range(len(route)-1):
        for j in range(n):
            k=(j+1)%n;faces.append([r*n+j,r*n+k,(r+1)*n+k,(r+1)*n+j])
            uv.append([(j/n,r*.05),((j+1)/n,r*.05),((j+1)/n,(r+1)*.05),(j/n,(r+1)*.05)])
    faces.extend([list(reversed(range(n))),list(range((len(route)-1)*n,len(route)*n))]);uv.extend([list(reversed(BEAM)),list(BEAM)])
    return explicit(name,vertices,faces,material,uv,False,.001)

def build(lod):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
    mats=materials(lod);parts=[];joints=[]
    original=bpy.data.collections.new('Editable_original_construction');bpy.context.scene.collection.children.link(original)
    def hold(obj):parts.append(obj);return obj
    def retain(obj):
        copy=obj.copy();copy.data=obj.data.copy();copy.name='cage_'+obj.name;original.objects.link(copy);copy.hide_render=True;copy.hide_set(True)
    def pin(name,centre,axis,length,diameter,material='iron'):
        a=Vector(centre)-Vector(axis)*length/2;b=Vector(centre)+Vector(axis)*length/2
        return hold(strand(name,[a,a.lerp(b,.12),a.lerp(b,.88),b],diameter,mats[material],lod))
    # Planed feet and relief cutouts are part of the skid silhouette, not buried boxes.
    for sx in (-1,1):
        outline=[(-.348,0),(-.182,0),(-.165,.037),(.165,.037),(.182,0),(.348,0),(.353,.068),(.320,.121),(-.320,.121),(-.353,.068)]
        hold(plate(f'shaped_ground_skid_{sx}',outline,.105,mats['oak'],'X',sx*.493,.003))
    for i in range(4):
        y=-.2475+i*.165
        hold(loft(f'raised_floor_board_{i}',[(-.622,y,.125,.163,.034),(-.58,y,.126,.164,.035),(.04,y,.126,.164,.035),(.622,y,.125,.163,.034)],mats['oak'],bevel=.001))
    # Three dovetail rows lock front/back planks into actual end-board notches.
    for row in range(3):
        z=.145+row*.148;h=.146
        outline=[(-.609,z),(.609,z),(.609,z+.031),(.670,z+.018),(.670,z+.128),(.609,z+.114),(.609,z+h),(-.609,z+h),(-.609,z+.114),(-.670,z+.128),(-.670,z+.018),(-.609,z+.031)]
        ends=[]
        for sx in (-1,1):
            ends.append(hold(plate(f'end_board_{sx}_{row}',[(-.347,z),(.347,z),(.347,z+h),(-.347,z+h)],.062,mats['oak'],'X',sx*.639,.0015)))
        for sy in (-1,1):
            wall=hold(plate(f'dovetailed_long_board_{sy}_{row}',outline,.060,mats['oak'],'Y',sy*.318,.0015))
            for end in ends:
                cutter=wall.copy();cutter.data=wall.data.copy();bpy.context.scene.collection.objects.link(cutter)
                cutter.name=f'{end.name}_receiving_dovetail_{sy}'
                # 0.6 mm fitting clearance on the actual tenon contact faces.
                for vertex in cutter.data.vertices:vertex.co.y=sy*.318+(vertex.co.y-sy*.318)*1.02
                retain(cutter);cname=cutter.name;cut_socket(end,cutter)
                joints.append({'receiver':end.name,'tenon':wall.name,'receivingCage':cname,'clearanceM':.0006})
    # Lid end caps follow the same arch as the continuous stave undersides.
    for sx in (-1,1):
        outline=[(-.360,.590),(.360,.590)]+[(y,arch(y)-.023) for y in [.360-i*.720/(16 if lod==0 else 10 if lod==1 else 6) for i in range((16 if lod==0 else 10 if lod==1 else 6)+1)]]
        hold(plate(f'arched_lid_end_{sx}',outline,.034,mats['oak'],'X',sx*.652,.0015))
    for sy in(-1,1):
        hold(plate(f'lid_closing_rail_{sy}',[(-.669,.590),(.669,.590),(.676,.620),(.664,.632),(-.664,.632),(-.676,.620)],.034,mats['oak'],'Y',sy*.338,.001))
    for i in range(7):
        y0=-.362+i*.724/7+.0007;y1=-.362+(i+1)*.724/7-.0007
        samples=(5,4,3)[lod];top=[(y0+(y1-y0)*j/(samples-1),arch(y0+(y1-y0)*j/(samples-1))) for j in range(samples)]
        section=top+[(y,z-.025) for y,z in reversed(top)]
        vertices=[(x,y,z) for x in(-.689,-.668,0,.668,.689) for y,z in section];n=len(section);faces=[];uv=[]
        for r in range(4):
            for j in range(n):
                k=(j+1)%n;faces.append([r*n+j,r*n+k,(r+1)*n+k,(r+1)*n+j])
                uv.append([(j/n,r*.35),((j+1)/n,r*.35),((j+1)/n,(r+1)*.35),(j/n,(r+1)*.35)])
        faces.extend([list(reversed(range(n))),list(range(4*n,5*n))]);uv.extend([list(reversed(section)),section])
        hold(explicit(f'arched_lid_stave_{i}',vertices,faces,mats['oak'],uv,False,.001))
    # Three narrow straps are swept over the actual arched lid and overlap its shoulders.
    for ix,x in enumerate((-.494,0,.494)):
        count=(28,18,10)[lod]
        route=[(x,-.372,.598),(x,-.372,.641)]+[(x,y,arch(y)+.006) for y in [-.361+j*.722/count for j in range(count+1)]]+[(x,.372,.641),(x,.372,.602)]
        hold(lid_band(f'fitted_forged_lid_strap_{ix}',route,.047 if ix else .050,.009,mats['iron']))
        for iy,y in enumerate((-.317,-.14,.14,.317)):
            normal=Vector((0,2*.132*y/.365**2,1)).normalized()
            pin(f'lid_strap_rivet_{ix}_{iy}',(x,y,arch(y)+.014),normal,.016,.020,'brass')
    # Front/body binding plates flare at the rivets; all ends lie on real boards.
    for x in(-.494,.494):
        for sy in(-1,1):
            outline=[(x-.023,.163),(x+.023,.163),(x+.034,.190),(x+.023,.222),(x+.023,.519),(x+.034,.553),(x+.023,.582),(x-.023,.582),(x-.034,.553),(x-.023,.519),(x-.023,.222),(x-.034,.190)]
            hold(plate(f'forged_wall_binding_{x}_{sy}',outline,.008,mats['iron'],'Y',sy*.353,.001))
            for z in(.197,.34,.553):pin(f'wall_rivet_{x}_{sy}_{z}',(x,sy*.361,z),(0,1,0),.017,.022,'brass')
    # Rear hinge eyes have real bores around the through pin; leaves meet the eyes.
    for x in(-.494,.494):
        for dx,width in[(-.041,.026),(0,.050),(.041,.026)]:
            n=(20,14,10)[lod];radius=.0215
            route=[(x+dx,.374+radius*math.cos(j*math.tau/n),.623+radius*math.sin(j*math.tau/n)) for j in range(n)]
            hold(loft(f'hinge_eye_{x}_{dx}',[(*p,.007,width) for p in route],mats['iron'],section=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)],guide=(1,0,0),closed_path=True,bevel=0))
        pin(f'hinge_through_pin_{x}',(x,.374,.623),(1,0,0),.121,.032)
        outline=[(x-.027,.518),(x+.027,.518),(x+.031,.542),(x+.025,.606),(x-.025,.606),(x-.031,.542)]
        hold(plate(f'hinge_body_leaf_{x}',outline,.008,mats['iron'],'Y',.360,.001))
    # Closed hanging hasp, real receiving slot and keeper. Static closed pose only.
    hasp=hold(plate('closed_front_hasp',[(-.027,.654),(.027,.654),(.031,.570),(.039,.493),(.031,.449),(0,.431),(-.031,.449),(-.039,.493),(-.031,.570)],.012,mats['iron'],'Y',-.377,.001))
    slot=plate('hasp_receiving_slot',[(-.012,.480),(.012,.480),(.012,.508),(-.012,.508)],.060,mats['iron'],'Y',-.377,0)
    retain(slot);cut_socket(hasp,slot)
    pin('hasp_hinge_pin',(0,-.373,.644),(1,0,0),.078,.019,'brass')
    hold(plate('keeper_backplate',[(-.049,.456),(.049,.456),(.055,.514),(.041,.532),(-.041,.532),(-.055,.514)],.009,mats['iron'],'Y',-.354,.001))
    pin('keeper_through_hasp',(0,-.380,.494),(0,1,0),.075,.020,'brass')
    # Broad rectangular end bails are shaped continuous forged stock, physically in eye loops.
    for sx in (-1,1):
        for y in(-.154,.154):
            outline=[(y-.036,.346),(y+.036,.346),(y+.038,.456),(y+.022,.473),(y-.022,.473),(y-.038,.456)]
            hold(plate(f'bail_anchor_plate_{sx}_{y}',outline,.009,mats['iron'],'X',sx*.6745,.001))
            for z in(.363,.449):pin(f'bail_anchor_rivet_{sx}_{y}_{z}',(sx*.680,y,z),(1,0,0),.034,.019,'brass')
            n=(20,14,10)[lod]
            loop=[(sx*.681,y+.020*math.cos(j*math.tau/n),.412+.020*math.sin(j*math.tau/n)) for j in range(n+1)]
            hold(strand(f'bail_anchor_eye_{sx}_{y}',loop,.009,mats['iron'],lod))
        route=[(sx*.683,-.156,.428),(sx*.711,-.175,.397),(sx*.741,-.176,.348),(sx*.756,-.143,.322),(sx*.762,0,.314),(sx*.756,.143,.322),(sx*.741,.176,.348),(sx*.711,.175,.397),(sx*.683,.156,.428)]
        hold(strand(f'forged_carry_bail_{sx}',route,.019,mats['iron'],lod))
        # Leather wraps meet the working grip, with bevelled cloth-thin edges.
        turns=(15,10,6)[lod];steps=turns*(12,10,8)[lod];route=[]
        for j in range(steps+1):
            y=-.119+j*.238/steps;angle=j*turns*math.tau/steps
            cx=.762-.006*abs(y)/.143;cz=.314+.008*abs(y)/.143
            route.append((sx*(cx+.0105*math.cos(angle)),y,cz+.0105*math.sin(angle)))
        hold(loft(f'leather_grip_wrap_{sx}',[(*p,.003,.238/turns*1.12) for p in route],mats['leather'],guide=(0,1,0),bevel=0))
    # Brass inventory plate is empty of faction iconography; two incised score rules.
    plaque=hold(plate('inventory_brass_plate',[(-.168,.309),(-.157,.299),(.157,.299),(.168,.309),(.168,.401),(.155,.413),(-.155,.413),(-.168,.401)],.004,mats['brass'],'Y',-.352,.0008))
    for z in(.329,.379):
        cutter=plate('incised_inventory_rule', [(-.107,z-.0015),(.107,z-.0015),(.107,z+.0015),(-.107,z+.0015)],.004,mats['iron'],'Y',-.355,0)
        retain(cutter);cut_socket(plaque,cutter)
    for x in(-.145,.145):pin('inventory_plate_rivet_'+str(x),(x,-.357,.354),(0,1,0),.010,.010,'iron')
    for obj in parts:
        if obj.name.startswith(('shaped_ground_skid','end_board','dovetailed_long_board','arched_lid_end','lid_closing_rail')):
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
        handles=[o for o in parts if 'bail' in o.name or 'grip_wrap' in o.name]
        masses={'closed_chest_body':[o for o in parts if o not in skids+handles]}
        masses.update({o.name:[o] for o in skids})
        for sx in(-1,1):masses[f'carry_bail_{sx}']=[o for o in handles if (sum(v.co.x for v in o.data.vertices)>0)==(sx>0)]
        measurements=[{'name':name,'parts':[o.name for o in objects],'boundsZUp':bounds(objects)} for name,objects in masses.items()]
        colliders=[]
        for group in measurements:
            a=group['boundsZUp']['minimum'];b=group['boundsZUp']['maximum']
            colliders.append({'x':(a[0]+b[0])/2,'z':-(a[1]+b[1])/2,'width':b[0]-a[0],'depth':b[1]-a[1],'minY':max(0,a[2]),'maxY':b[2]})
        front={'minimum':[-.8,0,.45],'maximum':[.8,2,1.6]}
        save(ROOT/'builder-contract.json',{'schemaVersion':1,'runtimeReady':False,'assets':{KEY:{'label':'Field Supply Chest','group':'Universal Town Logistics','kind':'field_supply_chest','model':KEY+'_lod0.glb','defaultScale':{'x':1,'y':1,'z':1},'colliderSpace':'model','sourceMasterSha256':sha(source),'boundsYUp':{'minimum':[lo[0],lo[2],-hi[1]],'maximum':[hi[0],hi[2],-lo[1]]},'footprint':{'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'chainAxis':'x'},'colliders':colliders,'collisionMeasurements':measurements,'walkableSurfaces':[],'cameraSolid':True,'standingPoint':{'x':0,'y':0,'z':1.02},'workingFront':front,'approachSource':{'minimum':[-.8,-1.6,0],'maximum':[.8,-.45,2]},'placementDatum':'Two planed skids at Y0. Closed static scenery; no inventory or opening interaction.'}}})
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
        if any(loop.tangent.length<.99 or abs(loop.tangent.dot(obj.data.corner_normals[loop.index].vector))>.001 for loop in obj.data.loops):raise RuntimeError('Collapsed tangent chart '+name)
        obj.data.free_tangents();exports.append(obj)
    final=ROOT/'masters'/f'{KEY}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(final))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:obj.select_set(True)
    bpy.context.view_layer.objects.active=exports[0]
    target=ROOT/'runtime'/f'{KEY}_lod{lod}.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True)
    record={'key':KEY,'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':result['triangles'],'parts':len(parts),'materials':len(exports),'joints':joints,'sourceMaster':str(source.relative_to(ROOT)).replace('\\','/'),'sourceMasterSha256':sha(source),'master':str(final.relative_to(ROOT)).replace('\\','/'),'masterSha256':sha(final),'audit':result,'sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p)} for p in sorted((ROOT/'tools').glob('*.py'))]+[{'path':'textures/sources.json','sha256':sha(ROOT/'textures/sources.json')}]}
    save(ROOT/'review'/f'{KEY}_lod{lod}_build.json',record);print('CHEST_EXPORTED',lod,result['triangles'],len(parts),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for lod in map(int,args.lods.split(',')):build(lod)
