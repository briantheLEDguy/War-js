"""Finish original siege joinery, sewn covers and serviceable mechanical fittings.

All added forms follow explicit designer-authored station paths and sections.
Sweeps connect those construction stations; no primitive mesh is instantiated.
"""
from __future__ import annotations
import copy
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('frontier_base_source', ROOT/'tools'/'author_source.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
P, A, M = base.PARTS, base.ASSETS, base.MATERIALS


def mesh(name, vertices, faces, material, finish, note):
    return base.cage(name, '\n'.join(' '.join(str(v) for v in p) for p in vertices),
                     '\n'.join(' '.join(str(i) for i in f) for f in faces), material, finish, note)


def cord(name, stations, material='rope', finish=1):
    """Explicit 3D cord/rod path with individually fitted eight-sided sections."""
    section = [(1,0),(.707,.707),(0,1),(-.707,.707),(-1,0),(-.707,-.707),(0,-1),(.707,-.707)]
    vertices=[]
    for index,(x,y,z,r) in enumerate(stations):
        a=stations[max(0,index-1)]; b=stations[min(len(stations)-1,index+1)]
        tangent=[b[i]-a[i] for i in range(3)]
        length=math.sqrt(sum(v*v for v in tangent)); tangent=[v/length for v in tangent]
        axis=[0,1,0] if abs(tangent[1])<.8 else [1,0,0]
        u=[tangent[1]*axis[2]-tangent[2]*axis[1],tangent[2]*axis[0]-tangent[0]*axis[2],tangent[0]*axis[1]-tangent[1]*axis[0]]
        length=math.sqrt(sum(v*v for v in u));u=[v/length for v in u]
        v=[tangent[1]*u[2]-tangent[2]*u[1],tangent[2]*u[0]-tangent[0]*u[2],tangent[0]*u[1]-tangent[1]*u[0]]
        vertices.extend([[p+r*(a*u[j]+b*v[j]) for j,p in enumerate((x,y,z))] for a,b in section])
    closed=stations[0][:3]==stations[-1][:3]
    if closed:vertices=vertices[:-8]
    faces=[[i+k,i+(k+1)%8,i+8+(k+1)%8,i+8+k] for i in range(0,len(vertices)-8,8) for k in range(8)]
    if closed:faces += [[len(vertices)-8+k,len(vertices)-8+(k+1)%8,(k+1)%8,k] for k in range(8)]
    else:faces += [list(reversed(range(8))),list(range(len(vertices)-8,len(vertices)))]
    return mesh(name,vertices,faces,material,[{'type':'SUBSURF','levels':finish}],
                'Individually positioned construction stations retain the curved path, section thickness and fitted ends of this '+name.replace('_',' ')+'.')


def band(name, stations, half_width, material, thickness=.008):
    vertices=[(x,y-half_width,z) for x,y,z in stations]+[(x,y+half_width,z) for x,y,z in stations]
    n=len(stations)
    return mesh(name,vertices,[[i,i+1,i+n+1,i+n] for i in range(n-1)],material,
                [{'type':'SUBSURF','levels':2},{'type':'SOLIDIFY','thickness':thickness}],
                'Fitted continuous '+name.replace('_',' ')+' follows an explicit curved construction profile with bound edges and real material thickness.')


# Folded canvas seams follow the same source canopy stations, including its sag.
canopy=P['cloth_canopy']['vertices']
for row in (1,2,3):
    stations=[(x*1.012,y,z+.014) for x,y,z in canopy[row*9:row*9+9]]
    band(f'canvas_panel_seam_{row}',stations,.023,'canvas_binding',.012)
    for side in (-1,1):
        hem=(side*1.115,stations[0][1],1.57)
        cord(f'canvas_lashing_{row}_{side}',[(hem[0],hem[1],hem[2],.015),(side*1.17,hem[1]-.025,1.43,.014),
             (side*1.235,hem[1]-.055,1.31,.016),(side*1.26,hem[1]+.015,1.28,.016),
             (side*1.22,hem[1]+.055,1.33,.016),(side*1.175,hem[1]-.005,1.39,.014),
             (side*1.225,hem[1]-.045,1.28,.014),(side*1.22,hem[1]-.04,1.20,.012)])
        # Forged eyelet is a bent closed iron strip with visible central opening.
        cord(f'canvas_eyelet_{row}_{side}',[(side*1.12,hem[1]-.038,1.595,.011),(side*1.125,hem[1]-.048,1.555,.011),
             (side*1.13,hem[1]-.023,1.519,.011),(side*1.13,hem[1]+.023,1.519,.011),
             (side*1.125,hem[1]+.047,1.55,.011),(side*1.12,hem[1]+.035,1.59,.011),
             (side*1.12,hem[1]-.038,1.595,.011)],'burnished_brass',2)

# Cross-lacing along the two mantlet hide overlaps; each profile follows its bowed roof.
for row in (1,3):
    roof=P['ram_hide_roof']['vertices'][row*5:row*5+5]
    band(f'hide_overlap_{row}',[(x,y,z+.025) for x,y,z in roof],.044,'leather_binding',.023)
    for side in (-1,1):
        cord(f'mantlet_tie_{row}_{side}',[(side*1.37,roof[0][1],2.43,.020),(side*1.32,roof[0][1]-.03,2.31,.020),
             (side*1.10,roof[0][1]-.055,2.18,.019),(side*1.03,roof[0][1]+.065,2.14,.019),
             (side*1.15,roof[0][1]+.11,2.18,.020),(side*1.29,roof[0][1]+.012,2.27,.020),
             (side*1.12,roof[0][1]-.075,2.12,.017),(side*1.08,roof[0][1]-.081,2.04,.014)])

# A hand-sewn repair patch is deliberately one local repair, not a repeated all-over decal.
mesh('canvas_repair_patch',[(-1.089,.49,1.79),(-1.108,.74,1.78),(-1.098,.96,1.83),(-1.065,.93,2.05),(-1.057,.64,2.10),(-1.064,.47,2.04)],
     [[0,1,2,3,4,5]],'canvas_patch',[{'type':'SOLIDIFY','thickness':.009},{'type':'BEVEL','width':.008,'segments':2}],
     'Single hand-cut replacement canvas patch fitted to the left rear canopy panel, with folded seam allowance.')

cord('cauldron_rim_reinforcement',[(.02,-.594,1.074,.024),(.40,-.436,1.07,.024),(.584,-.02,1.074,.024),
     (.415,.413,1.08,.024),(0,.592,1.071,.024),(-.417,.414,1.075,.024),(-.591,0,1.075,.024),
     (-.42,-.412,1.074,.024),(.02,-.594,1.074,.024)],'worked_iron',2)
cord('cauldron_control_lever',[(.72,0,.82,.026),(.81,.13,.91,.028),(.86,.37,1.12,.027),(.87,.63,1.28,.025),
     (.875,.91,1.23,.036),(.875,1.12,1.19,.038)],'worked_iron',2)
cord('cauldron_mount_pin',[(0,-.095,0,.026),(0,-.052,0,.025),(0,.06,0,.025),(.025,.085,0,.020),(.054,.088,.008,.020)],'worked_iron',2)
mesh('cauldron_pouring_spout',[(-.185,-.50,1.095),(-.12,-.51,1.055),(0,-.51,1.035),(.12,-.51,1.055),(.185,-.50,1.095),
     (-.195,-.65,1.105),(-.12,-.66,1.045),(0,-.66,1.025),(.12,-.66,1.045),(.195,-.65,1.105),
     (-.145,-.85,1.08),(-.095,-.855,1.025),(0,-.86,1.005),(.095,-.855,1.025),(.145,-.85,1.08)],
     [[row*5+i,row*5+i+1,(row+1)*5+i+1,(row+1)*5+i] for row in range(2) for i in range(4)],
     'worked_iron',[{'type':'SUBSURF','levels':2},{'type':'SOLIDIFY','thickness':.027}],
     'Flared open pouring channel with a concave floor, raised sides and a lowered flow lip fitted to the original cauldron rim.')

# Folded tool straps and bent retaining hooks are real physical fittings.
band('spoon_leather_binding',[(-.42,.48,3.38),(-.24,.39,3.43),(0,.385,3.47),(.24,.39,3.43),(.42,.48,3.38)],.036,'leather_binding',.018)
cord('catapult_trigger_hook',[(0,1.15,.86,.043),(0,1.07,1.00,.039),(0,.94,1.06,.038),(0,.85,1.01,.034),(0,.855,.94,.030)],'worked_iron',2)
cord('catapult_winch_handle',[(.88,1.04,.92,.033),(1.11,1.04,.92,.033),(1.17,1.055,1.00,.032),
     (1.17,1.10,1.23,.032),(1.18,1.25,1.27,.047),(1.18,1.48,1.27,.047)],'worked_iron',2)
# This straight laid rope receives an animated length/orientation between the
# real drum anchor and throwing-arm attachment. Its two ends remain connected.
cord('catapult_haul_rope',[(0,0,0,.018),(.006,0,.2,.018),(-.003,.004,.4,.019),(.002,-.003,.6,.018),
     (-.005,0,.8,.018),(0,0,1,.018)],'rope',2)
spool_section=[(1,0),(.924,.383),(.707,.707),(.383,.924),(0,1),(-.383,.924),(-.707,.707),(-.924,.383),
    (-1,0),(-.924,-.383),(-.707,-.707),(-.383,-.924),(0,-1),(.383,-.924),(.707,-.707),(.924,-.383)]
spool_stations=[(-.88,.06),(-.80,.06),(-.78,.19),(-.72,.19),(-.69,.12),(.69,.12),(.72,.19),(.78,.19),(.80,.06),(.88,.06)]
spool_vertices=[(x,a*r+1.05,b*r+.98) for x,r in spool_stations for a,b in spool_section]
spool_faces=[[row*16+i,row*16+(i+1)%16,(row+1)*16+(i+1)%16,(row+1)*16+i] for row in range(len(spool_stations)-1) for i in range(16)]
spool_faces += [list(reversed(range(16))),list(range(len(spool_vertices)-16,len(spool_vertices)))]
mesh('catapult_winding_drum',spool_vertices,spool_faces,'worked_iron',[{'type':'BEVEL','width':.008,'segments':3}],
     'Shouldered winding drum with axle journals, raised rope-retaining cheeks and a recessed barrel between the fixed rear bearings.')
ratchet=[]
for x in (.77,.81):
    for tooth in range(14):
        for turn,r in ((0,.165),(.18,.205),(.76,.205),(.94,.165)):
            angle=(tooth+turn)/14*math.tau;ratchet.append((x,1.05+r*math.cos(angle),.98+r*math.sin(angle)))
n=56
mesh('catapult_ratchet',ratchet,[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]+[list(reversed(range(n))),list(range(n,n*2))],
     'worked_iron',[{'type':'BEVEL','width':.003,'segments':2}],
     'Fourteen asymmetric forged ratchet teeth hold the winding drum against the separate release pawl.')
cord('catapult_release_pawl',[(.815,1.28,1.15,.022),(.815,1.21,1.19,.022),(.815,1.15,1.175,.020),(.815,1.10,1.16,.017)],'worked_iron',2)
band('ram_head_binding',[(-.29,-1.82,1.44),(-.34,-1.82,1.63),(-.27,-1.82,1.88),(0,-1.82,1.92),
     (.27,-1.82,1.88),(.34,-1.82,1.63),(.29,-1.82,1.44)],.075,'worked_iron',.034)
for side in (-1,1):
    cord('ram_operator_grip_'+str(side),[(side*.29,-.50,1.64,.033),(side*.49,-.48,1.66,.033),
         (side*.53,-.36,1.66,.032),(side*.53,-.01,1.66,.032),(side*.49,.10,1.66,.033),(side*.29,.12,1.64,.033)],'worked_iron',2)

# Supply tags and removable standards give identity without changing the mechanics.
mesh('campaign_standard',[(-.21,0,0),(-.20,0,.51),(-.18,0,.67),(.18,0,.67),(.21,0,.49),(.22,0,.06),(.07,-.016,.11),(0,-.02,.03),(-.07,-.01,.10)],
     [[0,1,2,3,4,5,6,7,8]],'accord_standard',[{'type':'SOLIDIFY','thickness':.012},{'type':'BEVEL','width':.006,'segments':2}],
     'Original tailored split-foot logistics pennant with a sewn heading and shaped hanging folds; standard artwork is retained in the PBR source.')
mesh('ledger_cover',[(-.16,-.014,0),(.16,-.014,0),(.174,.014,.29),(-.15,.014,.31),(-.17,.045,0),(.15,.045,0),(.164,.064,.29),(-.16,.064,.31)],
     [[0,1,2,3],[4,7,6,5],[0,4,5,1],[3,2,6,7],[0,3,7,4],[1,5,6,2]],'leather_binding',base.FORGED,
     'Bound logistics ledger with a raised rounded spine, offset leather covers and a thick retained paper block.')

# The teamster sits on a cambered bench in front of the cargo, with a real
# footboard and mortised trestles. Its origin remains the wagon's ground origin.
bench_section=[(-.22,0),(-.19,.045),(-.08,.056),(.10,.05),(.20,.028),(.22,-.022),(.14,-.046),(-.17,-.043)]
bench_vertices=[(x,y-1.38,z+1.49+.012*(1-abs(x))) for x in (-.91,-.83,0,.83,.91) for y,z in bench_section]
bench_faces=[[row*8+i,row*8+(i+1)%8,(row+1)*8+(i+1)%8,(row+1)*8+i] for row in range(4) for i in range(8)]
bench_faces += [list(reversed(range(8))),list(range(32,40))]
mesh('wagon_teamster_bench',bench_vertices,bench_faces,'aged_oak',[{'type':'BEVEL','width':.009,'segments':3}],
     'Full-width planed teamster bench with a hand-shaped seat crown, softened thigh edge, end shoulders and mortised supports.')
mesh('wagon_seat_trestle',[(-.06,-1.57,1.09),(.06,-1.57,1.09),(.054,-1.48,1.46),(-.054,-1.48,1.46),
     (-.07,-1.15,1.08),(.07,-1.15,1.08),(.055,-1.28,1.46),(-.055,-1.28,1.46)],
     [[0,1,2,3],[4,7,6,5],[0,4,5,1],[3,2,6,7],[0,3,7,4],[1,5,6,2]],'aged_oak',base.BEVEL,
     'Splayed full-depth trestle receives the driver bench in its top mortise and bears onto the deck.')

M.update({
    'canvas_binding':{'basecolor':[113,118,107],'roughness':.90,'metallic':0,'paint':'cloth'},
    'canvas_patch':{'basecolor':[62,78,85],'roughness':.93,'metallic':0,'paint':'cloth'},
    'leather_binding':{'basecolor':[48,32,22],'roughness':.64,'metallic':0,'paint':'leather'},
    'worked_iron':{'basecolor':[53,57,59],'roughness':.55,'metallic':.88,'paint':'metal'},
    'accord_standard':{'basecolor':[29,55,73],'roughness':.91,'metallic':0,'paint':'cloth'},
    'rift_standard':{'basecolor':[70,29,27],'roughness':.91,'metallic':0,'paint':'cloth'},
})

def add(asset,part,**kwargs):
    A[asset]['instances'].append(base.inst(part,**kwargs))

for part in P:
    if part.startswith(('canvas_panel_seam_','canvas_lashing_','canvas_eyelet_')) or part=='canvas_repair_patch':
        add('frontier_supply_wagon',part)
    elif part.startswith(('hide_overlap_','mantlet_tie_')):
        add('frontier_battering_ram',part)
for part in ('cauldron_pouring_spout','cauldron_control_lever'):
    add('frontier_oil_cauldron',part)
for side in (-1,1):
    for z in (.29,.89,1.17):
        add('frontier_oil_cauldron','cauldron_mount_pin',location=(side*.65,.91,z))
for part in ('spoon_leather_binding','catapult_trigger_hook','catapult_winch_handle','catapult_winding_drum','catapult_ratchet','catapult_release_pawl'):
    add('frontier_field_catapult',part)
add('frontier_field_catapult','catapult_haul_rope',location=(0,1.05,.98))
for side in (-1,1):
    add('frontier_battering_ram','ram_operator_grip_'+str(side))
    bearing=base.inst('wheel_hub',location=(side*.82,1.05,.98),rotation=(0,0,90),scale=(.48,.48,.48))
    bearing['material_override']='worked_iron';A['frontier_field_catapult']['instances'].append(bearing)
add('frontier_battering_ram','ram_head_binding')
add('frontier_supply_wagon','wagon_teamster_bench')
for side in (-1,1):add('frontier_supply_wagon','wagon_seat_trestle',location=(side*.64,0,0))
for x in (-.65,-.39,-.13,.13,.39,.65):
    add('frontier_supply_wagon','deck_plank',location=(x,-1.91,.09),scale=(1,.15,1))
for asset,x,y,z in [('frontier_supply_wagon',1.26,.54,.92),('frontier_battering_ram',1.37,-1.44,1.26),('frontier_field_catapult',1.10,-.19,1.29)]:
    add(asset,'campaign_standard',location=(x,y,z),rotation=(0,0,-90),name='realm_standard')

# Hooped source wheels stay shared; planks use bounded grain coordinates instead
# of repeating the very same knot at every joint and fastener.
for asset in A.values():
    for index,instance in enumerate(asset['instances']):
        if instance.get('part') in ('cauldron_pouring_spout','cauldron_rim_reinforcement','cauldron_control_lever'):
            instance['rigid_group']='tipping_cauldron'
        elif instance.get('part')=='spoon_leather_binding': instance['rigid_group']='throwing_assembly'
        elif instance.get('part')=='ram_head_binding': instance['rigid_group']='ram_striker'
        elif instance.get('part','').startswith('ram_operator_grip_'): instance['rigid_group']='ram_striker'
        elif instance.get('part') in ('catapult_winding_drum','catapult_ratchet','catapult_winch_handle'): instance['rigid_group']='winding_drum'
        elif instance.get('part')=='catapult_haul_rope': instance['rigid_group']='haul_rope'
        elif instance.get('part')=='campaign_standard': instance['rigid_group']='realm_standard'
        if 'part' in instance and P[instance['part']]['material'] in ('aged_oak','fresh_oak','forged_iron','sooted_iron'):
            instance['uv_window']={'scale':[.73,.91],'offset':[[.025,.12,.20,.09][index%4],[.014,.056,.078][index%3]]}

A['frontier_battering_ram']['mechanical_pivots']={}
A['frontier_field_catapult']['mechanical_pivots']={'winding_drum':[0,1.05,.98],'haul_rope':[0,1.05,.98]}
for instance in A['frontier_battering_ram']['instances']:
    if instance.get('part')=='ram_suspension_sling':
        name='suspension_front' if instance['location'][1]<0 else 'suspension_rear'
        instance['rigid_group']=name
        A['frontier_battering_ram']['mechanical_pivots'][name]=[0,instance['location'][1],2.89]

A['frontier_supply_wagon']['hitch_contract']={'horse_asset':'frontier_draft_horse','horse_origin_z_up':[0,-3.75,0],
    'shaft_attachment_z_up':[[-.61,-3.47,.98],[.61,-3.47,.98]],'wheel_radius':.79,
    'driver_seat_z_up':[0,-1.38,1.54],'front_axis_gltf':'+Z'}
A['frontier_supply_wagon']['sockets']={'draft_horse_origin':[0,-3.75,0],'driver_seat':[0,-1.38,1.54],
    'driver_feet':[0,-1.91,1.16],'shaft_left':[-.61,-3.47,.98],'shaft_right':[.61,-3.47,.98]}
A['frontier_battering_ram']['sockets']={'operator_left':[-.71,-.15,.83],'operator_right':[.71,-.15,.83],
    'ram_impact_rest':[0,-2.75,1.63]}
A['frontier_field_catapult']['sockets']={'operator':[1.50,1.35,0],
    'projectile_rest':[0,.68,3.43],'reload_winch':[1.18,1.25,1.27]}
A['frontier_oil_cauldron']['sockets']={'operator_reference':[.90,1.55,0],'pour_lip_rest':[0,-.86,1.005]}
A['frontier_battering_ram']['socket_parents']={'ram_impact_rest':'ram_striker'}
A['frontier_field_catapult']['socket_parents']={'projectile_rest':'throwing_assembly','reload_winch':'winding_drum'}
A['frontier_oil_cauldron']['socket_parents']={'pour_lip_rest':'tipping_cauldron'}
A['frontier_supply_wagon']['limitations']=['Separate draft horse and actor seat pose are required for the complete caravan assembly.']
A['frontier_battering_ram']['limitations']=['Impact outcomes and operator interaction remain authoritative runtime systems.']
A['frontier_field_catapult']['limitations']=['Projectile launch and impact remain authoritative; use the parented projectile socket at the release event.']
A['frontier_battering_ram']['operator_positions_z_up']=[[-.71,-.15,.83],[.71,-.15,.83]]
A['frontier_field_catapult']['operator_positions_z_up']=[[1.50,1.35,0]]
A['frontier_oil_cauldron']['operator_positions_z_up']=[[.90,1.55,0]]

def main():
    source={'schema_version':2,'units':'metres','up':'Z','front':'-Y',
            'source_policy':'Original authored control cages, explicit construction sweeps and finite fitted-part placements. No primitive constructors.',
            'parts':P,'assets':A,'materials':M,'review_status':'unreviewed_source'}
    (ROOT/'source'/'frontier_collection.json').write_text(json.dumps(source,indent=2)+'\n')
    print(json.dumps({'parts':len(P),'assets':len(A),'construction_pass':'staged_for_visual_review'}))


if __name__=='__main__': main()
