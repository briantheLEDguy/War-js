"""Original mortised campaign desk, fitted parchment and physically supported tools."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesh_authoring import explicit,plate,loft,strand,turned,cut_socket,finish,BEAM
from export_tangents import repair_export_tangents
KEY='frontier_field_command_table';TOP=.872

def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def save(file,value):
    temp=file.with_suffix(file.suffix+'.tmp');temp.write_text(json.dumps(value,separators=(',',':'))+'\n');temp.replace(file)
def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {'minimum':[min(v[i] for v in points) for i in range(3)],'maximum':[max(v[i] for v in points) for i in range(3)]}
def audit(objects):
    records=[]
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        records.append({'part':obj.name,'boundary':sum(e.is_boundary for e in bm.edges),'multi':sum(len(e.link_faces)>2 for e in bm.edges),'loose':sum(not e.link_faces for e in bm.edges),'triangles':sum(len(f.verts)-2 for f in bm.faces)})
        bm.free()
    return {**{field:sum(r[field] for r in records) for field in('boundary','multi','loose','triangles')},'meshes':records,'boundsZUp':bounds(objects)}

def materials(lod):
    result={}
    for name in('oak','iron','brass','leather','ceramic','parchment'):
        mat=bpy.data.materials.new('command_table.'+name);mat.use_nodes=True;mat.use_backface_culling=True
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
        for channel in('basecolor','normal','orm'):
            im=bpy.data.images.load(str(ROOT/'textures'/f'{name}_lod{lod}_{channel}.png'));im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
            node=nodes.new('ShaderNodeTexImage');node.image=im;links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
        links.new(maps['basecolor'].outputs['Color'],shader.inputs['Base Color'])
        normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';normal.inputs['Strength'].default_value=.35 if name in('brass','ceramic','parchment') else .6
        links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        separate=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],separate.inputs[0])
        links.new(separate.outputs['Green'],shader.inputs['Roughness']);links.new(separate.outputs['Blue'],shader.inputs['Metallic']);result[name]=mat
    return result

def map_point(u,v):
    # The broad centre lies on the planed tabletop; small edge curls and two soft
    # storage creases are bounded above it. Front-facing UV makes labels readable.
    x=-.10+(u-.5)*1.18+.0015*math.sin(v*31)*abs(2*u-1)**8
    y=-.02+(v-.5)*.66+.001*math.sin(u*37)*abs(2*v-1)**8
    edge=max(abs(2*u-1),abs(2*v-1))
    curl=.007*max(0,(edge-.83)/.17)**2*(.45+.55*math.sin(u*8+v*11)**2)
    fold=.0018*math.exp(-((u-.48)/.018)**2)+.0013*math.exp(-((v-.57)/.022)**2)
    return Vector((x,y,TOP+.00015+curl+fold))

def build(lod):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
    bpy.context.preferences.filepaths.save_version=0
    mats=materials(lod);parts=[];joints=[];ground=[]
    original=bpy.data.collections.new('Editable_original_construction');bpy.context.scene.collection.children.link(original)
    def hold(obj):parts.append(obj);return obj
    def retain(obj):
        copy=obj.copy();copy.data=obj.data.copy();copy.name='cage_'+obj.name;original.objects.link(copy);copy.hide_render=True;copy.hide_set(True)
    def socket(receiver,cutter):retain(cutter);cut_socket(receiver,cutter)
    def fit(receiver,member,label,clearance=.0003):
        cutter=member.copy();cutter.data=member.data.copy();bpy.context.scene.collection.objects.link(cutter);cutter.name=label
        # Expand around this piece's own measured centre, not the world origin.
        b=bounds([cutter]);c=Vector([(b['minimum'][i]+b['maximum'][i])/2 for i in range(3)])
        for vertex in cutter.data.vertices:
            delta=vertex.co-c
            for i in range(3):vertex.co[i]+=clearance*(1 if delta[i]>0 else -1)
        socket(receiver,cutter)
    def contact(a,b,kind='fitted_joint',tolerance=.002):joints.append({'part':a.name,'support':b.name,'kind':kind,'toleranceM':tolerance})
    def pin(name,centre,axis,length,diameter,material='oak'):
        a=Vector(centre)-Vector(axis)*length/2;b=Vector(centre)+Vector(axis)*length/2
        return hold(strand(name,[a,a.lerp(b,.08),a.lerp(b,.92),b],diameter,mats[material],lod))
    feet=[];posts=[];bearers=[];braces=[]
    for sx in(-1,1):
        foot=hold(plate(f'shaped_ground_skid_{sx}',[(-.435,0),(-.26,0),(-.21,.027),(.21,.027),(.26,0),(.435,0),(.435,.040),(.37,.096),(.24,.118),(-.24,.118),(-.37,.096),(-.435,.040)],.166,mats['oak'],'X',sx*.64,.003))
        post=hold(plate(f'trestle_upright_{sx}',[(sx*.64-.067,.062),(sx*.64+.067,.062),(sx*.64+.060,.63),(sx*.64+.081,.727),(sx*.64+.070,.759),(sx*.64-.070,.759),(sx*.64-.081,.727),(sx*.64-.060,.63)],.156,mats['oak'],'Y',0,.002))
        fit(foot,post,f'foot_mortise_{sx}');contact(post,foot)
        bearer=hold(loft(f'mortised_table_bearer_{sx}',[(sx*.64,y,.758,w,h) for y,w,h in[(-.462,.11,.06),(-.42,.17,.112),(-.34,.17,.112),(.34,.17,.112),(.42,.17,.112),(.462,.11,.06)]],mats['oak'],bevel=.002))
        fit(bearer,post,f'bearer_mortise_{sx}');contact(bearer,post)
        peg=pin(f'foot_drawbore_peg_{sx}',(sx*.64,0,.093),(0,1,0),.178,.017)
        fit(foot,peg,f'foot_peg_bore_{sx}',.00015);fit(post,peg,f'post_peg_bore_{sx}',.00015);contact(peg,foot);contact(peg,post)
        feet.append(foot);posts.append(post);bearers.append(bearer)
    stretcher=hold(loft('through_tenon_stretcher',[(x,0,.287,w,h) for x,w,h in[(-.785,.064,.08),(-.724,.074,.087),(-.699,.09,.124),(-.53,.095,.125),(.53,.095,.125),(.699,.09,.124),(.724,.074,.087),(.785,.064,.08)]],mats['oak'],bevel=.002))
    for sx,post in zip((-1,1),posts):
        fit(post,stretcher,f'stretcher_mortise_{sx}');contact(stretcher,post)
        peg=pin(f'stretcher_drawbore_peg_{sx}',(sx*.64,0,.287),(0,1,0),.174,.016)
        fit(post,peg,f'stretcher_post_peg_bore_{sx}',.00015);fit(stretcher,peg,f'stretcher_peg_bore_{sx}',.00015);contact(peg,post);contact(peg,stretcher)
        # Diagonal knees terminate inside receiving timber instead of merely
        # touching a bounding box. Their angled mortises are retained as cages.
        brace=hold(loft(f'angled_knee_brace_{sx}',[(sx*.637,0,.432,.071,.083),(sx*.59,0,.487,.071,.083),(sx*.44,0,.66,.066,.078),(sx*.33,0,.801,.065,.076)],mats['oak'],bevel=.002))
        fit(post,brace,f'knee_post_mortise_{sx}');contact(brace,post);braces.append(brace)
    # Five structural planks with softly relieved edge corners and real seams.
    boards=[]
    for row in range(5):
        a=-.5+row*.2+.0008;b=a+.1984
        outline=[(-.812,a+.003),(-.808,a),(.808,a),(.812,a+.003),(.812,b-.003),(.808,b),(-.808,b),(-.812,b-.003)]
        board=hold(plate(f'planed_table_plank_{row}',outline,.058,mats['oak'],'Z',TOP-.029,.001))
        for loop in board.data.uv_layers[0].data:
            u,v=loop.uv;loop.uv=(v*1.3+row*.113,u*.55+row*.21)
        boards.append(board)
        for bearer in bearers:contact(board,bearer,'load_bearing')
    for brace in braces:
        fit(boards[2],brace,brace.name+'_top_mortise');contact(brace,boards[2])
    ends=[]
    for sx in(-1,1):
        a,b=sorted((sx*.813,sx*.9))
        cap=hold(plate(f'breadboard_end_{sx}',[(a,-.497),(a+.003,-.5),(b-.003,-.5),(b,-.497),(b,.497),(b-.003,.5),(a+.003,.5),(a,.497)],.058,mats['oak'],'Z',TOP-.029,.001))
        ends.append(cap)
        for row in(0,2,4):
            y=-.4+row*.2
            tenon=hold(loft(f'breadboard_loose_tenon_{sx}_{row}',[(sx*.786,y,TOP-.029,.108,.018),(sx*.84,y,TOP-.029,.108,.018)],mats['oak'],bevel=.0004))
            fit(cap,tenon,f'endboard_tenon_socket_{sx}_{row}',.00015);fit(boards[row],tenon,f'plank_tenon_socket_{sx}_{row}',.00015);contact(tenon,cap);contact(tenon,boards[row])
            peg=pin(f'endboard_wood_pin_{sx}_{row}',(sx*.832,y,TOP-.011),(0,0,1),.024,.009)
            fit(cap,peg,f'endboard_pin_bore_{sx}_{row}',.0001);contact(peg,cap)
    # Closed top and underside of the thin parchment share an explicit perimeter.
    nx,ny=((48,28),(30,18),(18,10))[lod];vertices=[];faces=[];uv=[]
    for layer in(0,1):
        for j in range(ny+1):
            for i in range(nx+1):
                p=map_point(i/nx,j/ny);p.z+=layer*.0014;vertices.append(list(p))
    half=(nx+1)*(ny+1)
    for layer in range(2):
        for j in range(ny):
            for i in range(nx):
                ids=[layer*half+j*(nx+1)+i,layer*half+j*(nx+1)+i+1,layer*half+(j+1)*(nx+1)+i+1,layer*half+(j+1)*(nx+1)+i]
                coords=[(i/nx,j/ny),((i+1)/nx,j/ny),((i+1)/nx,(j+1)/ny),(i/nx,(j+1)/ny)]
                faces.append(ids if layer else list(reversed(ids)));uv.append(coords if layer else list(reversed(coords)))
    rim=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+list(range(ny*(nx+1)+nx-1,ny*(nx+1)-1,-1))+[j*(nx+1) for j in range(ny-1,0,-1)]
    for i,p in enumerate(rim):
        q=rim[(i+1)%len(rim)];faces.append([p,q,q+half,p+half]);uv.append([(.005,.01),(.006,.01),(.006,.012),(.005,.012)])
    paper=hold(explicit('fitted_thick_campaign_parchment',vertices,faces,mats['parchment'],uv,True,0))
    for board in boards[1:4]:contact(paper,board,'supported_sheet',.001)
    # Flattened forged map weights settle on the actual authored paper surface.
    for i,(u,v) in enumerate(((.065,.085),(.94,.09),(.07,.91),(.935,.92))):
        c=map_point(u,v);z=max(map_point(u+math.cos(j*math.tau/80)*.03/1.18,v+math.sin(j*math.tau/80)*.03/.66).z for j in range(80))+.0014
        weight=hold(turned(f'forged_map_weight_{i}',(c.x,c.y,z),[(0,.024),(.002,.029),(.006,.031),(.016,.026),(.023,.017),(.025,.012)],mats['iron'],lod));contact(weight,paper,'equipment_rest',.0015)
        boss=hold(turned(f'weight_brass_crest_{i}',(c.x,c.y,z+.0235),[(0,.011),(.002,.012),(.004,.008)],mats['brass'],lod));contact(boss,weight,'fixed_inlay')
    # Glazed ceramic ink vessel with a genuine deep mouth, wall thickness and
    # recessed inner bowl. Closing the bottom does not fill the open neck.
    ink=hold(turned('glazed_ink_vessel',(.712,.278,TOP),[(0,.032),(.003,.040),(.008,.045),(.025,.049),(.061,.045),(.077,.034),(.086,.028),(.097,.029),(.104,.027),(.104,.019),(.094,.019),(.084,.024),(.061,.033),(.025,.036),(.011,.030)],mats['ceramic'],lod));contact(ink,boards[3],'equipment_rest',.001)
    # An iron inset ink well sits inside the ceramic bowl, below the visible lip.
    inkpool=hold(turned('inset_ink_well',(.712,.278,TOP+.022),[(0,.035),(.001,.035),(.002,.034)],mats['iron'],lod));contact(inkpool,ink,'vessel_insert')
    # Stopper placed flat alongside, with a fitted brass ferrule and low knob.
    stopper=hold(turned('resting_ink_stopper',(.767,.107,TOP),[(0,.018),(.007,.019),(.012,.016),(.020,.014),(.030,.014)],mats['oak'],lod));contact(stopper,boards[3],'equipment_rest',.001)
    stoppercap=hold(turned('stopper_brass_cap',(.767,.107,TOP+.028),[(0,.014),(.004,.017),(.006,.016),(.011,.007)],mats['brass'],lod));contact(stoppercap,stopper,'fixed_ferrule')
    # Closed dispatch wallet has a shaped case, supported flap and real clasp.
    outline=[(.529,-.385),(.548,-.398),(.815,-.383),(.837,-.36),(.822,-.133),(.805,-.114),(.544,-.125),(.526,-.145)]
    wallet=hold(plate('leather_dispatch_wallet',outline,.026,mats['leather'],'Z',TOP+.013,.004));contact(wallet,boards[0],'equipment_rest',.001);contact(wallet,boards[1],'equipment_rest',.001)
    flap=hold(plate('folded_wallet_flap',[(.535,-.141),(.814,-.132),(.825,-.156),(.798,-.282),(.696,-.321),(.562,-.293),(.532,-.166)],.0035,mats['leather'],'Z',TOP+.027,.001));contact(flap,wallet,'sewn_flap')
    clasp=hold(plate('wallet_clasp_plate',[(.671,-.31),(.707,-.31),(.711,-.298),(.706,-.274),(.674,-.274),(.668,-.299)],.003,mats['brass'],'Z',TOP+.030,.0008));contact(clasp,flap,'fixed_clasp')
    stud=hold(turned('wallet_clasp_stud',(.69,-.293,TOP+.031),[(0,.006),(.003,.009),(.006,.006)],mats['brass'],lod));contact(stud,clasp,'fixed_rivet')
    # Leather edge stitches are explicit closed filaments, reduced by spacing at
    # distance rather than retaining invisible sub-pixel stitch geometry.
    if lod<2:
        for i in range(26 if lod==0 else 13):
            t=i/(25 if lod==0 else 12);x=.55+t*.253;y=-.373+t*.014
            stitch=hold(strand(f'wallet_edge_stitch_{i}',[(x-.0025,y,TOP+.026),(x,y-.001,TOP+.028),(x+.0025,y,TOP+.026)],.0012,mats['oak'],lod));contact(stitch,wallet,'seam',.001)
    # A timber pen rests on the wallet and paper: nib and shaft are continuous,
    # with a low desk rest beneath its far end rather than unsupported floating.
    a=Vector((.566,-.045,TOP+.012));b=Vector((.819,-.022,TOP+.012))
    pen=hold(loft('carved_writing_pen',[(*(a.lerp(b,t)),w,w) for t,w in[(0,.009),(.08,.013),(.25,.013),(.8,.011),(1,.005)]],mats['oak'],section=[(math.cos(j*math.tau/(16,12,8)[lod])*.5,math.sin(j*math.tau/(16,12,8)[lod])*.5) for j in range((16,12,8)[lod])],smooth=True,bevel=0))
    rest=hold(plate('pen_rest',[(.745,-.056),(.77,-.054),(.772,.0),(.747,-.002)],.006,mats['leather'],'Z',TOP+.003,.001));contact(rest,boards[2],'equipment_rest',.001);contact(pen,rest,'supported_tool',.002)
    nib=hold(loft('brass_split_pen_nib',[(.543,-.047,TOP+.0008,.0015,.0015),(.553,-.046,TOP+.006,.008,.003),(.568,-.045,TOP+.012,.009,.006)],mats['brass'],bevel=.0003));contact(nib,pen,'fixed_ferrule');contact(nib,boards[2],'equipment_rest',.001)
    # Open brass drafting dividers: flat forged shanks, supported steel tips and
    # a captive hinge with a radial washer, entirely atop the parchment.
    hinge=Vector((.28,.185,TOP+.010))
    legs=[]
    for side in(-1,1):
        tip=Vector((.28+side*.078,-.022,TOP+.003))
        leg=hold(loft(f'divider_forged_leg_{side}',[(*tip,.006,.004),(*tip.lerp(hinge,.12),.012,.005),(*tip.lerp(hinge,.65),.016,.006),(*hinge,.026,.006)],mats['brass'],bevel=.0005));contact(leg,paper,'equipment_rest',.002);legs.append(leg)
    hub=hold(turned('divider_hinge_pin',(hinge.x,hinge.y,hinge.z-.005),[(0,.009),(.001,.014),(.010,.014),(.012,.010)],mats['iron'],lod))
    for leg in legs:contact(hub,leg,'captive_hinge')
    washer=hold(turned('divider_hinge_rosette',(hinge.x,hinge.y,hinge.z+.006),[(0,.009),(.002,.012),(.004,.009)],mats['brass'],lod));contact(washer,hub,'fixed_washer')
    # Front and rear straps wrap the bearer/post seat; rivets sit inside the
    # strap face and actual timber. They are decorative reinforcement, not
    # substitutes for the receiving wooden joint.
    for sx,post in zip((-1,1),posts):
        for sy in(-1,1):
            strap=hold(plate(f'bearer_iron_cheek_{sx}_{sy}',[(sx*.64-.032,.657),(sx*.64+.032,.657),(sx*.64+.044,.765),(sx*.64-.044,.765)],.004,mats['iron'],'Y',sy*.080,.0008));contact(strap,post,'fixed_reinforcement')
            for z in(.677,.741):
                rivet=pin(f'cheek_rivet_{sx}_{sy}_{z}',(sx*.64,sy*.082,z),(0,1,0),.012,.010,'iron');contact(rivet,strap,'fixed_rivet')
    for obj in parts:
        if obj.name.startswith(('shaped_ground_skid','breadboard_end')):
            for loop in obj.data.uv_layers[0].data:loop.uv=(loop.uv.y,loop.uv.x)
        retain(obj)
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    source=ROOT/'masters'/f'{KEY}_lod{lod}.source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source))
    finish(parts,lod)
    # Continuous grain charts are assigned after receiving cuts, so Boolean
    # interior charts cannot leak rectangular patches onto a planed top face.
    for obj in parts:
        if obj.data.materials[0] != mats['oak']:continue
        name=obj.name
        grain=Vector((0,0,1)) if 'upright' in name else Vector((0,1,0)) if any(s in name for s in('skid','bearer','breadboard_end')) else Vector((1,0,0))
        offset=(sum(map(ord,name))%113)/113
        for face in obj.data.polygons:
            tangent=grain-face.normal*grain.dot(face.normal)
            if tangent.length<.01:
                guide=Vector((0,1,0)) if abs(face.normal.y)<.85 else Vector((1,0,0));tangent=guide-face.normal*guide.dot(face.normal)
            tangent.normalize();cross=face.normal.cross(tangent).normalized()
            for li,vi in zip(face.loop_indices,face.vertices):
                p=obj.data.vertices[vi].co;obj.data.uv_layers[0].data[li].uv=(p.dot(cross)*1.25+offset,p.dot(tangent)*.6+offset)
    result=audit(parts);save(ROOT/'review'/f'{KEY}_lod{lod}_source-audit.json',result)
    if any(result[k] for k in('boundary','multi','loose')):raise RuntimeError('Construction topology failed')
    # Per-part final surface witnesses survive batching as a separate receipt,
    # permitting exact imported support checks without adding runtime draw calls.
    fitted={o.name:{'material':o.data.materials[0].name.split('.')[-1],'vertices':[list(v.co) for v in o.data.vertices],'triangles':[list(p.vertices) for p in o.data.polygons]} for o in parts}
    save(ROOT/'review'/f'{KEY}_lod{lod}_finished-parts.json',fitted)
    if lod==0:
        b=result['boundsZUp'];lo=b['minimum'];hi=b['maximum']
        masses={'tabletop_and_supported_tools':[o for o in parts if o not in feet+posts+bearers+braces+[stretcher] and not o.name.startswith(('foot_','stretcher_drawbore','bearer_iron','cheek_rivet'))],
          'central_through_stretcher':[stretcher]+braces}
        for sx,foot,post,bearer in zip((-1,1),feet,posts,bearers):
            masses[f'ground_skid_{sx}']=[foot];masses[f'trestle_frame_{sx}']=[post,bearer]+[o for o in parts if o.name.startswith((f'bearer_iron_cheek_{sx}_',f'cheek_rivet_{sx}_',f'foot_drawbore_peg_{sx}',f'stretcher_drawbore_peg_{sx}'))]
        measurements=[{'name':name,'parts':[o.name for o in objects],'boundsZUp':bounds(objects)} for name,objects in masses.items()]
        colliders=[]
        for group in measurements:
            a=group['boundsZUp']['minimum'];b=group['boundsZUp']['maximum'];colliders.append({'x':(a[0]+b[0])/2,'z':-(a[1]+b[1])/2,'width':b[0]-a[0],'depth':b[1]-a[1],'minY':max(0,a[2]),'maxY':b[2]})
        front={'minimum':[-.95,0,.54],'maximum':[.95,2,1.8]}
        save(ROOT/'builder-contract.json',{'schemaVersion':1,'runtimeReady':False,'assets':{KEY:{'label':'Field Command Table','group':'Universal Town Logistics','kind':'field_command_table','model':KEY+'_lod0.glb','defaultScale':{'x':1,'y':1,'z':1},'colliderSpace':'model','sourceMasterSha256':sha(source),'boundsYUp':{'minimum':[lo[0],lo[2],-hi[1]],'maximum':[hi[0],hi[2],-lo[1]]},'footprint':{'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'chainAxis':'x'},'colliders':colliders,'collisionMeasurements':measurements,'walkableSurfaces':[],'cameraSolid':True,'standingPoint':{'x':0,'y':0,'z':1.08},'workingFront':front,'approachSource':{'minimum':[-.95,-1.8,0],'maximum':[.95,-.54,2]},'placementDatum':'Two relieved planed skids at Y0. Face the clear +Z front toward the aisle. Static campaign chart and tools; no interaction or tabletop walking.'}}})
    batches={}
    for obj in parts:batches.setdefault(obj.data.materials[0].name,[]).append(obj)
    exports=[]
    for name,objects in batches.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=objects[0];obj.name=KEY+'.'+name.split('.')[-1]
        obj.data.calc_tangents(uvmap='authored_uv');invalid={loop.index for loop in obj.data.loops if loop.tangent.length<.99 or abs(loop.tangent.dot(obj.data.corner_normals[loop.index].vector))>.001};obj.data.free_tangents()
        for face in obj.data.polygons:
            if not any(i in invalid for i in face.loop_indices):continue
            points=[obj.data.vertices[i].co for i in face.vertices];a,b=max(((0,1),(1,2),(2,0)),key=lambda pair:(points[pair[1]]-points[pair[0]]).length)
            edge=points[b]-points[a];side=edge.normalized();up=face.normal.cross(side).normalized();heights=[(point-points[a]).dot(up)/edge.length for point in points];scale=max(1,.008/max(max(heights)-min(heights),1e-12))
            for loop,point in zip(face.loop_indices,points):obj.data.uv_layers[0].data[loop].uv=((point-points[a]).dot(side)/edge.length,(point-points[a]).dot(up)/edge.length*scale)
        obj.data.update();obj.data.calc_tangents(uvmap='authored_uv')
        if any(loop.tangent.length>.01 and abs(loop.tangent.dot(obj.data.corner_normals[loop.index].vector))>.001 for loop in obj.data.loops):raise RuntimeError('Nonorthogonal authored tangent '+name)
        obj.data.free_tangents();exports.append(obj)
    final=ROOT/'masters'/f'{KEY}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(final))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:obj.select_set(True)
    bpy.context.view_layer.objects.active=exports[0];target=ROOT/'runtime'/f'{KEY}_lod{lod}.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True)
    tangentRepair=repair_export_tangents(target);save(ROOT/'review'/f'{KEY}_lod{lod}_tangent-repair.json',tangentRepair)
    record={'tangentRepair':tangentRepair,'key':KEY,'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':result['triangles'],'parts':len(parts),'materials':len(exports),'joints':joints,'sourceMaster':str(source.relative_to(ROOT)).replace('\\','/'),'sourceMasterSha256':sha(source),'master':str(final.relative_to(ROOT)).replace('\\','/'),'masterSha256':sha(final),'finishedParts':f'review/{KEY}_lod{lod}_finished-parts.json','finishedPartsSha256':sha(ROOT/'review'/f'{KEY}_lod{lod}_finished-parts.json'),'audit':result,'sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p)} for p in sorted((ROOT/'tools').glob('*.py'))]+[{'path':'textures/sources.json','sha256':sha(ROOT/'textures/sources.json')}]}
    save(ROOT/'review'/f'{KEY}_lod{lod}_build.json',record);print('COMMAND_TABLE_EXPORTED',lod,result['triangles'],len(parts),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for lod in map(int,args.lods.split(',')):build(lod)
