"""Bounded adaptations of reviewed channels; these controls do not grant appearance approval."""
import math


def surface_variation():
    return dict(secondaryScale=1.83, secondaryAngle=.63, maskMetres=31, macroMetres=94,
                vergeMetres=7, minimumMix=.25, maximumMix=.65, macroMinimum=.84)


def validate_variation(row):
    limits = dict(secondaryScale=(1.2, 4), secondaryAngle=(-math.pi, math.pi), maskMetres=(12, 120),
                  macroMetres=(40, 250), vergeMetres=(2, 15), minimumMix=(0, .45),
                  maximumMix=(.5, .9), macroMinimum=(.65, 1))
    if set(row) != set(limits) or any(not isinstance(row[k], (float, int)) or not math.isfinite(row[k])
        or not lo <= row[k] <= hi for k, (lo, hi) in limits.items()):
        raise ValueError('Invalid regional surface variation')


def rotated_uv(native_cm, metres, angle):
    """Match the native graph's source-X / negative-source-Z world axes, including seams."""
    if len(native_cm) != 3 or any(not math.isfinite(n) for n in native_cm) or not math.isfinite(metres) or metres <= 0 or not math.isfinite(angle):
        raise ValueError('Invalid surface coordinates')
    u, v = native_cm[1], -native_cm[0]
    return [(u * math.cos(angle) - v * math.sin(angle)) / (metres * 100),
            (u * math.sin(angle) + v * math.cos(angle)) / (metres * 100)]
