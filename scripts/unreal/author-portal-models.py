"""Author reference-driven portal candidates in Blender; never grants art approval.

All architectural surfaces are lofted/profiled meshes, with a clear central
opening. Outputs remain private draft assets until native collision/art review.
Run with Blender --background --python this_file. Units are metres, front is -Y.
"""
import bpy
import hashlib
import json
import math
import random
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/portal-models'
OUT.mkdir(parents=True, exist_ok=True)
random.seed(290926)
TAU = math.tau


def surface(name, vertices, faces, material, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new('Dressed edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def slab(name,outline,z,height,mat,bevel=.015):
    n=len(outline)
    vertices=[(x,y,zz) for zz in (z,z+height) for x,y in outline]
    faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return surface(name,vertices,faces,mat,bevel)


def material(name, color, metal=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = .42 if metal else .86
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = emission
    else:
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 16
        noise.inputs['Detail'].default_value = 4
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (*[c*.08 for c in color], 1)
        ramp.color_ramp.elements[1].color = (*[min(1,c*.8) for c in color], 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs[0], bsdf.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .23
        bump.inputs['Distance'].default_value = .015 if metal else .045
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs[0], bsdf.inputs['Normal'])
        coords=nodes.new('ShaderNodeTexCoord')
        links.new(coords.outputs['Object'],noise.inputs['Vector'])
    return mat


def loft(name, rings, mat, sides=8, bevel=.012):
    """Rings: centre x,y,z and independent planar radii; no stock mesh primitives."""
    vertices = [(x+rx*math.cos(TAU*i/sides+math.pi/8), y+ry*math.sin(TAU*i/sides+math.pi/8), z)
                for x,y,z,rx,ry in rings for i in range(sides)]
    faces = [tuple(reversed(range(sides)))]
    for j in range(len(rings)-1):
        for i in range(sides):
            a=j*sides+i; b=j*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.append(tuple((len(rings)-1)*sides+i for i in range(sides)))
    return surface(name,vertices,faces,mat,bevel)


def sweep(name, points, radius, mat, sides=6):
    vertices=[]
    for i,p in enumerate(points):
        p=Vector(p)
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize()
        u=tangent.cross(Vector((0,1,0)))
        if u.length < .01:u=tangent.cross(Vector((1,0,0)))
        u.normalize();v=tangent.cross(u).normalized()
        vertices.extend(tuple(p+radius*(u*math.cos(TAU*k/sides)+v*math.sin(TAU*k/sides))) for k in range(sides))
    faces=[tuple(reversed(range(sides)))]
    for j in range(len(points)-1):
        faces.extend((j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k) for k in range(sides))
    faces.append(tuple((len(points)-1)*sides+k for k in range(sides)))
    return surface(name,vertices,faces,mat)


def arch(width, spring, rise, depth):
    # Two circular arcs meet at a genuine pointed Gothic crown.
    r=(width*width+rise*rise)/(2*width)
    angle=math.acos((r-width)/r)
    left=[(-width,depth,.75),(-width,depth,spring)]
    left += [(-width+r-r*math.cos(angle*i/48),depth,spring+r*math.sin(angle*i/48)) for i in range(1,49)]
    return left+ [(-p[0],p[1],p[2]) for p in reversed(left[:-1])]


def crest(x,y,z,scale,evil,metal,glow):
    n=8 if evil else 16
    radius=.36*scale
    ring=[(x+radius*math.cos(TAU*i/64),y,z+radius*math.sin(TAU*i/64)) for i in range(65)]
    sweep('Hollow seal' if evil else 'Solar medallion rim',ring,.055*scale,metal,8)
    if not evil:
        vertices=[(x,y-.04,z)]+[(x+radius*.9*math.cos(TAU*i/64),y,z+radius*.9*math.sin(TAU*i/64)) for i in range(64)]
        surface('Hammered solar face',vertices,[(0,i+1,(i+1)%64+1) for i in range(64)],metal)
    for i in range(n):
        a=TAU*i/n
        length=scale*(1.15 if i%2==0 else .79)
        pts=[]
        for rr,offset,yy in ((radius*.7,-.09,y),(length,0,y-.02),(radius*.7,.09,y),(radius*.75,0,y-.11)):
            pts.append((x+rr*math.cos(a)+offset*math.sin(a),yy,z+rr*math.sin(a)-offset*math.cos(a)))
        surface('Thorn crest ray' if evil else 'Sunburst ray',pts,[(0,1,3),(1,2,3),(2,0,3),(2,1,0)],metal)
    if evil:sweep('Crimson inner seal',[(x+.25*scale*math.cos(TAU*i/48),y-.045,z+.25*scale*math.sin(TAU*i/48)) for i in range(49)],.018*scale,glow)


def tower(x,y,z,h,stone,metal,evil):
    rings=[(x,y,z,.38,.36),(x,y,z+.13,.39,.37),(x,y,z+.22,.29,.28),
           (x,y,z+.42,.24,.23),(x,y,z+h*.60,.20,.19),(x,y,z+h*.64,.29,.27),
           (x,y,z+h*.68,.23,.21),(x,y,z+h,.008,.008)]
    loft('Pinnacle stone core',rings,stone)
    for t,r in ((.04,.4),(.12,.3),(.58,.23),(.64,.30),(.68,.24)):
        zz=z+h*t
        loft('Moulded gold capital' if not evil else 'Forged copper collar',[(x,y,zz,r,r),(x,y,zz+.07,r+.025,r+.025),(x,y,zz+.13,r*.87,r*.87)],metal)
    for a in range(4):
        angle=TAU*a/4+math.pi/4
        dx=.225*math.cos(angle);dy=.225*math.sin(angle)
        sweep('Vertical tracery',[(x+dx,y+dy,z+.4),(x+dx,y+dy,z+h*.60),(x,y,z+h)],.021,metal)
    for sign in (-1,1):
        sweep('Lancet mullion',[(x+sign*.16,y-.24,z+.5),(x+sign*.16,y-.24,z+h*.55),(x,y-.24,z+h*.66)],.022,metal)
    for zz in (.8,1.3,1.8):
        if zz>h*.52:continue
        for sign in (-1,1):
            sweep('Cusp ornament',[(x,y-.252,z+zz+.20),(x+sign*.11,y-.252,z+zz+.10),(x+sign*.15,y-.252,z+zz)],.016,metal)
    # Fine recessed lancets and ogee tracery on all four exposed faces.
    for face in range(4):
        a=face*TAU/4
        for band in range(max(1,int(h*.7))):
            bottom=z+.45+band*.63
            if bottom+.62>z+h*.57:continue
            for sign in (-1,1):
                local=[(sign*.105,-.235,bottom),(sign*.105,-.235,bottom+.30),
                       (sign*.07,-.235,bottom+.45),(0,-.235,bottom+.60)]
                sweep('Fine blind lancet',[(x+xx*math.cos(a)-yy*math.sin(a),y+xx*math.sin(a)+yy*math.cos(a),zz) for xx,yy,zz in local],.012,metal)


def vortex(name, evil):
    """Bake a multi-scale spiral field; UVs and texture survive GLB/FBX import."""
    size=1536
    v,u=np.mgrid[0:size,0:size].astype(np.float32)/(size-1)
    x=(u-.5)*2;y=(v-.43)*2.3
    r=np.sqrt(x*x+y*y)+.007;a=np.arctan2(y,x)
    turbulence=np.zeros_like(r)
    for frequency,weight in ((19,.11),(43,.055),(97,.03),(211,.015)):
        turbulence+=weight*np.sin(x*frequency+np.cos(y*frequency*.78))*np.sin(y*frequency*.9+np.cos(x*frequency*.87))
    phase=a-4.2*np.log(r+.075)+turbulence*.6
    wisps=np.exp(-((np.sin(phase*2+turbulence))/.30)**2)
    wisps+=.28*np.exp(-((np.sin(phase*7+turbulence*3))/.16)**2)
    wisps*=np.maximum(0,.48+turbulence*1.8)/(1+r*.9)
    core=np.exp(-r*r*90)
    rgb=np.zeros((size,size,3),dtype=np.float32)
    tint=(1,.009,.06) if evil else (.04,.15,1)
    for c in range(3):rgb[:,:,c]=.001+wisps*tint[c]+core*(.9,.42,.19)[c]*.7
    rng=np.random.default_rng(291026)
    stars=(rng.random((size,size))>.9993)*rng.random((size,size))*.6
    rgb+=stars[:,:,None]*np.array((1,.28,.35) if evil else (.45,.65,1))
    pixels=np.dstack((rgb,np.ones_like(r))).astype(np.float32)
    image=bpy.data.images.new(name+'_Vortex',width=size,height=size,alpha=True)
    image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(OUT/(name+'_Vortex.png'));image.file_format='PNG';image.save();image.pack()
    mat=material(name+'_Vortex',(.002,.002,.005),0,1)
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Emission Strength'].default_value=12
    texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    mat.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Emission Color'])
    mat.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
    return mat


def skull(x,y,z,scale,bone):
    """Closed cranial loft with carved orbits, a nasal cavity and a separate jaw."""
    rings=[(0,0,.03,.15,.13),(0,-.03,.11,.18,.17),(0,0,.20,.25,.20),
           (0,.015,.32,.26,.22),(0,.02,.43,.21,.19),(0,.02,.49,.10,.10),(0,.02,.51,.004,.004)]
    head=loft('Weathered skull',rings,bone,24,.003)
    for xx,zz,sx,sz in ((-.107,.25,.092,.088),(.107,.25,.092,.088),(0,.145,.043,.07)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,location=(xx,-.17,zz))
        cutter=bpy.context.object;cutter.scale=(sx,.145,sz)
        bpy.context.view_layer.objects.active=head
        boolean=head.modifiers.new('Carved bone cavity','BOOLEAN');boolean.operation='DIFFERENCE';boolean.object=cutter
        bpy.ops.object.modifier_apply(modifier=boolean.name)
        bpy.data.objects.remove(cutter,do_unlink=True)
    head.location=(x,y,z);head.scale=(scale,scale,scale)
    for sign in (-1,1):
        sweep('Jawbone',[(x+sign*.17*scale,y,z+.14*scale),(x+sign*.13*scale,y-.16*scale,z+.015*scale),(x,y-.20*scale,z)],.035*scale,bone,6)
    for tooth in range(6):
        xx=x+(tooth-2.5)*.038*scale
        loft('Worn incisor',[(xx,y-.205*scale,z+.025*scale,.016*scale,.02*scale),(xx,y-.21*scale,z+.083*scale,.02*scale,.02*scale)],bone,6,.002)


def banner(x,y,z,evil,cloth,metal,glow):
    sweep('Banner standard',[(x,y,.12),(x,y,z+.35)],.047,metal)
    sweep('Banner crossbar',[(x-.54,y,z),(x+.54,y,z)],.047,metal)
    vertices=[];nx=14;nz=32
    for j in range(nz+1):
        for i in range(nx+1):
            u=i/nx;v=j/nz
            hem=(.36*abs(2*u-1)+(.16*math.sin(i*3.1) if evil else 0))*v**12
            vertices.append((x+(u-.5)*.85,y+.09*math.sin(u*9+v*4)*v,z-.08-v*2.5+hem))
    faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(nz) for i in range(nx)]
    obj=surface('Torn oxblood banner' if evil else 'Midnight heraldic banner',vertices,faces,cloth)
    solid=obj.modifiers.new('Woven thickness','SOLIDIFY');solid.thickness=.007
    for side in (0,nx):sweep('Banner embroidered border',[vertices[j*(nx+1)+side] for j in range(nz+1)],.012,metal)
    crest(x,y-.12,z-1.13,.25,evil,metal,glow)


def build(evil):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    name='Riftbound' if evil else 'Aegis'
    stone=material(name+'_Basalt',(.046,.042,.040) if evil else (.035,.057,.085))
    metal=material(name+'_Metal',(.27,.105,.040) if evil else (.48,.255,.065),.92)
    cloth=material(name+'_Cloth',(.12,.009,.016) if evil else (.009,.025,.08))
    glow=material(name+'_Rune',(.85,.008,.028) if evil else (.025,.24,1),0,4)
    crystal=material(name+'_Crystal',(.45,.016,.045) if evil else (.065,.24,.65),.42,1.2)
    crystal.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.48
    crystal.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.13
    bone=material(name+'_AncientBone',(.24,.19,.12)) if evil else None
    # Individually dressed voussoirs give the platform visible stone joints.
    for step in range(5):
        z=step*.15;r=3.8-step*.22
        if evil:
            front=-2.7+step*.27
            for block in range(8):
                left=-1.8+block*.45
                slab('Straight dark stair tread',[(left+.01,front),(left+.44,front),(left+.44,.65),(left+.01,.65)],z,.145,stone,.02)
            for sign in (-1,1):
                for block in range(3):
                    xx=sign*(2.12+block*.44);yy=-.45+step*.12
                    slab('Broken side masonry',[(xx-.21,yy-.8),(xx+.20,yy-.76),(xx+.19,yy+.8),(xx-.22,yy+.77)],z,.145,stone,.025)
            continue
        for block in range(32):
            a=TAU*block/32+.006;b=TAU*(block+1)/32-.006
            vertices=[(rr*math.cos(t),ry*math.sin(t),zz) for zz in (z,z+.145) for rr,ry,t in ((r,2.65-step*.25,a),(r,2.65-step*.25,b),(0,0,b),(0,0,a))]
            surface('Dressed plinth stone',vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(3,0,4,7)],stone,.018)
        if step==4:loft('Upper plinth inlaid rim',[(0,0,z+.13,r+.015,2.66-step*.25),(0,0,z+.15,r+.015,2.66-step*.25)],metal,32,.006)
    # Layered archivolts, front and back, around a 3.4m clear opening.
    for y in (-.32,.32):
        for width,rad,mat in ((1.89,.19,stone),(2.14,.15,stone),(1.74,.037,metal),(1.84,.052,metal),(2.04,.045,metal),(2.28,.06,metal)):
            sweep('Pointed archivolt',arch(width,5.55,2.35+(width-1.74)*.8,y),rad,mat,8)
        crown=arch(1.97,5.55,2.50,y-.19)[2:49]
        for sign in (-1,1):
            for i in range(2,len(crown)-2,4):
                x,yy,z=crown[i];x*=sign
                sweep('Crown rune',[(x-.045,yy,z-.07),(x+.03,yy,z),(x-.04,yy,z+.065)],.012,glow)
            for i in range(10):
                z=1.0+i*.45;x=sign*2.18
                sweep('Stone course joint',[(x-.075,y-.15,z),(x+.065,y-.15,z)],.009,metal)
        for sign in (-1,1):
            for i in range(14):
                z=1.25+i*.33
                x=sign*1.97
                # Original abstract three-stroke sigils, not text or a borrowed alphabet.
                stroke=[(x-.045,y-.20,z-.075),(x+.05,y-.20,z),(x-.025,y-.20,z+.08)]
                sweep('Luminous rune',stroke,.014,glow)
                if i%2:sweep('Rune cross stroke',[(x-.065,y-.20,z+.025),(x+.065,y-.20,z-.025)],.012,glow)
    for sign in (-1,1):
        tower(sign*2.55,.05,.70,6.7,stone,metal,evil)
        tower(sign*2.96,.35,.48,4.9,stone,metal,evil)
        tower(sign*1.58,.47,7.35,1.45,stone,metal,evil)
        tower(sign*.79,.5,8.08,1.40,stone,metal,evil)
        # Flying buttresses: shaped layered ribs, not bars blocking the passage.
        for y in (-.18,.65):
            sweep('Swept support rib',[(sign*3.22,y,.25),(sign*2.8,y,1.0),(sign*2.53,y,2.8),(sign*2.40,y,5.9),(sign*1.72,y,7.6),(0,y,8.9)],.075,metal,6)
        tower(sign*2.44,-1.1,.30,2.45,stone,metal,evil)
        loft('Crystal cradle',[(sign*2.44,-1.1,2.09,.2,.2),(sign*2.44,-1.1,2.20,.36,.36),(sign*2.44,-1.1,2.32,.27,.27)],metal)
        for dx,dz,scale in ((0,0,1),(-.19,-.06,.5),(.18,-.12,.62)):
            x=sign*2.44+dx;y=-1.1;z=2.27+dz
            loft('Faceted energy focus',[(x,y,z,.02,.02),(x,y,z+.20*scale,.18*scale,.15*scale),(x,y,z+.65*scale,.13*scale,.12*scale),(x+.045*sign,y,z+1.06*scale,.001,.001)],crystal,6,0)
        banner(sign*3.75,.1,4.70,evil,cloth,metal,glow)
        if evil:
            for i,(xx,yy,zz,scale) in enumerate(((2.85,-1.60,.2,.9),(3.08,-1.36,.32,.8),(2.96,-1.55,.63,.75),(3.37,-.82,.13,.7))):
                skull(sign*xx,yy,zz,scale,bone)
            for j in range(27):
                t=j/26;x=sign*(2.55+1.2*t);z=5.7-1.25*t-.6*math.sin(math.pi*t)
                points=[(x+.075*math.cos(TAU*k/16),.03+.045*math.sin(TAU*k/16)*(j%2),z+.12*math.sin(TAU*k/16)) for k in range(17)]
                sweep('Interlinked hanging chain',points,.022,metal,6)
            for i in range(6):
                x=sign*(2.25-.17*i);z=5.8+i*.48
                loft('Curved thorn',[(x,0,z,.15,.12),(x+sign*.18,0,z+.23,.10,.09),(x+sign*.30,0,z+.70,.002,.002)],metal,6)
    tower(0,.55,8.2,2.65,stone,metal,evil)
    crest(0,-.59,7.75,1.0,evil,metal,glow)
    crest(0,.71,6.60,.62,evil,metal,glow)
    # Rear spine and heraldic panel are actual geometry visible in side/back review.
    surface('Rear heraldic panel',[(-1.1,.65,2.2),(1.1,.65,2.2),(1.1,.65,6.1),(0,.65,7.1),(-1.1,.65,6.1)],[(0,1,2,3,4)],cloth)
    for sign in (-1,1):sweep('Rear panel border',[(0,.68,1.9),(sign*1.12,.68,2.3),(sign*1.12,.68,6.1),(0,.68,7.2)],.032,metal)
    # Separate effect surface. Collision must NEVER use this sealed silhouette.
    opening=arch(1.70,5.55,2.35,.06)
    obj=surface('PortalEnergy_NoCollision',opening,[tuple(range(len(opening)))],vortex(name,evil))
    uv=obj.data.uv_layers.new(name='PortalUV')
    for loop in obj.data.loops:
        p=obj.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=(p.x/3.4+.5,(p.z-.75)/7.15)
    return name


def render(name):
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1100;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.world.color=(.035,.035,.04)
    scene.view_settings.view_transform='AgX'
    for location,energy,size in (((-7,-9,13),1900,7),((6,-3,7),900,6),((1,5,11),2300,5)):
        data=bpy.data.lights.new('Studio softbox','AREA');data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=location
        obj.rotation_euler=(Vector((0,0,4))-obj.location).to_track_quat('-Z','Y').to_euler()
    camdata=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
    camdata.type='ORTHO';camdata.ortho_scale=12.3
    for view,pos in [('hero',(11,-22,12)),('front',(0,-25,6.3)),('back',(0,25,6.3)),('side',(25,-.1,6.3))]:
        cam.location=pos;cam.rotation_euler=(Vector((0,0,5))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/f'{name}-{view}.png');bpy.ops.render.render(write_still=True)


records=[]
for evil in (False,True):
    name=build(evil)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':obj.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in bpy.context.selected_objects if o.type=='MESH')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{name}.blend'))
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'{name}.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',bake_anim=False)
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'{name}.glb'),export_format='GLB',use_selection=True,export_apply=True)
    records.append(dict(name=name,fbxSha256=hashlib.sha256((OUT/f'{name}.fbx').read_bytes()).hexdigest(),
                        referenceSha256=hashlib.sha256((OUT/'references'/('riftbound.png' if evil else 'aegis.png')).read_bytes()).hexdigest(),
                        artApproved=False,nativeApproved=False,
                        limitations=['Procedural Blender surface detail requires native material translation.',
                                     'Vortex animation and collision are not yet native verified.',
                                     'Reference-faithful stone damage and fine sculpted ornament remain unfinished.'] if evil else
                                     ['Procedural Blender surface detail requires native material translation.',
                                      'Vortex animation and collision are not yet native verified.']))
    render(name)
(OUT/'models.json').write_text(json.dumps(records,indent=2)+'\n')
