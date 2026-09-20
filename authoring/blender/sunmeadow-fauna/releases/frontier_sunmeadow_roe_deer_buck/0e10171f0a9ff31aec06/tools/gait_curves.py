"""A planted stance joins a continuous-velocity return arc without a foot snap."""
import math


def foot_trajectory(phase, stance, stride, lift):
    phase %= 1
    if phase < stance:
        return stride * (phase / stance - .5), 0.0
    t = (phase - stance) / (1 - stance)
    tangent = (1 - stance) / stance
    # Compact endpoint corrections retain the planted velocity without the
    # large airborne overshoot of one cubic Hermite span on a short stance.
    forward = .5-t*t*(3-2*t)+tangent*(t*(1-t)**24-(1-t)*t**24)
    return stride * forward, lift * math.sin(math.pi * t) ** 2
