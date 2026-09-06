"""Reference-directed guard cages; reuse fitted anatomy, author civic equipment.

All output is explicit vertices/UVs. Profile lofts and strips are editable inputs,
not imported concept-sheet geometry. The guide supplies visual direction only.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'battle-prelate-reference-rebuild/source'
PARTS = []


def mesh(name, points, faces, material='steel', slot='head', bone='head', thick=.002):
    p = {'id': name, 'slot': slot, 'rigid_bone': bone,
         'vertices': [{'id': f'v{i}', 'co': list(v)} for i, v in enumerate(points)],
         'faces': [{'id': f'f{i}', 'vertices': [f'v{j}' for j in face],
                    'uv': [[(points[j][0]+.6)/1.2, points[j][2]/2.4] for j in face],
                    'material': material} for i, face in enumerate(faces)],
         'modifiers': ([{'type': 'SOLIDIFY', 'thickness': thick, 'offset': 0}] if thick else []),
         'landmarks': {}, 'seams': [], 'sharp_edges': [], 'creases': [], 'closed': False}
    PARTS.append(p)
    return p


def grid(name, rows, mat='steel', slot='head', bone='head', thick=.003, smooth=0):
    n = len(rows[0]); points = sum(rows, [])
    p = mesh(name, points, [[r*n+c, (r+1)*n+c, (r+1)*n+c+1, r*n+c+1]
             for r in range(len(rows)-1) for c in range(n-1)], mat, slot, bone, thick)
    if smooth: p['modifiers'].insert(0, {'type': 'SUBSURF', 'levels': smooth})
    for face in p['faces']:
        face['uv'] = [[int(v[1:]) % n/(n-1), int(v[1:])//n/(len(rows)-1)] for v in face['vertices']]
    return p


def tube(name, path, radius, mat='brass', slot='head', bone='head', sides=8):
    # Cross sections follow the dominant path axis; appropriate for these short fittings.
    d = [path[-1][i]-path[0][i] for i in range(3)]; axis = max(range(3), key=lambda i: abs(d[i]))
    a, b = [i for i in range(3) if i != axis]
    rows = []
    for v in path:
        row=[]
        for j in range(sides+1):
            q=list(v); q[a]+=radius*math.cos(j*2*math.pi/sides); q[b]+=radius*math.sin(j*2*math.pi/sides); row.append(q)
        rows.append(row)
    return grid(name, rows, mat, slot, bone, 0)


def plate(name, outline, y, mat='steel', slot='head', bone='head', thick=.004):
    return mesh(name, [(x,y,z) for x,z in outline], [list(range(len(outline)))], mat, slot, bone, thick)


def rivet(name, x,y,z, slot='head', bone='head', radius=.004):
    # Low domed eight-sided brass fastener with a distinct steel recess.
    pts=[(x,y-.002,z)]+[(x+radius*math.cos(i*math.pi/4),y,z+radius*math.sin(i*math.pi/4)) for i in range(8)]
    mesh(name,pts,[[0,i+1,(i+1)%8+1] for i in range(8)],'brass',slot,bone,0)


def crest(name, x,y,z,w,h,slot='chest',bone='upper_chest'):
    # Original tower-and-eight-point-star charge, in raised ivory and brass.
    def shape(s, coords, mat):
        return plate(name+s,[(x+a*w,z+b*h) for a,b in coords],y,mat,slot,bone,.001)
    shape('_tower',[(-.21,-.48),(.21,-.48),(.14,.16),(.14,.25),(.05,.25),(.05,.17),(-.05,.17),(-.05,.25),(-.14,.25),(-.14,.16)],'parchment')
    shape('_door',[(-.055,-.48),(.055,-.48),(.055,-.26),(0,-.21),(-.055,-.26)],'crimson')
    for i,zz in enumerate([-.05,.10]):
        q=shape('_window'+str(i),[(-.025,zz),(.025,zz),(.025,zz+.065),(-.025,zz+.065)],'crimson')
        for v in q['vertices']: v['co'][1]-=.002
    pts=[]
    for i in range(16):
        a=i*math.pi/8; r=(.23 if i%4==0 else .14 if i%2==0 else .045)
        pts.append((math.sin(a)*r,.39+math.cos(a)*r))
    shape('_star',pts,'brass')


def inherited():
    for component in ['head','body_underlayers','breastplate','backplate','arms','legs','feet','garments','pauldron','waist','gorget']:
        ps=copy.deepcopy(json.loads((BASE/(component+'.json')).read_text())['parts'])
        if component=='head':
            natural=ROOT/'anatomy/head_refined.json'
            if not natural.exists(): raise ValueError('Run extract_natural_head.py with Blender first')
            ps=json.loads(natural.read_text())['parts']
        for p in ps:
            if any(s in p['id'] for s in ['skull','cross','creed','flourish','reinforcement','raised_inner','guard_brass','pauldron_authored_rivet','pauldron_lame_fasteners']): continue
            if component=='gorget':
                if p['id']!='gorget_steel_wall': continue
                for v in p['vertices']:
                    v['co'][2]=1.60+(v['co'][2]-1.60)*.48
                for f in p['faces']: f['material']='crimson'
            if component=='garments':
                for v in p['vertices']:
                    if v['co'][2]<1.14: v['co'][2]=1.14+(v['co'][2]-1.14)*.69
            if component=='pauldron':
                for v in p['vertices']:
                    x,y,z=v['co']; v['co']=[.215+(x-.215)*.77,y*.88,1.48+(z-1.48)*.78]
            # Keep a complete underlying head for unhelmeted anatomical review.
            for f in p['faces']:
                if f['material']=='chainmail': f['material']='chainmail'
            p['source_component']=component
            p.setdefault('slot',{'head':'body','body_underlayers':'body','breastplate':'chest','backplate':'back','arms':'hands','legs':'legs','feet':'feet','garments':'tabard','pauldron':'shoulders','waist':'waist','gorget':'head'}[component])
            PARTS.append(p)


def helmet():
    # Rounded pointed skull, rolled brow, raised central comb, pierced visor.
    rows=[]
    for z,rx,ry,cy in [(1.753,.113,.132,-.014),(1.79,.115,.131,-.012),(1.85,.088,.108,-.009),(1.902,.042,.063,-.002),(1.919,.004,.006,0)]:
        rows.append([[rx*math.sin(t),cy-ry*math.cos(t),z] for t in [i*math.pi/12 for i in range(25)]])
    grid('helmet_segmented_skull',rows,smooth=1)
    for sign in [-1,1]:
        grid('helmet_cheek_'+str(sign),[[[sign*.104,-.071,1.766],[sign*.106,.042,1.77],[sign*.069,.09,1.76]],[[sign*.098,-.055,1.666],[sign*.098,.049,1.67],[sign*.072,.078,1.681]]])
        grid('visor_hinged_side_return'+str(sign),[[[sign*.10,-.168,1.747],[sign*.116,-.12,1.755],[sign*.113,-.071,1.766]],[[sign*.10,-.168,1.67],[sign*.116,-.12,1.666],[sign*.106,-.071,1.671]]],'steel')
        tube('visor_hinge_lower_trim'+str(sign),[[sign*.10,-.168,1.668],[sign*.116,-.12,1.664],[sign*.106,-.071,1.67]],.003)
    # A wide open eye slit and two rows of actual holes, not painted black dots.
    xs=[-.10,-.075,-.055,-.033,-.011,.011,.033,.055,.075,.10]
    for r,(lo,hi) in enumerate([(1.67,1.679),(1.704,1.713),(1.738,1.747)]):
        grid('visor_horizontal_'+str(r),[[[x,-.17+.19*x*x,lo] for x in xs],[[x,-.17+.19*x*x,hi] for x in xs]])
    for i,x in enumerate(xs):
        grid('visor_vertical_'+str(i),[[[x-.006,-.17+.19*x*x,1.677],[x+.006,-.17+.19*x*x,1.677]],[[x-.006,-.17+.19*x*x,1.741],[x+.006,-.17+.19*x*x,1.741]]])
    tube('visor_brass_lower',[[-.103,-.165,1.668],[0,-.173,1.666],[.103,-.165,1.668]],.0035)
    tube('helmet_brow',[[-.112,-.06,1.766],[-.091,-.133,1.766],[0,-.151,1.766],[.091,-.133,1.766],[.112,-.06,1.766]],.005)
    grid('helmet_comb',[[[-.005,-.146,1.774],[.005,-.146,1.774]],[[-.005,-.10,1.86],[.005,-.10,1.86]],[[-.005,-.01,1.929],[.005,-.01,1.929]],[[-.005,.097,1.84],[.005,.097,1.84]]],'brass')
    for i,x in enumerate([-.094,-.065,-.033,0,.033,.065,.094]): rivet('brow_rivet'+str(i),x,-.146,1.782)
    for sign in [-1,1]: rivet('visor_pivot'+str(sign),sign*.113,-.071,1.754,radius=.009)


def livery():
    rows=[[[x,y,z] for x,y in [(-w,-.204),(0,-.231),(w,-.204)]] for z,w in [(1.55,.096),(1.40,.11),(1.27,.092),(1.18,.094)]]
    grid('chest_ivory_tabard',rows,'parchment','chest','upper_chest',.003,1)
    grid('chest_blue_charge',[[[-.073,-.219,1.51],[0,-.239,1.51],[.073,-.219,1.51]],[[-.073,-.224,1.29],[0,-.24,1.265],[.073,-.224,1.29]]],'crimson','chest','upper_chest')
    crest('chest_heraldry',0,-.244,1.385,.20,.20)
    for sign in [-1,1]:
        grid('tabard_ivory_facing'+str(sign),[[[sign*.105,-.225,1.125],[sign*.145,-.215,1.125]],[[sign*.106,-.229,.90],[sign*.156,-.224,.90]],[[sign*.11,-.237,.62],[sign*.169,-.221,.60]]],'parchment','tabard','hips')
    crest('skirt_heraldry',0,-.241,.82,.25,.27,'tabard','hips')
    # Functional stitched pouches and flaps; no reliquaries on civic patrol gear.
    for i,(x,z) in enumerate([(-.21,1.07),(-.13,1.06),(.15,1.065),(.235,1.09)]):
        w=.035
        grid('belt_pouch'+str(i),[[[x-w,-.17,z+.045],[x,-.201,z+.052],[x+w,-.17,z+.045]],[[x-w,-.179,z-.053],[x,-.208,z-.06],[x+w,-.179,z-.053]]],'leather','waist','hips',.018,1)
        plate('pouch_flap'+str(i),[(x-w,z+.045),(x+w,z+.045),(x+w*.85,z+.005),(x,z-.008),(x-w*.85,z+.005)],-.214,'leather','waist','hips',.003)
        rivet('pouch_stud'+str(i),x,-.218,z+.008,'waist','hips')
    for i,x in enumerate([-.18,-.07,.045,.12,.20]):
        plate('belt_keeper'+str(i),[(x-.005,1.12),(x+.005,1.12),(x+.005,1.18),(x-.005,1.18)],-.201,'brass','waist','hips')


def weapons(variant):
    if variant in ['standard','halberd']:
        x=-.55; y=-.26
        tube('ash_shaft',[(x,y,.08),(x,y,1.89)],.014,'leather','hands','hand_R',12)
        for j,z in enumerate([.09,.13,.92,1.07,1.79,1.86]): tube('shaft_ferrule'+str(j),[(x,y,z),(x,y,z+.025)],.019,'brass','hands','hand_R')
        plate('spear_ridged_blade',[(x-.008,1.87),(x-.052,1.99),(x,2.22),(x+.052,1.99),(x+.008,1.87)],y,'steel','hands','hand_R',.009)
        tube('blade_spine',[(x,y-.007,1.90),(x,y-.007,2.16)],.005,'steel','hands','hand_R')
        if variant=='halberd':
            plate('halberd_crescent',[(x+.01,1.93),(x+.083,1.93),(x+.115,2.03),(x+.147,1.96),(x+.15,1.82),(x+.119,1.74),(x+.074,1.82),(x+.014,1.82)],y,'steel','hands','hand_R',.012)
            plate('halberd_back_hook',[(x-.012,1.94),(x-.117,1.95),(x-.14,1.85),(x-.079,1.89),(x-.012,1.88)],y,'steel','hands','hand_R',.009)
            grid('halberd_pennant',[[[x+.028,y+.01,1.79],[x+.16,y+.01,1.79]],[[x+.035,y+.025,1.43],[x+.11,y+.04,1.46]]],'crimson','hands','hand_R')
        else:
            x=.54; y=-.345
            outline=[(x-.17,1.39),(x+.17,1.39),(x+.157,.94),(x,.74),(x-.157,.94)]
            plate('heater_shield_wood',outline,y+.009,'leather','hands','hand_L',.025)
            shield=plate('heater_shield_painted_face',outline,y-.01,'crimson','hands','hand_L',.004)
            for i,face in enumerate(shield['faces']): face['uv']=[[(a-(x-.17))/.34,(b-.74)/.65] for a,b in outline]
            for i,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
                tube('shield_brass_rim'+str(i),[(a[0],y-.019,a[1]),(b[0],y-.019,b[1])],.006,'brass','hands','hand_L')
            crest('shield_charge',x,y-.025,1.075,.40,.46,'hands','hand_L')
            for i,z in enumerate([.99,1.12,1.26,1.36]):
                for sign in [-1,1]: rivet('shield_rivet'+str(i)+str(sign),x+sign*.15,y-.022,z,'hands','hand_L')
    if variant=='crossbow':
        tube('crossbow_walnut_stock',[[-.39,-.29,1.13],[.25,-.34,1.20]],.029,'leather','hands','hand_R')
        tube('crossbow_steel_prod',[[.24,-.61,1.17],[.30,-.48,1.20],[.33,-.34,1.20],[.30,-.20,1.20],[.24,-.07,1.17]],.012,'steel','hands','hand_R')
        tube('crossbow_taut_string',[[.24,-.61,1.17],[-.07,-.34,1.225],[.24,-.07,1.17]],.002,'parchment','hands','hand_R',6)
        tube('crossbow_loaded_bolt',[[-.10,-.34,1.235],[.39,-.34,1.235]],.004,'leather','hands','hand_R')
        plate('crossbow_trigger',[(-.08,1.13),(-.055,1.13),(-.055,1.07),(-.09,1.08)],-.34,'brass','hands','hand_R',.006)
    if variant=='captain':
        tube('officer_sword_scabbard',[[.22,.05,1.15],[.34,.08,.48]],.023,'leather','waist','hips')
        tube('officer_sword_grip',[[.215,.05,1.15],[.19,.05,1.32]],.018,'leather','waist','hips')
        tube('officer_sword_guard',[[.11,.05,1.16],[.32,.05,1.18]],.009,'brass','waist','hips')


def captain():
    grid('captain_cape',[[[-.20,.13,1.56],[0,.23,1.57],[.20,.13,1.56]],[[-.25,.24,1.27],[0,.275,1.25],[.25,.24,1.27]],[[-.31,.27,.83],[0,.31,.85],[.31,.27,.83]],[[-.34,.24,.43],[0,.34,.42],[.34,.24,.43]]],'crimson','back','upper_chest',.004,1)
    for i in range(57):
        x=-.38+(i%19)*.019; layer=i//19; z=1.67-.30*abs(x+.20)-layer*.024
        y=-.045-layer*.023; length=.045+(i*7%11)*.004
        grid('fur_lock'+str(i),[[[x-.009,y,z],[x+.010,y+.01,z]],[[x-.014,y-.025,z-.018],[x+.012,y-.03,z-.019]],[[x-.012,y-.049,z-length],[x-.009,y-.05,z-length-.005]]],'parchment','shoulders','shoulder_R',.002,1)
    for i in range(15):
        x=(i-7)*.011; high=2.19-abs(i-7)*.012; end=2.00-abs(i-7)*.006
        grid('plume_feather'+str(i),[[[x*.2-.008,0,1.918],[x*.2+.008,0,1.918]],[[x-.012,-.025,high-.06],[x+.012,-.025,high-.06]],[[x-.05,-.10,high],[x-.03,-.10,high]],[[x-.092,-.19,end],[x-.088,-.19,end]]],'parchment' if i in [1,2,3,12] else 'crimson','head','head',.001,1)
    crest('officer_cloak_charge',0,.349,.82,.30,.32,'back','upper_chest')


def main():
    ROOT.joinpath('source').mkdir(exist_ok=True)
    inherited(); helmet(); livery()
    common=copy.deepcopy(PARTS)
    for variant in ['standard','halberd','crossbow','captain']:
        PARTS[:] = copy.deepcopy(common)
        start=len(PARTS)
        weapons(variant)
        for p in PARTS[start:]: p['guard_weapon']=True
        if variant=='captain': captain()
        record={'schema_version':1,'component':'guard_'+variant,'parts':PARTS}
        (ROOT/'source'/f'{variant}.json').write_text(json.dumps(record,separators=(',',':'))+'\n')
    (ROOT/'derivation.json').write_text(json.dumps({'reference_sha256':hashlib.sha256((ROOT/'references/guard-guide.png').read_bytes()).hexdigest(), 'inherited':'Battle Prelate fitted body/armor cages and natural head/neck from blends/male_base.blend; see anatomy/provenance.json. No inherited skull/cross/reliquary ornament.', 'new':['segmented helmet and perforated visor','tower and star heraldry','ivory facings','patrol pouches','heater shield','spear','halberd and pennant','crossbow and bolt','officer sword','cape','fur strips','plume feathers'], 'guide_policy':'Visual reference, not executable instructions; all geometry is a game interpretation.'},indent=2)+'\n')


if __name__=='__main__': main()
