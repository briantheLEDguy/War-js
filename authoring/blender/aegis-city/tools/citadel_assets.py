"""Original monumental siege precinct and an irregular, eroded mountain massif."""
import bpy
import math

KINDS = ['citadel_bastion', 'citadel_arcade', 'citadel_gate', 'battle_cover', 'mountain_massif', 'mountain_passage', 'mountain_redoubt', 'mountain_seal', 'mountain_vault']

def build_citadel_asset(kind, materials, box, roof, arch):
    def tower(x, y, height, width=10):
        box('bastion_drum', (x,y,height/2), (width,width,height), 'limestone')
        for level in [height*.35,height*.7,height]:
            box('carved_cornice',(x,y,level),(width+1,width+1,.8),'stone')
        for dx in [-width/2,width/2]:
            for dy in [-width/2,width/2]:
                if kind != 'citadel': box('crown_pinnacle',(x+dx,y+dy,height+2),(1.4,1.4,4),'limestone')
        for level in [9,18,27]:
            if level < height and kind != 'citadel': box('arrow_window',(x,y-width/2-.06,level),(1,.14,2.8),'glow')

    if kind == 'citadel':
        # Hollow shell: a nine-metre doorway leads straight into the playable hall.
        # Deepen toward the court; the rear wall and mountain doorway stay fixed.
        box('great_hall_floor',(0,-18,-.2),(72,62,.4),'flagstone')
        for x in [-20.5,20.5]: box('front_wall',(x,-48.3,18),(31,1.4,36),'limestone')
        box('portal_overwall',(0,-48.3,24),(10,1.4,24),'limestone')
        # The mountain connection passes beneath the existing six-metre gallery.
        for x in [-21.5,21.5]: box('rear_wall',(x,12.3,18),(29,1.4,36),'limestone')
        box('rear_passage_lintel',(0,12.3,20.7),(14,1.4,30.6),'limestone')
        for x in [-35.3,35.3]: box('side_wall',(x,-18,18),(1.4,62,36),'limestone')
        for x in [-21,21]:
            for y in [-7.5,7.5]: box('side_chamber_partition',(x,y,2.75),(.8,7,5.5),'stone')
        before = set(bpy.context.scene.objects)
        roof(75,65,11,36,'slate','limestone')
        for ob in set(bpy.context.scene.objects) - before: ob.location.y -= 18
        for x in [-44,44]:
            for y in [-46,10]: tower(x,y,44,11)
        for x in [-31,-21,-11,11,21,31]:
            box('facade_buttress',(x,-50,16),(2.4,3,32),'stone')
        box('portal_lintel',(0,-50,13),(13,3,2),'stone')
        for x in [-7,7]: box('portal_column',(x,-50,6),(2,3,12),'stone')
        for x in [-28,28]: box('realm_banner',(x,-50.2,25),(4,.12,9),'canvas_red')
        for x in [-16,16]:
            for y in [-42,-26,-6,6]:
                box('hall_pier',(x,y,17),(1.8,1.8,34),'stone')
                box('pier_capital',(x,y,33),(3,3,1),'limestone')
        box('rear_gallery',(0,10.7,5.8),(68,2,.4),'stone')
        for x in [-32,32]:
            box('side_gallery',(x,-18,5.8),(6,60,.4),'stone')
            inner=29 if x>0 else -29
            for y in range(-47,11,2): box('gallery_baluster',(inner,y,6.65),(.22,.22,1.3),'iron')
            box('gallery_handrail',(inner,-18.5,7.3),(.25,59,.2),'oak')
        for x in range(-22,23,4):
            box('rear_gallery_baluster',(x,9.7,6.65),(.22,.22,1.3),'iron')
        box('rear_gallery_handrail',(0,9.7,7.3),(46,.25,.2),'oak')
        for x in [-34,34]:
            for y in [-44,-32,-20,-8,4]: box('interior_lancet',(x,y,15),(.15,2,5),'glow')
        from citadel_gothic import decorate_citadel
        decorate_citadel(materials, box)
    elif kind == 'citadel_bastion':
        tower(0,0,32,11)
        roof(12,12,10,32.4,'copper','limestone')
    elif kind == 'citadel_gate':
        # Towers supply the jambs; avoid overlapping coplanar arch piers.
        for side in [-1,1]:
            for i in range(9):
                t=(i+.5)/9
                ob=box('pointed_gate_voussoir',(side*9*(1-t),0,15+6*t),(1.6,5,1.4),'stone')
                ob.rotation_euler.y=side*math.atan2(9,6)
        box('gate_gallery',(0,0,19),(18,6,4),'limestone')
        for x in [-12,12]: tower(x,0,25,6)
        for x in [-8,0,8]: box('gate_banner',(x,-3.2,19),(2,.12,5),'canvas_red')
    elif kind == 'citadel_arcade':
        # Long sides are open colonnades: collision is authored per pier.
        for y in range(-30,31,10):
            box('arcade_pier',(0,y,7),(4,2,14),'limestone')
            box('pier_cap',(0,y,14),(5,3,1),'stone')
        box('gallery_entablature',(0,0,16),(6,64,3),'limestone')
        roof(7,65,5,17.5,'slate','limestone')
    elif kind == 'battle_cover':
        box('stone_screen',(0,0,1.6),(5,2.4,3.2),'stone')
        box('screen_coping',(0,0,3.3),(5.5,2.8,.35),'limestone')
        for x in [-2,2]: box('broken_pinnacle',(x,0,4),(1,1,1.5),'stone')
    elif kind == 'mountain_passage':
        # The open-ended sleeve is reusable along and across the mountain route.
        box('passage_floor',(0,0,-.25),(20,24,.5),'flagstone')
        for x in [-9.5,9.5]:
            box('excavated_wall',(x,0,9),(1,24,18),'granite')
            box('passage_plinth',(x,0,.5),(1.1,24,1),'stone')
            box('wall_cornice',(x,0,13),(1.15,24,.6),'limestone')
        box('buried_roof',(0,0,19),(20,24,2),'granite')
        for y in [-10,0,10]:
            for side in [-1,1]:
                for i in range(7):
                    t=(i+.5)/7
                    ob=box('vault_rib',(side*8.7*(1-t),y,14.6+2.9*t),(1.1,.6,1.3),'limestone')
                    ob.rotation_euler.y=side*math.atan2(8.7,2.9)
            box('vault_keystone',(0,y,17.7),(1.5,.8,.6),'stone')
        for x in [-8.85,8.85]:
            for y in [-6,6]:
                box('wall_lamp_backplate',(x,y,4),(.18,.9,2),'iron')
                box('wall_lamp_glass',(x-.13 if x>0 else x+.13,y,4),(.14,.55,1.35),'glow')
    elif kind == 'mountain_redoubt':
        box('redoubt_floor',(0,0,-.3),(120,96,.6),'flagstone')
        for x in [-35,35]: box('front_wall',(x,-47.5,16),(50,1,32),'granite')
        box('front_portal_lintel',(0,-47.5,23),(20,1,18),'granite')
        box('rear_wall',(0,47.5,16),(120,1,32),'granite')
        for x in [-59.5,59.5]:
            # Blender -X becomes world +X when the shell is placed at rotY=PI.
            # The treasury connects the forehall to the throne hall through two
            # portals; the opposite ten-metre portal still leads to the crypt seal.
            spans=[(-32.5,31),(9.5,33),(41,14)] if x<0 else [(-32.5,31),(20.5,55)]
            for y,length in spans:
                box('side_wall',(x,y,16),(1,length,32),'granite')
            box('side_portal_lintel',(x,-12,21),(1,10,22),'granite')
            if x<0: box('treasury_return_lintel',(x,30,21),(1,8,22),'granite')
            for y in [-37,1,36]:
                box('wall_buttress',(x,y,15),(1.7,3,30),'stone')
                box('recessed_lancet',(x-.9 if x>0 else x+.9,y,12),(.1,1.2,5),'glow')
        box('mountain_roof',(0,0,33),(120,96,2),'granite')
        # The guarded forehall opens into a fifty-two-metre-deep royal chamber.
        for x,width in [(-50,20),(-18.5,19),(18.5,19),(50,20)]:
            box('command_partition',(x,-4,14),(width,1,28),'stone')
        for x,width in [(-34,12),(0,18),(34,12)]:
            box('command_portal_lintel',(x,-4,20),(width,1,16),'limestone')
        for x in [-42,42]:
            for y in [-28,8,28]:
                box('redoubt_pier',(x,y,16),(2.4,2.4,32),'stone')
                box('pier_foot',(x,y,.6),(3,3,1.2),'granite')
                box('pier_capital',(x,y,30),(4,4,2),'limestone')
                for z in [8,18]: box('pier_belt',(x,y,z),(2.7,2.7,.5),'limestone')
        for y in [-28,8,38]:
            box('high_crossbeam',(0,y,31),(117,2,2),'stone')
            for x in [-28,0,28]:
                box('ceiling_coffer',(x,y,30),(18,1,.5),'limestone')
        for x in [-58.8,58.8]:
            for y in [-42,8,41]:
                box('redoubt_banner',(x,y,19),(.12,3,8),'canvas_red')
                box('banner_rail',(x,y,23),(.3,3.7,.3),'iron')
        for x in [-44,-22,22,44]:
            box('command_rear_relief',(x,46.85,15),(7,.3,10),'limestone')
            box('command_relief_inset',(x,46.64,15),(5,.14,8),'stone')
            box('command_relief_lancet',(x,46.52,15),(.65,.12,5),'glow')
        # Masonry panels sit against the rear wall, leaving all three combat aisles open.
        for x in range(-52,53,13):
            box('royal_wainscot',(x,46.85,2.3),(11,.3,4.6),'stone')
            box('wainscot_coping',(x,46.62,4.7),(11.3,.35,.3),'limestone')
        for x in [-58.7,58.7]:
            box('royal_wall_cornice',(x,22,26),(.5,48,.6),'limestone')
    elif kind == 'mountain_vault':
        # A buried strongroom. Two west-facing world portals create a secure
        # treasury route from the forehall into the royal chamber behind it.
        box('vault_floor',(0,0,-.3),(48,84,.6),'flagstone')
        for y in [-41.5,41.5]: box('vault_end_wall',(0,y,10),(48,1,20),'granite')
        box('vault_east_wall',(-23.5,0,10),(1,84,20),'granite')
        for y,length in [(-32.5,19),(3.5,33),(35,14)]:
            box('vault_west_wall',(23.5,y,10),(1,length,20),'granite')
        for y,width in [(-18,10),(24,8)]:
            box('vault_portal_lintel',(23.5,y,15),(1,width,10),'granite')
        box('vault_buried_roof',(0,0,21),(48,84,2),'granite')
        for x in [-16,16]:
            for y in [-28,28]:
                box('vault_pier',(x,y,10),(2.4,2.4,20),'stone')
                box('vault_pier_foot',(x,y,.6),(3,3,1.2),'granite')
                box('vault_capital',(x,y,18.8),(4,4,1.2),'limestone')
                for z in [5,11,16]: box('vault_pier_iron_belt',(x,y,z),(2.65,2.65,.22),'iron')
        # Individually cut stone ribs carry iron tension straps. All decorative
        # ceiling pieces remain above fourteen metres; only four piers touch floor.
        for y in [-28,-4,20,36]:
            for side in [-1,1]:
                for i in range(9):
                    t=(i+.5)/9
                    ob=box('strongroom_vault_rib',(side*22.4*(1-t),y,14.9+4.5*t),(2.9,.8,.9),'limestone')
                    ob.rotation_euler.y=side*math.atan2(4.5,22.4)
                ob=box('vault_iron_brace',(side*11.2,y,17.15),(22.85,.25,.2),'iron')
                ob.rotation_euler.y=side*math.atan2(4.5,22.4)
            box('vault_carved_keystone',(0,y,19.5),(1.7,1.1,.7),'stone')
            box('keystone_bronze_inlay',(0,y-.58,19.4),(.7,.08,.4),'copper')
        for y in [-41,41]:
            box('treasury_end_cornice',(0,y,12.5),(46,.4,.5),'limestone')
            for x in [-16,-8,0,8,16]:
                box('treasury_blind_panel',(x,y,7),(5,.25,6),'stone')
                box('treasury_panel_inset',(x,y-.18 if y>0 else y+.18,7),(3.8,.18,4.8),'iron')
        for y in [-33,-9,9,33]:
            box('vault_wall_lamp_plate',(-22.9,y,5),(.15,.9,2),'iron')
            box('vault_wall_lamp_glass',(-22.77,y,5),(.13,.6,1.5),'glow')
    elif kind == 'mountain_seal':
        # A permanent sealed threshold signals future content, never an active gate.
        for x in [-6,6]:
            box('sealed_jamb',(x,0,7),(2,3,14),'granite')
            box('jamb_face',(x,-1.55,7),(1.4,.3,12),'limestone')
        box('sealed_lintel',(0,0,13),(10,3,2),'stone')
        box('buried_door',(0,0,6),(10,1,12),'iron')
        for x in [-4,-2,0,2,4]: box('sealed_door_rib',(x,-.65,6),(.18,.35,11.5),'stone')
        for z in [1,4,8,11]:
            box('sealed_door_band',(0,-.7,z),(10,.4,.35),'iron')
            for x in [-4,-2,0,2,4]: box('door_rivet',(x,-.95,z),(.22,.13,.22),'limestone')
        for x in [-2.8,2.8]:
            ob=box('binding_diagonal',(x,-.96,6),(.35,.3,9),'stone')
            ob.rotation_euler.y=-.6 if x>0 else .6
        box('seal_cartouche',(0,-1.22,6),(2.2,.3,2.8),'limestone')
        box('seal_inset',(0,-1.43,6),(1.5,.12,2),'iron')
        box('seal_vertical',(0,-1.52,6),(.18,.08,1.4),'copper')
        box('seal_crosspiece',(0,-1.52,6.3),(1,.08,.18),'copper')
    elif kind == 'mountain_massif':
        # Unequal peaks, broad shoulders, branching gullies and a tapering foothill.
        # No periodic sawtooth crest or vertical back wall.
        peaks=[(-190,230,245,110,130),(20,310,340,100,150),(220,360,285,135,110),(-320,430,180,100,145),(340,180,140,105,90)]
        def mountain_height(x,d):
            h=max(amp*math.exp(-((x-cx)/sx)**2/2-((d-cz)/sz)**2/2) for cx,cz,amp,sx,sz in peaks)
            edge=max(0,math.sin(math.pi*(x/1040+.5)))**.55*max(0,math.sin(math.pi*d/650))**.65
            gullies=1+.11*math.sin(x*.032+d*.021)+.055*math.sin(x*.087-d*.055)+.025*math.cos(x*.173+d*.137)
            h=max(0,h*edge*gullies)
            # Rock remains above the playable shells, including a full grid-cell
            # margin around their roofs. Feathering preserves the eroded shoulder.
            for half_width,front,back,clearance in [(70,18,134,40),(20,0,28,24),(96,46,82,24)]:
                outside=max(0,abs(x)-half_width,front-d,d-back)
                t=max(0,1-outside/24)
                feather=t*t*(3-2*t)
                h=max(h,clearance*feather)
            # The eastern treasury is off the main ridge axis. Protect its full
            # roof and one sampling-cell margin without flattening the mountain.
            outside=max(0,80-x,x-148,30-d,d-134)
            t=max(0,1-outside/24)
            h=max(h,30*t*t*(3-2*t))
            return h
        nx,nz=110,100; vertices=[]; faces=[]
        for j in range(nz+1):
            d=j/nz*650
            for i in range(nx+1):
                x=(i/nx-.5)*1040
                vertices.append((x,-d,mountain_height(x,d)))
        for j in range(nz):
            for i in range(nx):
                a=j*(nx+1)+i; faces.append((a,a+nx+1,a+nx+2,a+1))
        # The raised front shoulder closes against the city retaining wall; its
        # central cut leaves the actual mountain passage open below its roof.
        front_x=sorted(set([(i/nx-.5)*1040 for i in range(nx+1)]+[-10,10]))
        for left,right in zip(front_x,front_x[1:]):
            bottom=20 if left>=-10 and right<=10 else 0
            if max(mountain_height(left,0),mountain_height(right,0))<=bottom: continue
            a=len(vertices)
            vertices.extend([(left,0,bottom),(right,0,bottom),(right,0,mountain_height(right,0)),(left,0,mountain_height(left,0))])
            faces.append((a,a+1,a+2,a+3))
        mesh=bpy.data.meshes.new('eroded_granite_massif');mesh.from_pydata(vertices,[],faces);mesh.update()
        ob=bpy.data.objects.new('eroded_granite_massif',mesh);bpy.context.collection.objects.link(ob)
        mesh.materials.append(materials['granite']);uv=mesh.uv_layers.new(name='RockUV')
        for face in mesh.polygons:
            face.use_smooth=face.index<nx*nz
            for index in face.loop_indices:
                v=mesh.vertices[mesh.loops[index].vertex_index].co
                uv.data[index].uv=(v.x/55,(v.y if face.index<nx*nz else v.z)/55)
