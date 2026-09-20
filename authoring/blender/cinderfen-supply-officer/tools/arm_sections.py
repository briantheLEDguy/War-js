"""Measure complete bone-local cross-sections consistently for source and export."""
import math
import numpy as np

def section(vertices, edges, bone, fraction):
    axis = (bone.tail - bone.head).normalized()
    origin = bone.head.lerp(bone.tail, fraction)
    x = bone.matrix.to_3x3().col[0].normalized()
    y = axis.cross(x).normalized()
    p, q = vertices[edges[:,0]], vertices[edges[:,1]]
    da, db = (p-np.array(origin))@np.array(axis), (q-np.array(origin))@np.array(axis)
    selected = da*db < 0
    hit = p[selected]+(q[selected]-p[selected])*(da[selected]/(da[selected]-db[selected]))[:,None]-np.array(origin)
    hit = hit[np.linalg.norm(hit,axis=1)<.16]
    points = np.stack((hit@np.array(x),hit@np.array(y)),axis=1)
    if len(points) == 0: return {'hits': 0}
    angles = sorted(math.atan2(y, x) for x, y in points)
    gaps = [b-a for a,b in zip(angles, angles[1:]+[angles[0]+math.tau])]
    ordered=points[np.argsort(np.arctan2(points[:,1],points[:,0]))]
    area=abs(np.sum(ordered[:,0]*np.roll(ordered[:,1],-1)-ordered[:,1]*np.roll(ordered[:,0],-1)))/2
    return {'hits': len(points), 'area':float(area), 'span': [float(np.ptp(points[:,i])) for i in range(2)],
            'largestAngularGapDegrees': math.degrees(max(gaps)),
            'radiusMin': min(math.hypot(*p) for p in points), 'radiusMax': max(math.hypot(*p) for p in points)}
