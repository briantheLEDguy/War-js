"""Bounded adaptations of reviewed channels; these controls do not grant appearance approval."""
import math


def surface_variation():
    return dict(secondaryScale=1.83, secondaryAngle=.63, maskMetres=31, macroMetres=94,
                vergeMetres=7, minimumMix=.25, maximumMix=.65, macroMinimum=.76, channelRange=[.04,.24])


def validate_variation(row):
    limits = dict(secondaryScale=(1.2, 4), secondaryAngle=(-math.pi, math.pi), maskMetres=(12, 120),
                  macroMetres=(40, 250), vergeMetres=(2, 15), minimumMix=(0, .45),
                  maximumMix=(.5, .9), macroMinimum=(.65, 1))
    if set(row) != set(limits)|{'channelRange'} or any(not isinstance(row[k], (float, int)) or not math.isfinite(row[k])
        or not lo <= row[k] <= hi for k, (lo, hi) in limits.items()):
        raise ValueError('Invalid regional surface variation')
    bounds=row['channelRange']
    if not isinstance(bounds,list) or len(bounds)!=2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in bounds) or not 0<=bounds[0]<bounds[1]<=1:
        raise ValueError('Invalid reviewed variation channel range')


def rotated_uv(native_cm, metres, angle):
    """Match the native graph's source-X / negative-source-Z world axes, including seams."""
    if len(native_cm) != 3 or any(not math.isfinite(n) for n in native_cm) or not math.isfinite(metres) or metres <= 0 or not math.isfinite(angle):
        raise ValueError('Invalid surface coordinates')
    u, v = native_cm[1], -native_cm[0]
    return [(u * math.cos(angle) - v * math.sin(angle)) / (metres * 100),
            (u * math.sin(angle) + v * math.cos(angle)) / (metres * 100)]


def validate_substrate(row):
    controls = dict(tileMetres=(.5, 12), patchMetres=(16, 120), patchStrength=(0, .8), slopeStrength=(0, .8))
    if not isinstance(row, dict) or any(not isinstance(row.get(k), (int, float)) or not math.isfinite(row[k])
        or not lo <= row[k] <= hi for k, (lo, hi) in controls.items()):
        raise ValueError('Invalid substrate controls')
    for key in ('color', 'normal'):
        channel = row.get(key)
        if not isinstance(channel, dict) or not isinstance(channel.get('path'), str) or not channel['path']:
            raise ValueError('Missing reviewed substrate channel')
        fingerprint = channel.get('sha256', '')
        if len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
            raise ValueError('Missing substrate fingerprint')
    tint, limits = row.get('tint', []), row.get('maskRange', [])
    if len(tint) != 3 or any(not isinstance(n, (int, float)) or not math.isfinite(n) or not 0 <= n <= 3 for n in tint):
        raise ValueError('Invalid substrate tint')
    if len(limits) != 2 or any(not isinstance(n, (int, float)) or not math.isfinite(n) for n in limits) or not 0 <= limits[0] < limits[1] <= 1:
        raise ValueError('Invalid substrate mask')


def substrate_weight(row, mask, normal_z):
    """Reference mask for endpoint/transition checks; native graphs evaluate the same bounded recipe."""
    validate_substrate(row)
    if not all(math.isfinite(n) for n in (mask, normal_z)):
        raise ValueError('Invalid ground mask sample')
    low, high = row['maskRange']; t = min(1, max(0, (mask-low)/(high-low)))
    t = t*t*(3-2*t)
    slope = min(1, max(0, (.98-normal_z)/.18))
    return min(1, max(0, t*row['patchStrength']+slope*row['slopeStrength']))


def validate_shorelines(rows):
    if not isinstance(rows,list) or len(rows)>8:raise ValueError('Shoreline inventory is not bounded')
    for row in rows:
        if set(row)!=set(('x','z','waterY','radius')) or any(not math.isfinite(v) for v in row.values()) or max(abs(row['x']),abs(row['z']))>2500 or not -100<=row['waterY']<=250 or not 10<=row['radius']<=100:
            raise ValueError('Invalid cosmetic shoreline')


def shoreline_weight(row,x,z,y):
    validate_shorelines([row])
    if any(not math.isfinite(v) for v in (x,z,y)):raise ValueError('Invalid shore sample')
    radial=max(0,min(1,(row['radius']-math.sqrt((x-row['x'])**2+(z-row['z'])**2+(y-row['waterY'])**2))/12))
    vertical=max(0,1-abs(y-row['waterY'])/.8)
    return radial*vertical*vertical*(3-2*vertical)*.65


def channel_weight(row,value):
    """Rescale dark linear colour channels before using them as macro blend masks."""
    validate_variation(row)
    if not math.isfinite(value):raise ValueError('Invalid colour sample')
    low,high=row['channelRange'];t=max(0,min(1,(value-low)/(high-low)))
    return t*t*(3-2*t)
