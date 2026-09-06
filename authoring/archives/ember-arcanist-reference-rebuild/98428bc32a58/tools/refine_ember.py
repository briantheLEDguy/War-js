"""Second reference pass: collar folds, worn hems, belt kit and staff fittings."""
import copy
import json
from pathlib import Path
from author_ember import patch, save

ROOT=Path(__file__).resolve().parents[1]


def read(name):return json.loads((ROOT/'source'/f'{name}.json').read_text())['parts']


def main():
    shoulders=[p for p in read('pauldron') if 'rivet' not in p['id'] and 'fastener' not in p['id']]
    save('pauldron',shoulders)
    collar=read('gorget')
    for p in collar:
        for v in p['vertices']:
            if p['id']=='folded_ash_cowl':v['co'][1]-=.018
            if p['id']=='rear_cowl_fold':
                v['co'][1]+=.060
                v['co'][2]+=.065
    for i,(dx,dy,dz) in enumerate([(0,-.032,.036),(.003,-.036,.004),(-.004,-.029,-.028)]):
        p=patch(f'cowl_fold_lip_{i}','''
-.133 -.107 1.581
-.122 -.123 1.565
-.069 -.177 1.571
-.067 -.192 1.555
.008 -.192 1.544
.014 -.204 1.527
.093 -.177 1.561
.101 -.187 1.547
.145 -.115 1.597
.152 -.127 1.580
''',2,'ash_cloth','head','upper_chest',.005,1)
        for v in p['vertices']:
            v['co']=[v['co'][0]+dx,v['co'][1]+dy,v['co'][2]+dz]
        collar.append(p)
    save('gorget',collar)
    # Pockets are shaped cloth/leather surfaces with individually stated depth.
    pouch=patch('left_belt_field_pouch','''
-.199 -.202 1.133
-.160 -.220 1.139
-.119 -.201 1.135
-.211 -.224 1.055
-.162 -.252 1.046
-.115 -.226 1.057
-.199 -.203 .994
-.163 -.228 .983
-.120 -.203 .996
''',3,'leather','waist','hips',.008,1)
    flap=patch('pouch_foldover_flap','''
-.201 -.209 1.139
-.162 -.225 1.146
-.119 -.208 1.141
-.205 -.238 1.097
-.160 -.256 1.086
-.115 -.236 1.099
''',3,'leather','waist','hips',.004,1)
    waist=read('waist')+[pouch,flap]
    for original in [pouch,flap]:
        p=copy.deepcopy(original);p['id']+='small'
        for v in p['vertices']:
            x,y,z=v['co'];v['co']=[x-.078,y+.045,1.11+(z-1.11)*.78]
        waist.append(p)
    save('waist',waist)
    # Weathered brass seal derived from the authored reliquary ring, without skull.
    med=json.loads((ROOT/'inherited/medallion.json').read_text())['parts']
    chosen=[p for p in med if p['id'] in {'reliquary_recessed_backing','reliquary_outer_rim','reliquary_pointed_rays'}]
    for p in chosen:
        p['id']='ember_'+p['id'];p.pop('instances',None);p.pop('transform',None)
        for v in p['vertices']:
            x,y,z=v['co'];v['co']=[x*.58,y*.58-.108,1.39+(z-1.39)*.58]
    # Use the measured source centroid rather than guessing ornament placement.
    xs=[v['co'][0] for p in chosen for v in p['vertices']]
    ys=[v['co'][1] for p in chosen for v in p['vertices']]
    zs=[v['co'][2] for p in chosen for v in p['vertices']]
    center=[(min(a)+max(a))/2 for a in [xs,ys,zs]]
    for p in chosen:
        for v in p['vertices']:
            v['co']=[v['co'][0]-center[0],v['co'][1]-center[1]-.215,v['co'][2]-center[2]+1.365]
    save('harness',read('harness')+chosen)
    staff=read('staff')
    band=staff[-1]
    for i,(scale,z) in enumerate([(.79,1.706),(.23,1.58),(.22,1.39),(.22,.82),(.19,.12)]):
        p=copy.deepcopy(band);p['id']=f'staff_binding_{i}'
        for v in p['vertices']:
            x,y,h=v['co'];v['co']=[x*scale,y*scale,h-1.85+z]
        staff.append(p)
    save('staff',staff)
    hair=read('hair')
    for p in hair:
        if p['id']=='auburn_scalp':
            for v in p['vertices']:
                x,y,z=v['co'];v['co']=[x*1.09,y*1.15,1.78+(z-1.78)*1.10+.008]
    save('hair',hair)
    # Local palette and inspectable wear paths. Painted wear is not scene lighting.
    path=ROOT/'textures/paint_strokes.json';paint=json.loads(path.read_text())
    for material,color in [('crimson',[62,19,16]),('leather',[29,19,14]),('parchment',[145,124,87]),('ash_cloth',[95,87,69]),('hair',[78,25,12]),('dark_steel',[35,33,30])]:
        paint['materials'][material]['base']['basecolor']=color
    size=paint['resolution']
    def points(coords):return [[int(x*(size-1)),int(y*(size-1))] for x,y in coords]
    paint['brushes']['ember_scorched_hem']={'kind':'polygons','shapes':[points([(0,.83),(.08,.88),(.19,.81),(.27,.91),(.40,.86),(.48,.94),(.61,.84),(.70,.91),(.80,.86),(.93,.92),(.999,.85),(.999,.999),(0,.999)])]}
    paint['brushes']['ember_long_creases']={'kind':'paths','shapes':[points(s) for s in [
        [(.08,.04),(.12,.23),(.09,.42),(.14,.61),(.11,.86)],[(.24,.01),(.23,.23),(.27,.43),(.22,.73),(.25,.96)],
        [(.43,.02),(.39,.25),(.44,.47),(.41,.72),(.46,.97)],[(.65,.02),(.61,.30),(.64,.48),(.60,.69),(.63,.96)],
        [(.82,.01),(.87,.28),(.83,.52),(.88,.76),(.84,.99)],[(.95,.04),(.91,.24),(.94,.52),(.90,.74),(.94,.96)]]]}
    for name in ['crimson','parchment']:
        layers=paint['materials'][name]['layers']
        layers[:]=[x for x in layers if not x['id'].startswith('ember_')]
        layers.extend([
          {'id':'ember_hem','brush':'ember_scorched_hem','opacity':215,'softness':12,'paint':{'basecolor':[18,14,11],'roughness':243,'height':105}},
          {'id':'ember_foldwear','brush':'ember_long_creases','opacity':115,'softness':3,'width':3,'paint':{'basecolor':[141,104,62] if name=='crimson' else [64,44,24],'height':145,'roughness':227}}])
    path.write_text(json.dumps(paint,indent=2)+'\n')
    skin_path=ROOT/'textures/skin_paint_strokes.json'
    skin=json.loads(skin_path.read_text())
    skin['layers']=[p for p in skin['layers'] if not p['id'].startswith('ember_')]
    skin['layers'].append({'id':'ember_auburn_stubble','kind':'polygons','opacity':190,'softness':12,
      'paint':{'basecolor':[48,27,19],'roughness':221},'shapes':[[[.50,.475],[.545,.50],[.59,.55],[.635,.59],[.647,.515],[.610,.401],[.54,.350],[.50,.352]],[[.500,.550],[.525,.540],[.545,.523],[.537,.510],[.50,.520]]]})
    skin_path.write_text(json.dumps(skin,indent=2)+'\n')


if __name__=='__main__':main()
