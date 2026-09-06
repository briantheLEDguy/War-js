"""Literal tailoring edits and a small field badge for the secondary armor set."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / 'battle-prelate-reference-rebuild'

FRONT = [
(-.151,-.170,1.130),(-.107,-.187,1.136),(-.068,-.168,1.140),(-.026,-.191,1.134),(.018,-.169,1.139),(.067,-.188,1.135),(.116,-.174,1.137),(.151,-.174,1.131),
(-.153,-.181,1.053),(-.108,-.207,1.052),(-.066,-.177,1.050),(-.025,-.205,1.045),(.020,-.181,1.056),(.071,-.211,1.050),(.118,-.189,1.045),(.154,-.179,1.050),
(-.156,-.180,.936),(-.110,-.207,.933),(-.066,-.180,.931),(-.023,-.207,.933),(.022,-.183,.936),(.072,-.209,.934),(.119,-.191,.930),(.154,-.178,.934),
(-.159,-.174,.823),(-.112,-.199,.822),(-.066,-.179,.819),(-.021,-.201,.821),(.025,-.175,.820),(.074,-.203,.822),(.120,-.183,.824),(.155,-.168,.826),
(-.158,-.165,.705),(-.112,-.190,.704),(-.065,-.169,.702),(-.019,-.193,.700),(.028,-.167,.700),(.076,-.194,.703),(.120,-.174,.706),(.154,-.161,.708),
(-.157,-.164,.677),(-.112,-.188,.676),(-.065,-.167,.674),(-.018,-.191,.672),(.030,-.165,.672),(.077,-.192,.675),(.119,-.172,.678),(.153,-.159,.680),
]
REAR = [
(-.220,.101,1.167),(-.162,.133,1.166),(-.092,.139,1.163),(0,.142,1.160),(.085,.147,1.162),(.161,.127,1.165),(.219,.104,1.168),
(-.227,.107,1.035),(-.166,.162,1.038),(-.091,.156,1.032),(.003,.168,1.030),(.092,.154,1.032),(.170,.163,1.038),(.230,.108,1.041),
(-.230,.108,.888),(-.169,.176,.885),(-.090,.160,.882),(.006,.180,.880),(.098,.159,.887),(.176,.174,.894),(.234,.105,.899),
(-.232,.108,.722),(-.169,.183,.718),(-.089,.161,.714),(.009,.189,.713),(.102,.157,.720),(.179,.183,.726),(.236,.103,.730),
(-.229,.106,.655),(-.167,.180,.649),(-.087,.158,.645),(.012,.187,.645),(.106,.155,.650),(.180,.179,.657),(.235,.101,.662),
]
TASSET = [
(.110,-.137,1.153),(.165,-.129,1.161),(.211,-.098,1.165),(.241,-.051,1.164),
(.119,-.149,1.108),(.174,-.138,1.115),(.224,-.100,1.120),(.250,-.044,1.119),
(.128,-.153,1.055),(.181,-.151,1.059),(.233,-.106,1.067),(.257,-.039,1.078),
(.131,-.149,1.022),(.185,-.143,1.019),(.238,-.100,1.032),(.260,-.032,1.063),
]

def load(name):
    return json.loads((ORIGINAL / 'source' / (name + '.json')).read_text())

def save(name, data):
    data['derivation'] = {'source': str(ORIGINAL / 'source' / (name + '.json')),
        'sha256': hashlib.sha256((ORIGINAL / 'source' / (name + '.json')).read_bytes()).hexdigest(),
        'method': 'Deliberately specified replacement coordinates or retained approved control records; no shape generator.'}
    (ROOT / 'source' / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

def replace_coordinates(part, coordinates):
    assert len(part['vertices']) == len(coordinates)
    for vertex, coordinate in zip(part['vertices'], coordinates):
        vertex['co'] = list(coordinate)

def patch(name, coordinates, faces, material, slot, bone, thickness):
    return {'id': name, 'slot': slot, 'rigid_bone': bone,
        'vertices': [{'id': f'v{i:03}', 'co': list(p)} for i,p in enumerate(coordinates)],
        'faces': [{'id': f'f{i:03}', 'vertices': [f'v{j:03}' for j in face],
            'material': material, 'uv': [[coordinates[j][0] * 4 + .5, coordinates[j][2] * 4 - 4] for j in face]} for i,face in enumerate(faces)],
        'modifiers': [{'type':'SOLIDIFY','thickness':thickness,'offset':0}, {'type':'BEVEL','width':.001,'segments':2}],
        'closed': False, 'seams': [], 'sharp_edges': [], 'creases': [], 'landmarks': {},
        'transform': {'location':[0,0,0],'rotation_degrees':[0,0,0],'scale':[1,1,1]}}

garments = load('garments')
replace_coordinates(garments['parts'][0], FRONT)
replace_coordinates(garments['parts'][1], REAR)
garments['reference_notes'] = ['Short square-cut russet front and rear skirt, with retained authored folds and a practical plain hem. The padded body-owned abdominal layer is unchanged.']
save('garments', garments)

waist = load('waist')
waist['parts'] = waist['parts'][:2]
top_z = [1.193,1.197,1.201,1.209,1.208,1.205,1.200,1.198]
bottom_z = [1.147,1.151,1.155,1.163,1.162,1.160,1.155,1.152]
for vertex,z in zip(waist['parts'][0]['vertices'],top_z+bottom_z): vertex['co'][2]=z
replace_coordinates(waist['parts'][1], TASSET)
for face in waist['parts'][1]['faces']: face['material']='leather'
waist['parts'][1]['modifiers'] = [{'type':'MIRROR','axis':'X'}, {'type':'SUBSURF','levels':1}, {'type':'SOLIDIFY','thickness':.004,'offset':0}]
waist['parts'].append(patch('novitiate_plain_iron_buckle',
    [(-.027,-.178,1.195),(.027,-.178,1.195),(.027,-.185,1.145),(-.027,-.185,1.145),(-.019,-.180,1.188),(.019,-.180,1.188),(.019,-.184,1.152),(-.019,-.184,1.152)],
    [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'dark_steel','waist','hips',.004))
waist['parts'].append(patch('novitiate_buckle_tongue',
    [(-.002,-.187,1.173),(.024,-.187,1.173),(.024,-.187,1.168),(-.002,-.187,1.168)],[(0,1,2,3)],'steel','waist','hips',.003))
waist['reference_notes'] = ['Narrow utility belt, a small iron buckle and paired short leather hip flaps. All reliquaries, sacred tome and ornamental tasset borders are omitted.']
save('waist', waist)

badge = patch('novitiate_small_faith_badge',
    [(-.005,-.1901,1.443),(.005,-.1901,1.443),(.005,-.1933,1.425),(.021,-.1918,1.425),(.021,-.19235,1.416),(.005,-.1938,1.416),(.005,-.19265,1.392),(-.005,-.19265,1.392),(-.005,-.1938,1.416),(-.021,-.19235,1.416),(-.021,-.1918,1.425),(-.005,-.1933,1.425)],
    [(0,1,2,11),(11,2,5,8),(8,5,6,7),(2,3,4,5),(9,8,11,10)],'brass','chest','upper_chest',.002)
(ROOT/'source/faith_badge.json').write_text(json.dumps({'schema_version':1,'component':'faith_badge','reference_notes':['One small plain brass cross preserves class identity at a novice rank. Explicit surface patch; no surrounding medallion or skull ornament.'],'parts':[badge]},indent=2)+'\n')
for name in ['medallion.json','tome.json','relics.json','repeated_reliquaries.json']:
    (ROOT/'source'/name).unlink(missing_ok=True)
(ROOT/'review/core_design.json').write_text(json.dumps({'retained_shared_body_part':'padded_abdominal_doublet','front_hem_m':[.672,.680],'rear_hem_m':[.645,.662],'removed_components':['medallion','tome','relics','repeated_reliquaries'],'new_patches':['novitiate_plain_iron_buckle','novitiate_buckle_tongue','novitiate_small_faith_badge']},indent=2)+'\n')
