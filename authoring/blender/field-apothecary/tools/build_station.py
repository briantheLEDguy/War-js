"""Author, finish and export an original joined field apothecary station."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesh_authoring import beam,loft,plate,turned,strand,leaf,cut_socket,finish,BEAM,ROUND
KEY='frontier_field_apothecary'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def bounds(objects):
    points=[obj.matrix_world@v.co for obj in objects for v in obj.data.vertices]
    return {'minimum':[min(v[i] for v in points) for i in range(3)],'maximum':[max(v[i] for v in points) for i in range(3)]}
def audit(objects):
    records=[]
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        record={'part':obj.name,'boundary':sum(e.is_boundary for e in bm.edges),'multi':sum(len(e.link_faces)>2 for e in bm.edges),'loose':sum(not e.link_faces for e in bm.edges),'triangles':sum(len(f.verts)-2 for f in bm.faces)}
        bm.free();records.append(record)
    return {'meshes':records,'boundary':sum(r['boundary'] for r in records),'multi':sum(r['multi'] for r in records),'loose':sum(r['loose'] for r in records),'triangles':sum(r['triangles'] for r in records),'boundsZUp':bounds(objects)}

def materials(lod):
    result={}
    for name in ('timber','endgrain','iron','leather','amber','sage','dried','linen','stoneware'):
        mat=bpy.data.materials.new('apothecary.'+name);mat.use_nodes=True;mat.use_backface_culling=True
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
        for channel in('basecolor','normal','orm'):
            image=bpy.data.images.load(str(ROOT/'textures'/f'{name}_lod{lod}_{channel}.png'),check_existing=True);image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
            node=nodes.new('ShaderNodeTexImage');node.image=image;links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
        links.new(maps['basecolor'].outputs['Color'],shader.inputs['Base Color']);normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';normal.inputs['Strength'].default_value=.6;links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        separate=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],separate.inputs[0]);links.new(separate.outputs['Green'],shader.inputs['Roughness']);links.new(separate.outputs['Blue'],shader.inputs['Metallic'])
        result[name]=mat
    return result

def build(lod):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
    mats=materials(lod);parts=[];mass={};joints=[]
    retained=bpy.data.collections.new('Editable_original_parts_and_receiving_cages');bpy.context.scene.collection.children.link(retained)
    def hold(obj,group=None):
        parts.append(obj)
        if group:mass.setdefault(group,[]).append(obj)
        return obj
    def remember(obj):
        copy=obj.copy();copy.data=obj.data.copy();copy.name='cage_'+obj.name;retained.objects.link(copy);copy.hide_render=True;copy.hide_set(True)
    def socket(receiver,cutter):
        remember(cutter);cut_socket(receiver,cutter);joints.append({'receiver':receiver.name,'opening':cutter.name if cutter else 'mortise'})
    def pin(name,centre,axis=(0,1,0),length=.16,diameter=.024,material='endgrain'):
        a=Vector(centre)-Vector(axis)*length/2;b=Vector(centre)+Vector(axis)*length/2
        return hold(strand(name,[a,a.lerp(b,.08),a.lerp(b,.9),b],diameter,mats[material],lod))
    # Splayed legs have shouldered tenons seated through actual receiving holes.
    for sx in(-1,1):
        for sy in(-1,1):
            name=f'pegged_tapered_leg_{sx}_{sy}'
            obj=hold(loft(name,[(sx*.905,sy*.365,0,.15,.15),(sx*.896,sy*.36,.055,.158,.153),(sx*.86,sy*.33,.38,.139,.14),(sx*.842,sy*.312,.85,.127,.137)],mats['timber'],guide=(1,0,0),bevel=0),name)
            for vertex in obj.data.vertices[:len(BEAM)]:vertex.co.z=0
            remember(obj)
            for axis,z,w,h in [('X',.36,.073,.067),('Y',.22,.063,.063)]:
                centre=Vector((sx*(.862 if axis=='X' else .877),sy*(.332 if axis=='X' else .345),z));direction=Vector((1,0,0) if axis=='X' else(0,1,0))
                cutter=beam(name+'_'+axis+'_mortise',centre-direction*.17,centre+direction*.17,w,h,mats['timber'],0)
                cname=cutter.name;remember(cutter);cut_socket(obj,cutter);joints.append({'receiver':name,'opening':cname})
            pin(name+'_drawpin',(sx*.862,sy*.332,.36),length=.16,diameter=.019)
    for sy in(-1,1):
        y=sy*.332;name=f'shouldered_long_stretcher_{sy}'
        hold(loft(name,[(-.952,y,.36,.065,.06),(-.79,y,.36,.065,.06),(-.783,y,.36,.106,.115),(.783,y,.36,.106,.115),(.79,y,.36,.065,.06),(.952,y,.36,.065,.06)],mats['timber'],bevel=.0025),name)
        hold(beam('upper_apron_'+str(sy),(-.88,sy*.33,.807),(.88,sy*.33,.807),.075,.12,mats['timber']),f'upper_apron_{sy}')
    for sx in(-1,1):
        x=sx*.877;name=f'shouldered_side_stretcher_{sx}'
        hold(loft(name,[(x,-.428,.22,.056,.056),(x,-.274,.22,.056,.056),(x,-.267,.22,.10,.104),(x,.267,.22,.10,.104),(x,.274,.22,.056,.056),(x,.428,.22,.056,.056)],mats['timber'],bevel=.0025),name)
        hold(beam('top_crossbearer_'+str(sx),(sx*.84,-.45,.853),(sx*.84,.45,.853),.155,.08,mats['timber']),f'top_crossbearer_{sx}')
        for sy in(-1,1):
            outline=[(sx*.841,.59),(sx*.841,.844),(sx*.60,.844),(sx*.64,.80),(sx*.715,.738),(sx*.77,.67)]
            if sx<0:outline.reverse()
            hold(plate(f'shaped_knee_{sx}_{sy}',outline,.063,mats['timber'],'Y',sy*.311,.002))
    for i,y in enumerate((-.405,-.2025,0,.2025,.405)):
        hold(loft(f'worn_worktop_board_{i}',[(-1.025,y,.904,.197,.070),(-.99,y,.906,.199,.071),(-.48,y+.0009,.906,.198,.072),(.12,y-.0008,.905,.199,.070),(.69,y+.0005,.906,.197,.071),(1.025,y,.904,.197,.070)],mats['timber'],bevel=.002),'worktop')
    for sx in(-1,1):
        hold(beam('breadboard_end_'+str(sx),(sx*1.085,-.51,.905),(sx*1.085,.51,.905),.122,.075,mats['timber'],.0025),'worktop')
        for y in(-.36,0,.36):pin(f'breadboard_pin_{sx}_{y}',(sx*1.085,y,.908),(0,0,1),.071,.017)
    # Rear posts are fitted through the top into strapped brackets on the rear frame.
    for x in(-.96,.96):
        name='rack_rear_post_'+str(x)
        board=next(obj for obj in parts if obj.name=='worn_worktop_board_4')
        cutter=loft(name+'_worktop_socket',[(x,.38,.82,.089,.081),(x,.38,1.04,.089,.081)],mats['timber'],bevel=0)
        cname=cutter.name;remember(cutter);cut_socket(board,cutter);joints.append({'receiver':board.name,'opening':cname})
        hold(loft(name,[(x,.379,.72,.072,.081),(x,.381,.93,.075,.083),(x,.386,1.30,.068,.075),(x,.386,1.805,.064,.07)],mats['timber'],guide=(1,0,0),bevel=.0025),name)
        outline=[(x-.059,.756),(x+.058,.756),(x+.055,1.016),(x+.035,1.034),(x-.037,1.034),(x-.060,1.008)]
        hold(plate('rack_clamp_'+str(x),outline,.009,mats['iron'],'Y',.425,.001),'rack_clamp_'+str(x))
        for z in(.79,.992):pin(f'rack_clamp_bolt_{x}_{z}',(x,.428,z),(0,1,0),.02,.020,'iron')
    hold(loft('drying_crossbar',[(-1.046,.386,1.772,.083,.094),(-.99,.386,1.795,.086,.10),(-.3,.386,1.799,.083,.102),(.5,.386,1.796,.084,.10),(1.046,.386,1.776,.083,.092)],mats['timber'],bevel=.003),'rack_top')
    for x in(-.96,.96):pin('crossbar_peg_'+str(x),(x,.386,1.777),(0,1,0),.101,.018)
    hold(beam('fitted_vial_shelf',(-.02,.314,1.133),(.90,.314,1.133),.27,.061,mats['timber']),'vial_shelf')
    for x in(.02,.84):
        hold(plate('shelf_scroll_bracket_'+str(x),[(.23,.939),(.407,.939),(.41,1.14),(.19,1.14),(.19,1.10),(.255,1.067),(.273,1.006)],.037,mats['timber'],'X',x,.002))
    # Stoppered vessels are closed shaped profiles, held by two separate leather rails.
    for i,x in enumerate((.08,.27,.455,.65,.835)):
        h=(.185,.216,.171,.205,.177)[i];r=(.057,.058,.054,.060,.05)[i];z=1.165
        profile=[(0,r*.64),(.008,r*.88),(.025,r),(h*.55,r*.99),(h*.73,r*.87),(h*.81,r*.52),(h*.88,r*.40),(h*.92,r*.53),(h,r*.53),(h+.006,r*.44)]
        hold(turned(f'handblown_stoppered_vial_{i}',(x,.309,z),profile,mats['amber'],lod))
        hold(turned(f'cork_stopper_{i}',(x,.309,z+h),[(0,r*.37),(.019,r*.40),(.025,r*.48),(.035,r*.44)],mats['endgrain'],lod))
        if lod<2:
            hold(turned(f'waxed_neck_binding_{i}',(x,.309,z+h*.895),[(0,r*.54),(.013,r*.555),(.017,r*.50)],mats['linen'],lod))
        # Each vial has an open fitted cradle, not an impossible solid socket.
        for dx in(-r-.008,r+.008):hold(beam(f'vial_cradle_cheek_{i}_{dx}',(x+dx,.222,z+.017),(x+dx,.396,z+.017),.015,.034,mats['timber'],.001))
    for z in(1.195,1.27):
        points=[(-.01,.214,z),(.05,.215,z+.003),(.45,.216,z-.004),(.9,.217,z),(.92,.24,z)]
        hold(loft('vial_retaining_leather_'+str(z),[(*p,.024,.006) for p in points],mats['leather'],bevel=.0007))
        for x in(.012,.89):pin(f'leather_rail_rivet_{z}_{x}',(x,.208,z),(0,1,0),.016,.012,'iron')
    # Hollow mortared stoneware bowl and its resting shaped pestle.
    bowlx,bowly=-.65,-.17
    hold(turned('worked_stoneware_mortar',(bowlx,bowly,.941),[(0,.09),(.012,.12),(.038,.145),(.15,.169),(.174,.178),(.184,.174),(.184,.151),(.155,.143),(.057,.112),(.032,.07)],mats['stoneware'],lod))
    pestle=hold(loft('fitted_resting_pestle',[(bowlx-.065,bowly,.996,.073,.069),(bowlx-.045,bowly,1.033,.079,.073),(bowlx+.012,bowly,1.135,.035,.034),(bowlx+.059,bowly,1.238,.046,.04)],mats['stoneware'],ROUND[::(1 if lod==0 else 2)],True,0))
    # Trays are sewn shallow polygon basins: visible bottom, sloping inner wall and lip.
    def tray(name,cx,cy,w,d):
        outline=[(-.46,-.5),(.43,-.5),(.5,-.34),(.5,.34),(.43,.5),(-.44,.5),(-.5,.34),(-.5,-.35)]
        loops=[(w*.94,d*.94,.943),(w,d,.99),(w*.93,d*.87,.995),(w*.82,d*.72,.955)]
        vertices=[(cx+a*width,cy+b*depth,z) for width,depth,z in loops for a,b in outline];n=len(outline);faces=[];uv=[]
        for row in range(3):
            for j in range(n):
                k=(j+1)%n;faces.append([row*n+j,row*n+k,(row+1)*n+k,(row+1)*n+j]);uv.append([(j/n,0),((j+1)/n,0),((j+1)/n,1),(j/n,1)])
        faces.extend([list(reversed(range(n))),list(range(3*n,4*n))]);uv.extend([list(reversed(outline)),outline])
        from mesh_authoring import explicit
        return hold(explicit(name,vertices,faces,mats['timber'],uv,False,.001))
    tray('fitted_preparation_tray',.34,-.205,.69,.37)
    tray('small_sorted_seed_tray',-.22,.185,.34,.245)
    for i in range((12,8,5)[lod]):
        x=.11+(i%4)*.12;y=-.28+(i//4)*.065
        hold(leaf('prepared_leaf_'+str(i),(x,y,.958),(x+.10,y+.015,.962),.041,mats['sage'],lod,i))
    # Three tied bundles, individually curved stems and thick folded leaves.
    for bundle,cx in enumerate((-.76,-.48,-.20)):
        top=1.733;cy=.317
        # Peg curves toward the player; binding closes around the actual crossbar.
        pin('drying_peg_'+str(bundle),(cx,.32,1.759),(0,1,0),.18,.02)
        ring=[(cx+.013*math.cos(t*math.tau/16),cy-.017,top+.035+.029*math.sin(t*math.tau/16)) for t in range(17)]
        hold(strand('hanging_loop_'+str(bundle),ring,.005,mats['linen'],lod))
        stems=(7,5,4)[lod]
        for i in range(stems):
            angle=i*math.tau/stems+bundle*.7;length=.28+.048*math.sin(i*2.3+bundle);spread=.07+.015*math.sin(i)
            tip=(cx+math.cos(angle)*spread,cy+math.sin(angle)*spread,top-length)
            middle=(cx+math.cos(angle)*spread*.42,cy+math.sin(angle)*spread*.42,top-length*.56)
            # Individual cut stem ends occupy separate positions inside the binding.
            start=(cx+.008*math.cos(angle),cy+.008*math.sin(angle),top+.001*math.sin(i*.9))
            hold(strand(f'herb_stem_{bundle}_{i}',[start,middle,tip],.004,mats['dried'],lod))
            for j in range((5,4,3)[lod]):
                t=.31+j*.135;base=Vector((cx,cy,top)).lerp(Vector(tip),t);heading=angle+(j%2)*math.pi+.22*j
                end=base+Vector((math.cos(heading)*(.065+.012*j),math.sin(heading)*(.065+.012*j),-.073))
                hold(leaf(f'curled_drying_leaf_{bundle}_{i}_{j}',base,end,.039+.005*(j%2),mats['sage' if bundle!=1 else 'dried'],lod,i+j))
        for turn in range(3 if lod<2 else 1):
            route=[(cx+.019*math.cos(t*math.tau/20),cy+.019*math.sin(t*math.tau/20),top-.026-turn*.006) for t in range(21)]
            hold(strand(f'bundle_binding_{bundle}_{turn}',route,.005,mats['linen'],lod))
    # Incised dressing cuts in the actual worktop; kept sparse around the preparation front.
    if lod<2:
        for i in range(9 if lod==0 else 4):
            x=-.3+i*.065;y=-.38+(i%3)*.018
            hold(plate('worktop_tool_score_'+str(i),[(x,y),(x+.07,y+.003),(x+.071,y+.005),(x+.016,y+.003)],.0007,mats['endgrain'],centre=.942,bevel=0))
    for obj in parts:remember(obj)
    source=ROOT/'masters'/f'{KEY}_lod{lod}.source.blend'
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    finish(parts,lod);result=audit(parts)
    save(ROOT/'review'/f'{KEY}_lod{lod}_source-audit.json',result)
    if result['boundary'] or result['multi'] or result['loose']:raise RuntimeError('Source topology failed')
    # The front corridor is a reservation, never invisible collision geometry.
    collision=[];measurements=[]
    for name,objects in mass.items():
        b=bounds(objects);lo=b['minimum'];hi=b['maximum']
        collision.append({'x':(lo[0]+hi[0])/2,'z':-(lo[1]+hi[1])/2,'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'minY':max(0,lo[2]),'maxY':hi[2]})
        measurements.append({'name':name,'parts':[o.name for o in objects],'boundsZUp':b})
    if lod==0:
        b=bounds(parts);lo=b['minimum'];hi=b['maximum']
        contract={'schemaVersion':1,'units':'metres','upAxis':'+Y','frontAxis':'+Z','runtimeReady':False,'assets':{KEY:{'label':'Field Apothecary Worktable','group':'Universal Town Workshops','kind':'field_apothecary','model':KEY+'_lod0.glb','defaultScale':{'x':1,'y':1,'z':1},'colliderSpace':'model','boundsYUp':{'minimum':[lo[0],lo[2],-hi[1]],'maximum':[hi[0],hi[2],-lo[1]]},'footprint':{'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'chainAxis':'x'},'colliders':collision,'collisionMeasurements':measurements,'walkableSurfaces':[],'cameraSolid':True,'workingFront':{'minimum':[-1.1,0,.57],'maximum':[1.1,2,1.67]},'approachSource':{'minimum':[-1.1,-1.67,0],'maximum':[1.1,-.57,2]},'standingPoint':{'x':0,'y':0,'z':1.12},'placementDatum':'Flat finished feet at Y0; front +Z. Reserve workingFront against other props.','sourceMasterSha256':sha(source)}}}
        save(ROOT/'builder-contract.json',contract)
    finished=ROOT/'masters'/f'{KEY}_lod{lod}.blend'
    # Keep editable per-part masters; batch only the literal export by material.
    batches={}
    for obj in parts:batches.setdefault(obj.data.materials[0].name,[]).append(obj)
    exports=[]
    for name,objects in batches.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=objects[0];obj.name=KEY+'.'+name.split('.')[-1]
        obj.data.calc_tangents(uvmap='authored_uv');invalid={loop.index for loop in obj.data.loops if loop.tangent.length<.99};obj.data.free_tangents()
        # Boolean mortise interior facets need their own physical planar UV basis.
        # Assign only collapsed corner charts; preserve every authored vertex/normal.
        for face in obj.data.polygons:
            if not any(i in invalid for i in face.loop_indices):continue
            points=[obj.data.vertices[i].co for i in face.vertices];a,b=max(((0,1),(1,2),(2,0)),key=lambda pair:(points[pair[1]]-points[pair[0]]).length)
            edge=points[b]-points[a];side=edge.normalized();up=face.normal.cross(side).normalized()
            coordinates=[((point-points[a]).dot(side)/edge.length,(point-points[a]).dot(up)/edge.length) for point in points]
            altitude=max(v for u,v in coordinates)-min(v for u,v in coordinates)
            for loop,point in zip(face.loop_indices,points):
                relative=point-points[a];obj.data.uv_layers[0].data[loop].uv=(relative.dot(side)/edge.length,relative.dot(up)/edge.length*max(1,.008/max(altitude,1e-12)))
        obj.data.update()
        obj.data.calc_tangents(uvmap='authored_uv');invalid={loop.index for loop in obj.data.loops if loop.tangent.length<.99}
        if invalid:
            save(ROOT/'review'/f'invalid-tangents-lod{lod}.json',{'material':name,'faces':[{'index':f.index,'area':f.area,'normal':list(f.normal),'points':[list(obj.data.vertices[i].co) for i in f.vertices],'uv':[list(obj.data.uv_layers[0].data[i].uv) for i in f.loop_indices],'normals':[list(obj.data.corner_normals[i].vector) for i in f.loop_indices]} for f in obj.data.polygons if any(i in invalid for i in f.loop_indices)]})
            raise RuntimeError(f'Invalid authored UV tangents: {name} {len(invalid)}')
        obj.data.free_tangents()
        exports.append(obj)
    batch_audit=audit(exports)
    if any(batch_audit[field] for field in('boundary','multi','loose')):raise RuntimeError('Batched export topology failed')
    bpy.ops.wm.save_as_mainfile(filepath=str(finished))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:obj.select_set(True)
    bpy.context.view_layer.objects.active=exports[0]
    target=ROOT/'runtime'/f'{KEY}_lod{lod}.glb';bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
    record={'key':KEY,'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':result['triangles'],'joints':joints,'parts':len(parts),'materials':len(exports),'sourceMaster':str(source.relative_to(ROOT)).replace('\\','/'),'sourceMasterSha256':sha(source),'master':str(finished.relative_to(ROOT)).replace('\\','/'),'masterSha256':sha(finished),'boundsZUp':result['boundsZUp'],'audit':result,'sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p)} for p in sorted((ROOT/'tools').glob('*.py'))]+[{'path':'textures/sources.json','sha256':sha(ROOT/'textures/sources.json')}]}
    save(ROOT/'review'/f'{KEY}_lod{lod}_build.json',record);print('APOTHECARY_EXPORTED',lod,result['triangles'],len(parts),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for directory in('masters','runtime','review'):(ROOT/directory).mkdir(exist_ok=True)
    for lod in args.lods.split(','):build(int(lod))
