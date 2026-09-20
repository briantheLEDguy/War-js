"""Bounded caudal underside lift when a femur reaches peak forward flexion."""
import numpy as np
from joint_correctives import smoothstep


def hamstring_displacement(rest, scale, carrier_rotation, flexions):
    points = np.asarray(rest)/scale
    left = smoothstep(-.08, .08, points[:, 0])
    tuck = left*smoothstep(.565, .62, -flexions[1])+(1-left)*smoothstep(.565, .62, -flexions[-1])
    support = smoothstep(.20, .42, points[:, 1])*(1-smoothstep(.45, .62, points[:, 2]))*smoothstep(.30, .41, points[:, 2])
    # The lower hamstring curves upward toward the rear. The complete upper
    # pelvis and distal limbs remain outside this pose-only field.
    lift = .065*support*tuck*scale
    return lift[:, None]*np.asarray(carrier_rotation)[:, 2]
