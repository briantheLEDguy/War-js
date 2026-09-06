"""Fit inherited explicit cages and serialize new reference-directed mesh patches.

No Blender primitives or randomized geometry. Drapery, hair and staff silhouettes
are recorded as literal control points; helpers only connect the written rows.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source'


def save(name, parts):
    (SOURCE / (name + '.json')).write_text(json.dumps({
        'schema_version': 1, 'component': name,
        'reference_notes': ['Ember Arcanist reference adaptation. Explicit authored cages; inherited topology is attributed in derivation.json.'],
        'parts': parts}, indent=2) + '\n')


def patch(name, rows, columns, material, slot, bone, thickness=.003, subdivision=1):
    points = [list(map(float, line.split())) for line in rows.strip().splitlines()]
    assert len(points) % columns == 0
    faces = []
    for row in range(len(points)//columns-1):
        for col in range(columns-1):
            ids = [row*columns+col, (row+1)*columns+col, (row+1)*columns+col+1, row*columns+col+1]
            faces.append({'id': f'f{len(faces)}', 'vertices': [f'v{i}' for i in ids],
                          'uv': [[i%columns/(columns-1), i//columns/(len(points)//columns-1)] for i in ids], 'material': material})
    return {'id': name, 'slot': slot, 'rigid_bone': bone,
            'vertices': [{'id': f'v{i}', 'co': p} for i,p in enumerate(points)], 'faces': faces,
            'modifiers': [{'type':'SUBSURF','levels':subdivision}, {'type':'SOLIDIFY','thickness':thickness,'offset':0}],
            'landmarks':{},'seams':[],'sharp_edges':[],'creases':[],'closed':False}


def remap(part, materials):
    for face in part['faces']:
        face['material'] = materials.get(face['material'], face['material'])


def main():
    # Freeze the accepted source cages once; reruns always derive from these bytes.
    inherited = ROOT/'inherited'
    inherited.mkdir(exist_ok=True)
    if not (inherited/'head.json').exists():
        for file in SOURCE.glob('*.json'):
            (inherited/file.name).write_bytes(file.read_bytes())
    def parts(name): return copy.deepcopy(json.loads((inherited/(name+'.json')).read_text())['parts'])
    # Source files intentionally replaced below, with previous bytes retained.
    allowed={'scene','head','body_underlayers','garments','arms','feet','legs','pauldron','tome','waist','relics','breastplate','backplate','gorget','hair','staff','harness'}
    for file in SOURCE.glob('*.json'):
        if file.stem not in allowed:
            file.unlink()
    body=parts('body_underlayers')
    for p in body: remap(p,{'chainmail':'ash_cloth','steel':'leather'})
    save('body_underlayers',body)
    head=parts('head')
    # Narrow the veteran's jaw and soften the brow while retaining the anatomical cage.
    for p in head:
        for v in p['vertices']:
            x,y,z=v['co']
            if p['id']=='head_skin' and z<1.74: v['co'][0]=x*.92
        remap(p,{'brow':'hair'})
    save('head',head)
    shoulders=[p for p in parts('pauldron') if not any(s in p['id'] for s in ('raised_inner','guard_brass','sun_cross','lower_lame'))]
    for p in shoulders:
        for v in p['vertices']:
            x,y,z=v['co'];v['co']=[.23+(x-.23)*.84,y*.90,1.48+(z-1.48)*.72]
        remap(p,{'steel':'dark_steel','chainmail':'ash_cloth'})
    save('pauldron',shoulders)
    arms=[p for p in parts('arms') if p['id'] not in {'elbow_couter_and_wing','rerebrace_shaped_shell'}]
    for p in arms:
        remap(p,{'steel':'leather','brass':'dark_steel','chainmail':'ash_cloth'})
    save('arms',arms)
    legs=[p for p in parts('legs') if p['id'] in {'thigh_steel_cuisse','greave_shaped_front_shell','thigh_padded_underlayer','knee_and_calf_padded_underlayer','greave_leather_closure_bands','greave_outer_closure_buckles'}]
    for p in legs: remap(p,{'steel':'leather','brass':'dark_steel','chainmail':'ash_cloth'})
    save('legs',legs)
    feet=[p for p in parts('feet') if p['id'] in {'boot_contoured_welt_and_sole','boot_shaped_leather_upper','sabaton_shaped_toecap','boot_heel_steel_counter','boot_outer_leather_buckle_strap','boot_outer_brass_buckle','boot_buckle_tongue'}]
    for p in feet: remap(p,{'steel':'leather','brass':'dark_steel'})
    save('feet',feet)
    chest=[p for p in parts('breastplate') if p['id']=='breastplate_shell']
    for p in chest:
        p['slot']='chest';p['rigid_bone']='upper_chest';remap(p,{'steel':'crimson'})
    save('breastplate',chest)
    back=parts('backplate')
    for p in back: remap(p,{'steel':'crimson','brass':'leather'})
    save('backplate',back)
    garments=parts('garments')
    # Extend the source folds into a nearly ankle-length split robe.
    for p in garments:
        if p['slot']=='tabard':
            for v in p['vertices']:
                x,y,z=v['co'];v['co']=[x*1.20,y*1.09,1.14+(z-1.14)*1.13]
    side=patch('left_split_robe', '''
.158 -.162 1.132
.208 -.083 1.135
.228 .009 1.132
.205 .100 1.135
.193 -.180 .94
.263 -.085 .935
.283 .022 .93
.249 .132 .94
.211 -.171 .66
.304 -.067 .65
.317 .039 .662
.279 .157 .67
.221 -.151 .37
.326 -.052 .34
.340 .049 .36
.292 .149 .385
.216 -.141 .265
.333 -.047 .237
.337 .044 .258
.288 .147 .294
''',4,'crimson','tabard','hips')
    side['modifiers'].insert(0,{'type':'MIRROR','axis':'X'})
    garments.append(side)
    # Two narrow parchment facing panels leave the red skirt visible between them.
    facing=patch('front_parchment_facing', '''
.068 -.206 1.137
.099 -.215 1.139
.127 -.205 1.135
.074 -.232 .94
.108 -.238 .947
.145 -.221 .941
.080 -.229 .71
.118 -.246 .698
.159 -.216 .704
.073 -.208 .46
.119 -.223 .451
.155 -.190 .468
.077 -.201 .273
.120 -.212 .251
.158 -.186 .283
''',3,'parchment','tabard','hips',.002)
    facing['modifiers'].insert(0,{'type':'MIRROR','axis':'X'})
    garments.append(facing)
    save('garments',garments)
    collar=patch('folded_ash_cowl', '''
-.115 -.030 1.604
-.080 -.103 1.616
0 -.131 1.613
.084 -.104 1.619
.119 -.028 1.606
-.158 -.044 1.557
-.103 -.161 1.566
.012 -.173 1.541
.121 -.148 1.559
.159 -.038 1.571
-.159 -.068 1.521
-.100 -.193 1.529
.025 -.195 1.494
.131 -.168 1.524
.170 -.063 1.545
-.161 -.073 1.487
-.093 -.196 1.469
.019 -.199 1.453
.133 -.162 1.493
.172 -.057 1.519
''',5,'ash_cloth','head','upper_chest',.006,2)
    rear=patch('rear_cowl_fold', '''
-.117 -.008 1.613
-.102 .086 1.62
0 .116 1.624
.102 .086 1.62
.117 -.008 1.613
-.151 .018 1.574
-.138 .123 1.557
.002 .158 1.534
.138 .123 1.557
.151 .018 1.574
-.165 .026 1.520
-.163 .130 1.478
0 .174 1.431
.163 .130 1.478
.165 .026 1.520
''',5,'ash_cloth','head','upper_chest',.005,2)
    save('gorget',[collar,rear])
    straps=patch('cross_body_leather_harness', '''
-.168 -.149 1.507
-.137 -.161 1.519
-.098 -.202 1.421
-.064 -.211 1.434
-.027 -.219 1.329
.009 -.219 1.348
.072 -.205 1.238
.109 -.201 1.256
.129 -.180 1.162
.163 -.174 1.178
''',2,'leather','chest','upper_chest',.008)
    straps['modifiers'].insert(0,{'type':'MIRROR','axis':'X'})
    save('harness',[straps])
    waist=[p for p in parts('waist') if p['id']=='heavy_relic_belt']
    save('waist',waist)
    tome=[p for p in parts('tome') if p['id'] not in {'tome_raised_aegis_cross','tome_center_reliquary_setting'}]
    save('tome',tome)
    relics=[p for p in parts('relics') if p['id'].startswith(('relic_upper_','relic_belt_','relic_four_'))]
    save('relics',relics)
    # Scalp cap and independently directed locks, deliberately asymmetric.
    hair=patch('auburn_scalp', '''
-.072 -.084 1.788
-.046 -.098 1.817
.006 -.103 1.823
.057 -.087 1.810
.082 -.054 1.786
-.095 -.025 1.814
-.057 -.043 1.862
.005 -.037 1.881
.066 -.029 1.860
.098 -.012 1.810
-.096 .036 1.788
-.058 .068 1.842
.003 .079 1.851
.064 .065 1.829
.095 .035 1.778
-.081 .073 1.734
-.047 .110 1.771
.004 .121 1.785
.059 .101 1.760
.080 .065 1.725
''',5,'hair','body','head',.007,2)
    locks=[hair]
    lock=patch('swept_forelock', '''
.050 -.067 1.850
.071 -.067 1.848
.086 -.060 1.835
.006 -.099 1.872
.026 -.110 1.878
.047 -.103 1.862
-.048 -.103 1.843
-.031 -.124 1.852
-.011 -.116 1.840
-.079 -.108 1.805
-.067 -.130 1.819
-.050 -.123 1.812
-.086 -.091 1.756
-.081 -.107 1.771
-.076 -.102 1.766
''',3,'hair','body','head',.006,2)
    locks.append(lock)
    for i,(dx,dy,dz,scale) in enumerate([(.022,.011,.005,.96),(.039,.027,-.005,.93),(-.015,.018,-.008,.96)]):
        p=copy.deepcopy(lock);p['id']=f'swept_lock_{i}'
        for v in p['vertices']:
            x,y,z=v['co'];v['co']=[x*scale+dx,y+dy,1.8+(z-1.8)*scale+dz]
        locks.append(p)
    sidehair=patch('temple_and_nape_lock', '''
.060 .009 1.842
.083 -.001 1.841
.095 .008 1.821
.086 .046 1.801
.106 .040 1.812
.114 .048 1.791
.082 .088 1.745
.107 .091 1.758
.113 .093 1.739
.091 .097 1.687
.112 .108 1.692
.112 .105 1.687
''',3,'hair','body','head',.005,2)
    sidehair['modifiers'].insert(0,{'type':'MIRROR','axis':'X'})
    locks.append(sidehair)
    save('hair',locks)
    # An octagonal hand-carved shaft with a tapered iron basket and ember stone.
    # The point coordinates are explicit cross sections, not primitive operators.
    staff=patch('staff_carved_shaft','''
-.012 -.010 .08
.012 -.010 .08
.017 .006 .08
0 .018 .08
-.017 .006 .08
-.012 -.010 .08
-.016 -.012 .72
.016 -.012 .72
.021 .008 .72
0 .022 .72
-.021 .008 .72
-.016 -.012 .72
-.015 -.013 1.14
.015 -.013 1.14
.020 .008 1.14
0 .021 1.14
-.020 .008 1.14
-.015 -.013 1.14
-.014 -.011 1.64
.014 -.011 1.64
.019 .007 1.64
0 .020 1.64
-.019 .007 1.64
-.014 -.011 1.64
''',6,'leather','weapon','weapon_root',.006,1)
    # The deliberately open longitudinal seam is welded before finishing below.
    def weld_wrap(p,cols):
        rem={f'v{i}':f'v{i-cols+1}' for i in range(cols-1,len(p['vertices']),cols)}
        for f in p['faces']:f['vertices']=[rem.get(v,v) for v in f['vertices']]
        p['vertices']=[v for v in p['vertices'] if v['id'] not in rem]
    weld_wrap(staff,6)
    basket=patch('brazier_iron_rib','''
-.014 -.018 1.59
.014 -.018 1.59
-.022 -.061 1.70
.022 -.061 1.70
-.020 -.111 1.83
.020 -.111 1.83
-.015 -.097 1.98
.015 -.097 1.98
-.006 -.060 2.10
.006 -.060 2.10
''',2,'dark_steel','weapon','weapon_root',.009,1)
    basket['instances']=[{'rotation_degrees':[0,0,a]} for a in [0,60,120,180,240,300]]
    crystal=patch('ember_heart','''
-.011 -.012 1.70
.012 -.012 1.70
.019 .008 1.70
0 .020 1.70
-.018 .008 1.70
-.011 -.012 1.70
-.049 -.048 1.81
.043 -.046 1.82
.067 .023 1.83
.006 .065 1.84
-.060 .024 1.82
-.049 -.048 1.81
-.022 -.027 1.94
.024 -.021 1.96
.029 .022 1.97
.003 .040 1.98
-.028 .019 1.95
-.022 -.027 1.94
-.005 -.002 2.055
.002 -.004 2.065
.006 .004 2.069
0 .009 2.07
-.006 .004 2.06
-.005 -.002 2.055
''',6,'ember','weapon','weapon_root',.005,0)
    weld_wrap(crystal,6)
    staffparts=[staff,basket,crystal]
    bands=patch('brazier_brass_band','''
-.072 -.072 1.850
.072 -.072 1.850
.102 .001 1.850
.072 .072 1.850
-.072 .072 1.850
-.102 .001 1.850
-.072 -.072 1.850
-.074 -.074 1.876
.074 -.074 1.876
.104 .001 1.876
.074 .074 1.876
-.074 .074 1.876
-.104 .001 1.876
-.074 -.074 1.876
''',7,'brass','weapon','weapon_root',.005,0)
    weld_wrap(bands,7);staffparts.append(bands)
    save('staff',staffparts)
    scene=json.loads((inherited/'scene.json').read_text())
    scene.update(revision='ember-001',stage='full_character',comparison_pose={'staff':{'location':[-.64,0,0]}})
    scene['acceptance']={'visual_status':'unreviewed','runtime_promotion':False}
    for camera in scene['cameras']:
        if camera['id'].startswith('full_'):
            camera['orthographic_scale']=2.6
            camera['target']=[0,0,1.04]
            camera['resolution']=[1000,1100]
    (SOURCE/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
    (ROOT/'derivation.json').write_text(json.dumps({'base':'Battle Prelate accepted explicit cage workflow','inherited_components':'Body anatomy, shoulder/arm/boot topology, robe folds, book and seals; fitted and rematerialed for the mage','new_components':['scarf','robe side panels','parchment facing','harness','hair','staff'],'reference':'references/ember-arcanist-reference.jpg','status':'source authored; pending rendered review'},indent=2)+'\n')


if __name__=='__main__':main()
