"""Bastion's shared-boundary row-house planner. Coordinates are campaign metres.

The wall plane, not the mesh bounds or roof eave, owns the parcel boundary.
Adjacent lots reuse their exact boundary points, including mitred corner lots.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/dutch-bastion'
VERSION = 1
DISTRICTS = ('gateward', 'cinderbank', 'lantern_quays', 'bellfound', 'crownwatch')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def native_mesh(source):
    """Snap below visual tolerance and discard only collapsed overlay slivers.

    Unreal rejects nearly-zero cross products. The 0.1mm grid is 100 times
    stricter than the shared-wall acceptance limit and consistent for every lot.
    """
    mesh=dict(source);mesh['positions']=[[round(v,2) for v in p] for p in source['positions']]
    mesh['indices']=[];mesh['triangleMaterials']=[]
    for i in range(0,len(source['indices']),3):
        indices=source['indices'][i:i+3];a,b,c=[mesh['positions'][j] for j in indices]
        u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if max(abs(n) for n in cross)<=1e-4: continue
        mesh['indices'].extend(indices);mesh['triangleMaterials'].append(source['triangleMaterials'][i//3])
    return mesh


def lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(2)]


def area(points):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points, points[1:]+points[:1])) / 2


def inset(points, distance):
    """Intersect offset wall planes; never round a corner into an unfilled sliver."""
    if area(points) <= 0:
        raise ValueError('Block must be counterclockwise')
    lines = []
    for a,b in zip(points, points[1:]+points[:1]):
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        if length < .01: raise ValueError('Degenerate block edge')
        lines.append(([a[0]-dy/length*distance,a[1]+dx/length*distance], [dx,dy]))
    result = []
    for i,(b,v) in enumerate(lines):
        a,u = lines[i-1]
        cross = u[0]*v[1]-u[1]*v[0]
        if abs(cross) < 1e-8: raise ValueError('Collinear block corners must be simplified')
        t = ((b[0]-a[0])*v[1]-(b[1]-a[1])*v[0])/cross
        result.append([a[0]+t*u[0],a[1]+t*u[1]])
    return result


def frontage_widths(length, seed, opening=False):
    """Solve the final bay from the remaining length, avoiding accumulated gaps."""
    clear = 2.8 if opening else 0
    count = max(1, math.ceil((length-clear)/7.2))
    if count>1 and (length-clear)/count<4 and (length-clear)/(count-1)<=8:
        count-=1
    if (length-clear)/count < 4:
        raise ValueError('Frontage is too short for a house: '+str(length))
    weights = [1 + .12*math.sin((i+1)*2.37+seed) for i in range(count)]
    widths = [(length-clear)*v/sum(weights) for v in weights]
    if any(w < 4 or w > 8 for w in widths):
        widths = [(length-clear)/count]*count
    if opening: widths.insert(count//2,clear)
    widths[-1] = length-sum(widths[:-1])
    return widths, count//2 if opening else -1


def block(identity, district, boundary, depth=8, opening_edge=0):
    court = inset(boundary,depth)
    result = dict(id=identity,district=district,boundary=boundary,court=court,lots=[],openings=[])
    for edge,(a,b) in enumerate(zip(boundary,boundary[1:]+boundary[:1])):
        c,d = court[edge],court[(edge+1)%len(court)]
        length = math.dist(a,b)
        widths, opening = frontage_widths(length,edge+sum(map(ord,identity)),edge==opening_edge)
        splits = [0]
        for width in widths: splits.append(splits[-1]+width/length)
        splits[-1] = 1
        front = [lerp(a,b,t) for t in splits]
        rear = [lerp(c,d,t) for t in splits]
        if opening>=0:
            rear_length=math.dist(c,d)
            centre=(splits[opening]+splits[opening+1])/2
            half=1.4/rear_length
            if centre-half<=splits[opening-1] or centre+half>=splits[opening+2]:
                raise ValueError('Court passage requires fitted corner parcels')
            rear[opening]=lerp(c,d,centre-half)
            rear[opening+1]=lerp(c,d,centre+half)
        for bay,width in enumerate(widths):
            poly = [front[bay],front[bay+1],rear[bay+1],rear[bay]]
            key = f'{identity}_e{edge:02}_b{bay:02}'
            if bay == opening:
                result['openings'].append(dict(id=key,kind='court_passage',polygon=poly,width=width,edge=edge))
                continue
            number = edge*7+bay
            result['lots'].append(dict(id=key,actorId='bastion_dutch_'+key,polygon=poly,
                edge=edge,width=width,storeys=2+number%3,gable=('step','bell','triangle')[number%3],
                palette=number%5,publicInterior=None,entranceWidth=1.4,entranceHeight=2.45))
    return result


def pilot_plan():
    # The north frontage follows the craft canal. Different edge directions
    # exercise shared corner walls; the south passage opens onto the backcourt.
    b = block('cinderbank_canal_01','cinderbank',
              [[-111,-47],[-99,-53],[-77,-50],[-73,-27],[-77,0],[-95,1],[-110,-4]],7.2,1)
    venues = [('inn','The Copper Heron'),('cafe','Embercup Coffeehouse'),('shop','The Reed and Rivet')]
    # Public rooms deliberately occupy long, non-corner bays.
    candidates=[]
    for edge in (1,3,4):
        edge_lots=[lot for lot in b['lots'] if lot['edge']==edge and lot['width']>=5]
        candidates.append(edge_lots[len(edge_lots)//2])
    for lot,(kind,name) in zip(candidates,venues):
        lot['publicInterior'] = dict(kind=kind,name=name,service='atmosphere_only')
        lot['storeys'] = 3
    if sum(bool(l['publicInterior']) for l in b['lots']) != 3:
        raise ValueError('Pilot needs three different public venues')
    street = inset(b['boundary'],-3.0)
    source = ROOT/'public/assets/maps/aegis_capital.json'
    plan = dict(schemaVersion=VERSION,zone='aegis_capital',units='campaign_metres',stage='representative_block',
        sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),blocks=[b],
        streets=[dict(id='cinderbank_canal_walk',width=4.5,points=street+[street[0]])],
        acceptance=dict(geometry=False,visual=False,traversal=False,citywide=False,release=False))
    plan['signature'] = digest({k:v for k,v in plan.items() if k not in ('signature','acceptance')})
    validate(plan)
    return plan


def validate(plan):
    if plan['zone'] != 'aegis_capital': raise ValueError('Bastion only')
    if 'signature' in plan and plan['signature'] != digest({k:v for k,v in plan.items() if k not in ('signature','acceptance')}):
        raise ValueError('Plan fingerprint changed')
    ids = []
    for b in plan['blocks']:
        ids.append(b['id'])
        if b['district'] not in DISTRICTS or area(b['boundary']) <= 0 or area(b['court']) <= 0:
            raise ValueError('Invalid block or court')
        rings = b['lots']+b['openings']
        for row in rings:
            ids.append(row['id'])
            if area(row['polygon']) <= 0: raise ValueError('Inverted lot: '+row['id'])
        for row in b['lots']:
            if not 4 <= row['width'] <= 8: raise ValueError('House frontage outside 4–8 metres')
        for row in b['openings']:
            if row['kind']!='court_passage' or row['width']<2: raise ValueError('Passage too narrow')
        for edge,(a,z) in enumerate(zip(b['boundary'],b['boundary'][1:]+b['boundary'][:1])):
            rows = sorted((r for r in rings if r['edge']==edge),key=lambda r:math.dist(a,r['polygon'][0]))
            if not rows or math.dist(rows[0]['polygon'][0],a)>1e-7 or math.dist(rows[-1]['polygon'][1],z)>1e-7:
                raise ValueError('Unfilled frontage endpoint')
            for left,right in zip(rows,rows[1:]):
                if left['polygon'][1] != right['polygon'][0] or left['polygon'][2] != right['polygon'][3]:
                    raise ValueError('Party-wall seam: '+left['id'])
            following=[r for r in rings if r['edge']==(edge+1)%len(b['boundary'])]
            first=min(following,key=lambda r:math.dist(z,r['polygon'][0]))
            if rows[-1]['polygon'][2]!=first['polygon'][3]: raise ValueError('Corner party-wall seam')
        expected = area(b['boundary'])-area(b['court'])
        if abs(sum(area(r['polygon']) for r in rings)-expected)>1e-6:
            raise ValueError('Ring area does not close')
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate stable identity')
    return True


def write_plan():
    plan = pilot_plan()
    OUT.mkdir(parents=True,exist_ok=True)
    target = OUT/'pilot-plan.json'
    content = json.dumps(plan,indent=2)+'\n'
    if target.exists() and target.read_text()!=content:
        previous=json.loads(target.read_text());validate(previous)
        archive=OUT/'plans';archive.mkdir(exist_ok=True)
        saved=archive/(previous['signature']+'.json')
        if saved.exists() and saved.read_text()!=target.read_text(): raise RuntimeError('Archived plan changed')
        saved.write_text(target.read_text())
    target.write_text(content)
    print(f"{len(plan['blocks'][0]['lots'])} attached houses; 3 public venues; signature {plan['signature']}")


if __name__ == '__main__': write_plan()
