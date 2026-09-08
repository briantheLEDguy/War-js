"""Original Riftbound street assemblies; named editable parts, no runtime proxies."""
import json, math, random
from pathlib import Path

PROFILES=json.loads((Path(__file__).resolve().parents[4]/'scripts/campaign/riftspire-district-props.json').read_text())
DETAIL_KINDS=list(PROFILES)

def build_detail(kind, kit):
    box,mesh,beam,tube,ring,lantern,arch=[kit[k] for k in ['box','mesh','beam','tube','ring','lantern','arch']]
    pi=math.pi

    def turned(name,x,y,z,profile,mat='iron',sides=16,cap=True):
        verts=[(x+r*math.cos(i*2*pi/sides),y+r*math.sin(i*2*pi/sides),z+h) for h,r in profile for i in range(sides)]
        faces=[(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(len(profile)-1) for i in range(sides)]
        if cap:faces += [tuple(range(sides-1,-1,-1)),tuple((len(profile)-1)*sides+i for i in range(sides))]
        return mesh(name,verts,faces,mat)

    def hoop(name,x,y,z,r,mat='iron'):
        tube(name,[(x+r*math.cos(i*pi/12),y+r*math.sin(i*pi/12),z) for i in range(25)],.065,mat)

    def barrel(x,y,z=0,s=1):
        turned('coopered_barrel',x,y,z,[(0,.48*s),(.2*s,.55*s),(.7*s,.64*s),(1.2*s,.56*s),(1.4*s,.48*s)],'timber')
        for h,r in [(.1,.52),(.35,.59),(1.05,.59),(1.3,.52)]:hoop('riveted_barrel_hoop',x,y,z+h*s,r*s)
        for i in range(12):
            a=i*pi/6;tube('individual_stave_seam',[(x+r*s*math.cos(a),y+r*s*math.sin(a),z+h*s) for h,r in [(.05,.50),(.7,.645),(1.35,.50)]],.015,'iron')
        box('barrel_bung',(x,y,z+1.41*s),(.18*s,.18*s,.05*s),'trim')

    def chest(x,y,z=0,w=1.8,d=1.1,h=.95):
        box('bound_supply_chest',(x,y,z+h/2),(w,d,h),'timber')
        for dx in [-w*.35,w*.35]:
            box('iron_chest_binding',(x+dx,y-d/2-.03,z+h/2),(.14,.07,h),'iron')
            box('lid_iron_binding',(x+dx,y,z+h+.03),(.14,d+.1,.07),'iron')
        box('chest_lock',(x,y-d/2-.07,z+h*.75),(.25,.12,.35),'iron')
        ring('chest_lock_ring',x,y-d/2-.15,z+h*.7,.12)

    def rune(x,y,z,s=1):
        for a,b in [((0,0),(0,2)),((-.6,1.3),(0,2)),((.6,1.3),(0,2)),((-.6,1.3),(0,.7)),((.6,1.3),(0,.7)),((-.5,0),(0,.6)),((.5,0),(0,.6))]:
            beam('inlaid_rift_sigil',(x+a[0]*s,y,z+a[1]*s),(x+b[0]*s,y,z+b[1]*s),.055*s,'rune')

    def cloth(x,y,z,w,h,seed=1):
        rng=random.Random(seed);verts=[];cols=12;rows=8
        for row in range(rows+1):
            for col in range(cols+1):
                u=col/cols;v=row/rows
                tear=rng.uniform(.03,.22) if row==rows else 0
                verts.append((x+(u-.5)*w,y+math.sin(u*pi*4+v*2)*.12*v,z-v*h+tear))
        faces=[(r*(cols+1)+c,r*(cols+1)+c+1,(r+1)*(cols+1)+c+1,(r+1)*(cols+1)+c) for r in range(rows) for c in range(cols)]
        mesh('torn_patched_fabric',verts,faces,'cloth')
        for dx in [-w*.25,w*.16]:box('stitched_cloth_patch',(x+dx,y-.03,z-h*.65),(.35,.04,.48),'timber',.02)

    def shield(x,y,z,s=1):
        outline=[(-.6,.8),(.6,.8),(.7,.2),(.4,-.6),(0,-1),(-.4,-.6),(-.7,.2)]
        vertices=[(x+dx*s,y+dy,z+dz*s) for dy in [0,.16] for dx,dz in outline]
        faces=[tuple(range(6,-1,-1)),tuple(range(7,14))]+[(i,(i+1)%7,(i+1)%7+7,i+7) for i in range(7)]
        mesh('beaten_iron_trophy_shield',vertices,faces,'iron',.04)
        tube('shield_bound_edge',[(x+dx*s,y-.03,z+dz*s) for dx,dz in outline+[outline[0]]],.055,'trim')
        rune(x,y-.07,z-.55*s,.55*s)

    def blade(x,y,z):
        mesh('forged_spear_blade',[(x-.16,y,z),(x,y-.12,z+.7),(x+.16,y,z),(x,y+.12,z+.7),(x,y,z+1.15)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,3,2,1)],'trim')

    def wheel(x,y,z,r=.7):
        tube('iron_wheel_tyre',[(x,y+r*math.cos(i*pi/16),z+r*math.sin(i*pi/16)) for i in range(33)],.1)
        for i in range(12):
            a=i*pi/6;beam('carved_wheel_spoke',(x,y,z),(x,y+r*math.cos(a),z+r*math.sin(a)),.105,'timber')
        beam('wheel_hub',(x-.18,y,z),(x+.18,y,z),.3)

    def canopy(w,d,h):
        for x in [-w/2+.15,w/2-.15]:
            for y in [-d/2+.15,d/2-.15]:beam('stall_timber_post',(x,y,0),(x,y,h-.3),.17,'timber')
            beam('stall_cross_brace',(x,-d/2+.15,h-1.4),(x,d/2-.15,h-.4),.13,'timber')
        for i in range(12):
            a=-w/2+i*w/12;b=a+w/12
            mesh('sagging_canopy_panel',[(a,-d/2,h-.45),(b,-d/2,h-.45),(b,0,h-.15-.08*math.sin(i)),(a,0,h-.15-.08*math.sin(i)),(a,d/2,h),(b,d/2,h)],[(0,1,2,3),(3,2,5,4)],'cloth')
        for x in [-w/2+.12,w/2-.12]:beam('canopy_ridge_support',(x,-d/2,h-.45),(x,d/2,h),.12)
        cloth(0,-d/2,h-.45,w,.45,4)

    def counter(w,d=1.0,y=-.8):
        for x in [-w*.4,w*.4]:
            for dy in [-d*.4,d*.4]:box('counter_trestle',(x,y+dy,.7),(.18,.18,1.4),'timber')
        for i in range(5):box('worn_counter_plank',(0,y-d/2+(i+.5)*d/5,1.4),(w,d/5-.025,.16),'timber')

    def brazier(x=0,y=0,z=0):
        for h,w in [(.15,2),(.45,1.65)]:box('brazier_cut_base',(x,y,z+h),(w,w,.3),'basalt')
        turned('fluted_brazier_stem',x,y,z,[(.55,.52),(1,.30),(2.6,.30),(2.9,.72),(3.2,.95),(3.6,1),(3.65,.82),(3.25,.68)],'iron',12,False)
        for i in range(8):
            a=i*pi/4;beam('claw_crown',(x+.7*math.cos(a),y+.7*math.sin(a),z+3),(x+1.05*math.cos(a),y+1.05*math.sin(a),z+4.15),.14)
            turned('banked_ember',x+.48*math.cos(a),y+.48*math.sin(a),z+3.1,[(0,.22),(.3,.19),(.65,.03)],'glass',5)
        hoop('brazier_crown_ring',x,y,z+3.4,1)

    if kind=='war_brazier':brazier()
    elif kind=='war_standard':
        box('standard_stone_foot',(0,0,.22),(1.3,1.2,.44),'basalt')
        beam('black_iron_standard',(0,0,.4),(0,0,7.5),.17)
        beam('banner_crossbar',(-1.25,0,6.9),(1.25,0,6.9),.17)
        cloth(0,-.07,6.8,2.35,4.3,15);rune(0,-.23,3.6,1.1)
        for s in [-1,1]:tube('barbed_standard_finial',[(0,0,7),(s*.45,0,7.45),(s*.3,0,7.95)],.1)
    elif kind=='arms_rack':
        for x in [-1.9,1.9]:
            beam('rack_upright',(x,0,0),(x,0,3),.25,'timber')
            beam('rack_splayed_foot',(x,-1,0),(x,.9,.25),.25,'timber')
        for z in [.8,2.4]:beam('rack_crossbar',(-2,0,z),(2,0,z),.22,'timber')
        for i,x in enumerate([-1.6,-.8,0,.8,1.6]):
            beam('pike_shaft',(x,.1,.15),(x,.1,3.9),.075,'timber');blade(x,.1,3.2)
            if i%2==0:shield(x,-.25,1.3,.7)
        chest(0,.65,0,2,.6,.65)
    elif kind=='checkpoint':
        counter(4,1.7,0);chest(1.3,1,.05,1.6,1,.8)
        box('open_registry_ledger',(-.8,-.2,1.58),(1.15,.8,.13),'cloth')
        for x in [-1.22,-.98,-.74,-.50]:beam('ledger_ink_rules',(x,-.5,1.66),(x,.1,1.66),.025,'trim')
        turned('official_seal',.6,-.3,1.55,[(0,.18),(.13,.18),(.18,.06),(.35,.09)],'iron')
        beam('checkpoint_notice_post',(-2,1,0),(-2,1,2.8),.13);box('edict_notice',(-1.25,.98,2.1),(1.4,.15,1.1),'timber');rune(-1.25,.87,1.75,.35)
    elif kind in ['market_stall','apothecary','provision_stall']:
        p=PROFILES[kind];w,d,h=p['width'],p['depth'],p['height'];canopy(w-.24,d-.24,h-.1);counter(w-.4,1.05,-d/2+.65)
        if kind=='market_stall':
            for x in [-2,-.8,.6]:chest(x,.5,0,1.1,1.1,.9)
            for i in range(7):turned('rolled_trading_cloth',-2+i*.58,-1.1,1.52,[(0,.2),(.65,.2)],'cloth',10)
            shield(1.8,.5,2.3,.65);lantern(w/2-.55,-d/2+.65,3)
        elif kind=='apothecary':
            for z in [1.5,2.25,3]:box('apothecary_shelf',(0,1.25,z),(w-.4,.7,.12),'timber')
            for row in range(3):
                for col in range(8):
                    x=-1.8+col*.5;z=1.56+row*.75
                    turned('stoppered_tincture',x,1.25,z,[(0,.13),(.32,.16),(.40,.08),(.53,.06)],'rune' if col%3==0 else 'glass',8)
                    turned('vial_cork',x,1.25,z+.52,[(0,.07),(.07,.07)],'timber',8)
            turned('stone_mortar',.8,-1,1.5,[(0,.3),(.35,.5),(.40,.4),(.15,.2)],'basalt',12,False)
            beam('grinding_pestle',(.75,-1,1.6),(1.05,-1,2.25),.13,'trim')
        else:
            barrel(-1.6,.6,0,.8);barrel(1.5,.55,0,.95)
            beam('provision_hanging_rail',(-w/2+.27,.8,3.9),(w/2-.27,.8,3.9),.12)
            for x in [-w/2+.27,w/2-.27]:beam('hanging_rail_bracket',(x,d/2-.27,3.8),(x,.8,3.9),.1)
            for x in [-1.4,-.6,.2,1]:
                chest(x,-1,1.5,.65,.6,.25)
                for i in range(4):turned('market_root_bundle',x+(i%2)*.19-.1,-1+(i//2)*.15,1.8,[(0,.08),(.25,.12),(.38,.02)],'timber',7)
            for x in [-1.4,-.7,0,.7,1.4]:
                tube('hanging_food_cord',[(x,.8,3.9),(x,.8,3.1)],.03,'timber')
                turned('smoked_provision',x,.8,2.35,[(0,.08),(.35,.16),(.65,.14),(.75,.03)],'timber',8)
    elif kind in ['supply_cart','ore_cart']:
        for x in [-1.35,1.35]:
            for y in [-1,1]:wheel(x,y,.72,.66)
        for y in [-1,1]:beam('cart_axle',(-1.65,y,.72),(1.65,y,.72),.18)
        box('cart_floor',(0,0,.95),(2.55,3,.2),'timber')
        for x in [-1.25,1.25]:
            for z in [1.2,1.55,1.9]:box('cart_bound_planking',(x,0,z),(.14,3,.3),'timber' if kind=='supply_cart' else 'iron')
        for y in [-1.5,1.5]:box('cart_end',(0,y,1.5),(2.65,.15,1.25),'timber')
        if kind=='supply_cart':
            for x in [-.7,.7]:beam('haulage_shaft',(x,-1.5,.8),(x,-2.9,.4),.13,'timber')
            chest(-.55,.4,1.1,1.2,1.4,1);barrel(.65,.3,1.1,.65);cloth(0,-.4,2.45,2.3,1.1,9)
        else:
            for i in range(16):
                x=(i%4-.5)*.47-.5;y=(i//4-1.5)*.6
                turned('jagged_ore_load',x,y,1.1,[(0,.31),(.45,.38),(.85+.1*math.sin(i),.06)],'basalt' if i%3 else 'iron',5)
            for x in [-1.5,1.5]:beam('ore_rail_runner',(x,-2,0),(x,2,0),.12)
    elif kind=='barrel_stack':
        barrel(-.72,0);barrel(.72,.25);barrel(0,.1,1.42,.85)
        chest(1.1,-.75,0,.7,.7,.65)
    elif kind=='laundry_rig':
        for x in [-2.8,2.8]:
            beam('washing_line_post',(x,0,0),(x,0,4.5),.15,'timber')
            beam('post_knee',(x,-.8,0),(x,0,1.5),.12)
        tube('sagging_washline',[(-2.8,0,4.3),(-1.4,0,4.05),(0,0,3.85),(1.4,0,4.05),(2.8,0,4.3)],.04,'timber')
        for i,x in enumerate([-1.9,-.6,.8,2]):
            def line_height(px):return 3.85+min(abs(px),1.4)*.2/1.4+max(0,abs(px)-1.4)*.25/1.4
            top=min(line_height(x-.3),line_height(x+.3))-.04
            cloth(x,-.03,top,1 if i%2 else 1.25,1.3 if i%2 else 2,i+7)
            for dx in [-.3,.3]:box('clothes_peg',(x+dx,-.02,line_height(x+dx)),(.05,.10,.18),'timber')
        turned('wash_tub',-1,0,0,[(0,.55),(.6,.8),(.7,.75),(.2,.45)],'timber',16,False);hoop('wash_tub_hoop',-1,0,.5,.76)
    elif kind=='communal_hearth':
        for i in range(12):
            a=i*pi/6;turned('fire_circle_stone',math.cos(a),math.sin(a),0,[(0,.3),(.3,.35),(.45,.2)],'basalt',6)
        turned('coal_fire',0,0,.15,[(0,.6),(.18,.65),(.55,.1)],'glass',9)
        for i in range(3):
            a=i*2*pi/3;beam('kettle_tripod',(1.45*math.cos(a),1.45*math.sin(a),0),(0,0,3.5),.11)
        for z in [2.1,2.35,2.6,2.85,3.1]:ring('kettle_chain',0,0,z,.13)
        turned('communal_iron_kettle',0,0,.85,[(0,.45),(.2,.7),(.8,.85),(1,.65),(1,.55),(.2,.32)],'iron',20,False)
        for x in [-2.25,2.25]:
            box('hearth_bench',(x,0,.65),(.65,3.3,.2),'timber')
            for y in [-1.25,1.25]:box('bench_stump',(x,y,.3),(.5,.4,.6),'basalt')
    elif kind=='chain_winch':
        box('bolted_winch_bed',(0,0,.18),(4.4,3.3,.36),'timber')
        for x in [-1.4,1.4]:
            beam('winch_bearing_frame',(x,-1.3,.3),(x,0,2.8),.3);beam('winch_rear_brace',(x,1.3,.3),(x,0,2.8),.25)
        beam('winch_drum_axle',(-1.8,0,2),(1.8,0,2),.35)
        for x in [-1.25+i*.18 for i in range(15)]:
            tube('wound_haulage_rope',[(x,.75*math.cos(a*pi/12),2+.75*math.sin(a*pi/12)) for a in range(25)],.09,'timber')
        for x in [-1.55,1.55]:wheel(x,0,2,.95)
        beam('winch_crank',(1.8,0,2),(1.8,-1,2),.16);beam('crank_grip',(1.8,-1,2),(2.15,-1,2),.15,'timber')
    elif kind=='water_pump':
        box('pump_cut_foundation',(0,0,.2),(4.2,3.4,.4),'basalt')
        turned('riveted_pump_body',-.6,.3,.4,[(0,.7),(.5,.65),(3.6,.55),(4.2,.35),(4.5,.4)],'iron',16)
        for z in [1,2.5,4.2]:hoop('pump_flange',-.6,.3,z,.67)
        tube('bent_water_outlet',[(-.6,.3,4),(-.6,-.8,4),(.6,-.8,3.8),(.85,-.8,3.2)],.19)
        for x in [-1.7,1.7]:box('cistern_side',(x,-.5,.85),(.25,2,1.3),'basalt')
        for y in [-1.5,.5]:box('cistern_end',(0,y,.85),(3.4,.25,1.3),'basalt')
        box('dark_cistern_water',(0,-.5,.75),(3.1,1.75,.05),'slate',0)
        beam('pump_lever',(-.6,.3,4.8),(-.6,1.5,6),.16,'iron')
        wheel(.2,.4,2.7,.7)
    elif kind=='ritual_obelisk':
        for h,w in [(.2,3.8),(.65,3.2),(1.05,2.6)]:box('obelisk_cut_plinth',(0,0,h),(w,w,.35),'basalt')
        verts=[(x*w,y*d,z) for z,w,d in [(1.2,1,.8),(8.5,.75,.65),(10.7,0,0)] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        mesh('carved_oath_needle',verts,[(j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i) for j in range(2) for i in range(4)],'basalt',.05)
        for z,w in [(2,1),(5,.9),(8,.8)]:box('obelisk_iron_binding',(0,0,z),(w*2+.12,1.8,.22),'iron')
        rune(0,-.89,3.05,1.3)
        for x in [-1.3,1.3]:tube('obelisk_anchor_chain',[(x,0,.4),(x*.7,-.7,1.3),(x*.65,-.8,2.8)],.09)
    elif kind=='oath_monument':
        for i in range(3):box('monument_dais',(0,0,.25+i*.4),(6.8-i*.7,4.8-i*.5,.5),'basalt')
        for x in [-.75,.75]:
            box('statue_sabatons',(x,-.25,1.65),(.95,1.7,.65),'trim')
            beam('statue_greave',(x,0,1.9),(x*.85,0,5),.75,'trim')
        turned('statue_armored_torso',0,0,4.8,[(0,1),(.7,.85),(2.6,1.6),(3.4,1.05)],'basalt',8)
        for x in [-1.7,1.7]:
            turned('barbed_pauldron',x,0,7.9,[(0,.7),(.6,.9),(1.15,.2)],'trim',6)
            beam('statue_arm',(x,0,7.8),(x*.9,-.2,5.5),.65,'basalt')
            beam('shoulder_spike',(x,0,8.4),(x*1.5,0,9.4),.23,'iron')
        turned('sealed_horned_helm',0,0,8.3,[(0,.75),(.8,.9),(1.5,.7),(1.8,.25)],'trim',10)
        for s in [-1,1]:
            tube('swept_crown_horn',[(s*.6,0,9.7),(s*1.3,0,10.3),(s*1.6,.1,11.6),(s*1.2,0,12.8)],.18,'iron')
            beam('hooded_violet_eye',(s*.15,-.79,9.4),(s*.5,-.78,9.5),.06,'rune')
            tube('statue_binding',[(s*2.7,0,1.1),(s*1.9,-.8,3),(s*1.4,-1,5.5)],.13)
        for z in [5.4,6.3,7.2]:box('lamellar_statue_plate',(0,-.9,z),(1.6,.3,.65),'iron')
        rune(0,-1.1,5.6,.8);cloth(0,.9,8,3.8,6.5,43)
    elif kind=='war_table':
        counter(6.6,4,0)
        for x in [-2.7,2.7]:
            for y in [-1.7,1.7]:box('war_table_claw',(x,y,.65),(.5,.5,1.3),'iron')
        box('engraved_campaign_plate',(0,0,1.56),(5.6,3.3,.13),'basalt')
        for y in [-.9,0,.9]:
            for x in [-2,-.8,.5,1.8]:
                turned('campaign_keep_marker',x,y,1.65,[(0,.17),(.4,.12),(.7,.03)],'iron',5)
        for x in [-2.6,2.6]:
            turned('war_map_scroll',x,0,1.6,[(0,.16),(.8,.16)],'cloth',10)
        for y in [-2.4,2.4]:
            box('council_bench',(0,y,.7),(5.6,.6,.25),'timber')
            for x in [-2.1,2.1]:box('council_bench_leg',(x,y,.3),(.35,.45,.6),'iron')
    elif kind=='hanging_cage':
        box('cage_gallows_foot',(.9,.4,.18),(1.1,1.6,.36),'basalt')
        beam('cage_gallows_post',(.9,.4,.3),(.9,.4,6.1),.28)
        beam('cage_crossarm',(.9,.4,6),(-.6,.4,6),.25)
        beam('gallows_knee',(.9,.4,4.9),(-.5,.4,6),.15)
        for z in [4.9,5.2,5.5,5.8]:ring('hanging_cage_chain',-.45,.4,z,.16)
        turned('empty_cage_floor',-.45,0,1.7,[(0,1),(.15,1)],'iron',16)
        for z in [1.9,2.8,4,4.5]:hoop('cage_iron_band',-.45,0,z,1)
        for i in range(16):
            a=i*pi/8;beam('cage_vertical_bar',(-.45+math.cos(a),math.sin(a),1.8),(-.45+math.cos(a),math.sin(a),4.5),.075)
            beam('cage_crown_bar',(-.45+math.cos(a),math.sin(a),4.5),(-.45,0,4.9),.075)
    else:raise ValueError(kind)
