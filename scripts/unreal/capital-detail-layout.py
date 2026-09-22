"""Deterministic street furniture candidates in the original city geography."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_geography import source_map, sampled_path, height


def layout():
    source = source_map()
    fixtures = []
    for path in source['paths']:
        samples = sampled_path(path, 24)
        for index, (a,b) in enumerate(zip(samples,samples[1:])):
            if index % 2:
                continue
            dx,dz = b['x']-a['x'],b['z']-a['z']
            length = math.hypot(dx,dz)
            if length < .1:
                continue
            for side in [-1,1]:
                offset = path['width']/2 + 1.5
                x,z = a['x']-dz/length*offset*side,a['z']+dx/length*offset*side
                if any(math.hypot(x-p['x'],z-p['z']) < 5 for p in source.get('npcs',[])):
                    continue
                # Do not decorate the castle stairs or elevated rampart routes.
                if z > 128:
                    continue
                fixtures.append({'id':f"{path['id']}_{index}_{side}",
                    'position':[z*100,x*100,height(x,z)*100+5],
                    'yaw':math.degrees(math.atan2(dx,dz)), 'side':side})
    # Shared intersections must not produce overlapping fixtures.
    result=[]
    for row in fixtures:
        if not any(math.dist(row['position'][:2],p['position'][:2]) < 800 for p in result):
            result.append(row)
    return result
