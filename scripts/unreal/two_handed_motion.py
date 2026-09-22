"""Shared interpolation for authored heavy-weapon paths, in Blender metres.

Interpolate pitch as an angle, not a normalized direction chord. Antipodal
direction chords turn a back-to-front swing into an unintended sideways sweep.
"""
import math


def curve(keys, time):
    """Shape-preserving cubic; continuous velocity through transit keys."""
    if time <= keys[0][0]: return tuple(keys[0][1])
    if time >= keys[-1][0]: return tuple(keys[-1][1])
    def slope(index, component):
        if index in (0, len(keys)-1): return 0.
        before=(keys[index][1][component]-keys[index-1][1][component])/(keys[index][0]-keys[index-1][0])
        after=(keys[index+1][1][component]-keys[index][1][component])/(keys[index+1][0]-keys[index][0])
        if before*after <= 0: return 0.
        return 2*before*after/(before+after)
    for index, ((start,a),(end,b)) in enumerate(zip(keys,keys[1:])):
        if time > end: continue
        span=end-start
        u=(time-start)/span
        return tuple((2*u**3-3*u*u+1)*a[c]+(-2*u**3+3*u*u)*b[c]
                     +(u**3-2*u*u+u)*span*slope(index,c)
                     +(u**3-u*u)*span*slope(index+1,c) for c in range(len(a)))


def shaft_axis(pitch, lateral):
    plane=math.sqrt(1-lateral*lateral)
    return (lateral, math.sin(pitch)*plane, math.cos(pitch)*plane)
