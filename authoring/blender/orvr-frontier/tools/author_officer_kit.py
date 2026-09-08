"""Original dispatch satchel, ledger, seal and writing tools for supply officers."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_draft_horse as geometry
import build_collection as build
ROOT=build.ROOT;ASSET='frontier_supply_officer_kit'


def make():
    leather=geometry.material('officer.oxhide',(.067,.027,.011),.73)
    edge=geometry.material('officer.burnished_edges',(.026,.010,.004),.61)
    linen=geometry.material('officer.linen_thread',(.24,.19,.11),.86)
    brass=geometry.material('officer.old_brass',(.25,.17,.06),.43,.83)
    paper=geometry.material('officer.rag_paper',(.43,.36,.23),.91)
    ink=geometry.material('officer.ink',(.013,.009,.005),.88)
    sealwax=geometry.material('officer.seal_wax',(.10,.015,.009),.69)
    for material in (leather,edge,paper):
        nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=185;noise.inputs['Detail'].default_value=3
        bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.0007;bump.inputs['Strength'].default_value=.4
        links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    objects=[]
    # Individually measured soft gussets: a flattened base, full central pouch,
    # narrow throat and inset lining; top remains an actual open bag cavity.
    outline=[(-1,-.58),(-.79,-1),(.76,-1),(1,-.53),(1,.55),(.74,1),(-.77,1),(-1,.53)]
    sections=[(.018,.142,.055),(.035,.169,.068),(.115,.179,.071),(.265,.166,.059),(.333,.151,.050),(.340,.143,.043),(.263,.153,.050),(.065,.151,.052),(.040,.129,.039)]
    rings=[[(x*width,y*depth,z) for x,y in outline] for z,width,depth in sections]
    pouch=geometry.smooth(geometry.loft('officer_satchel_gusset',rings,leather),2);objects.append(pouch)
    # The cover folds over the rear lip and settles across the front opening.
    flap_stations=[(.065,.315,.150),(.057,.365,.153),(.018,.379,.162),(-.042,.366,.170),(-.080,.321,.164),(-.080,.240,.144),(-.079,.226,.125)]
    vertices=[]
    for y,z,width in flap_stations:
        vertices.extend([(-width,y,z),(0,y-.007,z+.009),(width,y,z)])
    faces=[[i,i+1,i+4,i+3] for i in range(0,len(vertices)-3,3)]+[[i+1,i+2,i+5,i+4] for i in range(0,len(vertices)-3,3)]
    flap=geometry.smooth(geometry.mesh('officer_bound_flap',vertices,faces,leather),2)
    solid=flap.modifiers.new('folded_leather_thickness','SOLIDIFY');solid.thickness=.006;objects.append(flap)
    for side in (-1,1):
        path=[(side*(width-.005),y-.002,z+.003) for y,z,width in flap_stations]
        objects.append(geometry.tube('officer_flap_piping_'+str(side),path,edge,.0025))
        # Every stitch is an actual short hand-placed thread spanning the seam.
        seam=[Vector(p) for p in path]
        for segment,(a,b) in enumerate(zip(seam,seam[1:])):
            count=max(2,round((b-a).length/.012))
            for stitch in range(count):
                p=a.lerp(b,(stitch+.32)/count);q=a.lerp(b,(stitch+.65)/count)
                objects.append(geometry.tube(f'officer_flap_stitch_{side}_{segment}_{stitch}',[p+Vector((-side*.004,-.001,0)),q+Vector((side*.001,-.001,0))],linen,.0008))
        loop=geometry.strap('officer_belt_loop_'+str(side),[(side*.095,.046,.275),(side*.095,.083,.345),(side*.095,.079,.405),(side*.095,.044,.401),(side*.095,.040,.334)],edge,.025,(1,0,0));objects.append(loop)
        # Reinforced lower corners are inset open patches, not intersecting boxes.
        patch=geometry.mesh('officer_corner_patch_'+str(side),[(side*.12,-.067,.030),(side*.17,-.060,.053),(side*.168,-.065,.130),(side*.123,-.076,.085)],[[0,1,2,3]],edge)
        solid=patch.modifiers.new('corner_patch_thickness','SOLIDIFY');solid.thickness=.003;objects.append(patch)
    strap=geometry.strap('officer_closing_strap',[(0,-.047,.374),(0,-.088,.301),(0,-.091,.222),(0,-.077,.124)],edge,.029,(1,0,0));objects.append(strap)
    buckle=[(-.021,-.096,.237),(-.025,-.096,.248),(-.023,-.096,.270),(.022,-.096,.270),(.025,-.096,.248),(.021,-.096,.237),(-.021,-.096,.237)]
    objects.append(geometry.tube('officer_buckle_frame',buckle,brass,.0033))
    objects.append(geometry.tube('officer_buckle_tongue',[(0,-.096,.242),(0,-.101,.260),(0,-.091,.268)],brass,.0018))
    # A folded stack of signatures protrudes above the pouch, beneath the flap.
    book_outline=[(-.122,-.035),(-.126,-.026),(-.124,.032),(-.115,.039),(.113,.036),(.121,.027),(.120,-.031),(.109,-.038)]
    for index,z in enumerate([.322,.327,.332,.337,.342,.347]):
        rings=[[(x,y,z+offset) for x,y in book_outline] for offset in (0,.003)]
        objects.append(geometry.loft('officer_ledger_signature_'+str(index),rings,paper))
    for z in (.318,.351):
        cover=geometry.loft('officer_ledger_cover_'+str(z),[[(x*1.03,y*1.06,z+d) for x,y in book_outline] for d in (0,.005)],edge);objects.append(cover)
    for side in (-1,1):
        for i in range(3):
            x=side*(.045+i*.019)
            objects.append(geometry.tube(f'officer_signature_binding_{side}_{i}',[(x,.04,.321),(x,.044,.336),(x,.04,.357)],linen,.001))
    # Original hollow leather quill sleeve on the right-hand gusset.
    sleeve=geometry.strap('officer_quill_sleeve',[(.167,-.02,.105),(.194,-.032,.150),(.193,-.008,.211),(.169,.012,.216)],edge,.043,(0,1,0));objects.append(sleeve)
    shaft=[(.183,-.002,.153),(.183,.002,.245),(.174,.009,.344),(.166,.012,.407)]
    objects.append(geometry.tube('officer_quill_shaft',shaft,linen,.0016))
    vertices=[]
    for i in range(19):
        t=i/18;center=Vector((.182-.020*t,.006,.262+.161*t));breadth=.014*math.sin(math.pi*(t*.98+.01))
        vertices.extend([center+Vector((-breadth,0,0)),center+Vector((0,-.0013,.002)),center+Vector((breadth*.78,0,.006))])
    faces=[]
    for i in range(0,len(vertices)-3,3):faces.extend([[i,i+1,i+4,i+3],[i+1,i+2,i+5,i+4]])
    vane=geometry.mesh('officer_quill_continuous_vane',vertices,faces,paper)
    solid=vane.modifiers.new('feather_vane_thickness','SOLIDIFY');solid.thickness=.00035;objects.append(vane)
    # Stamped wax tally tied at the opposite seam, with an original three-notch mark.
    stamp=[(-.196,-.025,.201),(-.206,-.027,.213),(-.202,-.028,.231),(-.189,-.027,.241),(-.174,-.027,.231),(-.173,-.026,.214)]
    medallion=geometry.loft('officer_tally_seal',[[Vector(p)+Vector((0,offset,0)) for p in stamp] for offset in (0,.006)],sealwax);objects.append(medallion)
    objects.append(geometry.tube('officer_tally_cord',[(-.143,.012,.305),(-.174,-.001,.288),(-.185,-.020,.240)],linen,.0012))
    for i in range(3):objects.append(geometry.tube('officer_tally_mark_'+str(i),[(-.197+i*.007,-.030,.215),(-.195+i*.007,-.030,.227)],ink,.0008))
    fitting=build.evaluated_join([pouch,flap],'construction.satchel_fitting_surface');fitting.hide_set(True);fitting.hide_render=True
    objects.remove(strap);bpy.data.objects.remove(strap,do_unlink=True)
    # Project a dense, continuous closing tongue onto the actual front surface;
    # nearest-surface projection can jump to the underside at the folded lip.
    vertices=[]
    for i in range(25):
        z=.304-i*.0066;width=.0145*(.65+.35*math.sin(math.pi*(i+.7)/25.7))
        for x in (-width,width):
            found,point,_,_=fitting.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
            if not found:raise ValueError('Closing tongue must meet the finished leather surface')
            vertices.append((x,point.y-.005,z))
    strap=geometry.mesh('officer_closing_strap',vertices,[[i+1,i,i+2,i+3] for i in range(0,len(vertices)-2,2)],edge)
    solid=strap.modifiers.new('closing_tongue_thickness','SOLIDIFY');solid.thickness=.004;objects.append(strap)
    for obj in objects:
        if obj.name.startswith(('officer_corner_patch_','officer_flap_stitch_','officer_flap_piping_')):
            if obj.name.startswith('officer_corner_patch_'):
                modifier=obj.modifiers.new('fitted_patch_subdivision','SUBSURF');modifier.levels=2;modifier.render_levels=2
                obj.modifiers.move(len(obj.modifiers)-1,0)
            modifier=obj.modifiers.new('fit_to_finished_satchel','SHRINKWRAP');modifier.target=fitting
            modifier.wrap_method='NEAREST_SURFACEPOINT';modifier.wrap_mode='ABOVE_SURFACE';modifier.offset=.004 if obj.name=='officer_closing_strap' else .0018
            first_solidify=next((i for i,entry in enumerate(obj.modifiers) if entry.type=='SOLIDIFY'),len(obj.modifiers)-1)
            obj.modifiers.move(len(obj.modifiers)-1,first_solidify)
        obj['source_policy']='Original fitted dispatch gear, authored cage/cloth paths, no primitive geometry';obj['rigid_group']='officer_kit'
    return objects


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True);objects=make()
    source=ROOT/'masters'/f'{ASSET}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source))
    if args.preview:build.set_view(objects,ROOT/'review'/f'{ASSET}_source.png')
    records=[]
    for level in (0,1,2):
        mesh=build.evaluated_join(objects,f'{ASSET}_lod{level}')
        if level:
            modifier=mesh.modifiers.new('fitted_distance_reduction','DECIMATE');modifier.ratio=.55 if level==1 else .20
            bpy.context.view_layer.objects.active=mesh;bpy.ops.object.modifier_apply(modifier=modifier.name)
        if not mesh.data.uv_layers:
            mesh.data.uv_layers.new(name='construction_uv');bpy.context.view_layer.objects.active=mesh
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
        textures=build.baker.bake_module_atlas(mesh,f'{ASSET}_lod{level}',ROOT/'textures/baked',resolution=2048 if level==0 else 1024 if level==1 else 512)
        modifier=mesh.modifiers.new('stable_runtime_triangles','TRIANGULATE');bpy.context.view_layer.objects.active=mesh;bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True)
        socket=bpy.data.objects.new('socket.belt_mount',None);bpy.context.scene.collection.objects.link(socket);socket.location=(0,.060,.365);socket.select_set(True)
        runtime=ROOT/'runtime'/f'{ASSET}_lod{level}.glb'
        bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True)
        records.append({'level':level,'path':str(runtime.relative_to(ROOT)),'sha256':build.sha(runtime),'bytes':runtime.stat().st_size,'triangles':len(mesh.data.polygons),'materials':len(mesh.data.materials),'textures':textures})
        bpy.data.objects.remove(socket,do_unlink=True);mesh.hide_set(True);mesh.hide_render=True
    (ROOT/'review'/f'{ASSET}_build.json').write_text(json.dumps({'asset_id':ASSET,'approval':'pending_visual_review','source_sha256':build.sha(Path(__file__)),'master':str(source.relative_to(ROOT)),'master_sha256':build.sha(source),'lods':records,'limitations':['Supply officer body and pose must use an approved existing race profile; belt fit is profile-specific.']},indent=2)+'\n')


if __name__=='__main__':main()
