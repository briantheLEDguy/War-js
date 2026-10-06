"""Stepped wing ornament hierarchy, pending integration and native review.

Structural bay positions and terrace masses remain the caller's responsibility.
The cornice dimensions are measured after the existing upper-height transform.
"""
import math

PRESERVED_Z_CM = 9000
CORNICE_DEPTH_CM = 80
CORNICE_PROJECTION_CM = 30
WINDOW_HEAD_GAP_CM = 30


def wing_hierarchy(x0, x1, base, top, upper_factor):
    if not all(math.isfinite(v) for v in (x0, x1, base, top, upper_factor)):
        raise ValueError('Finite wing dimensions are required')
    if x1 <= x0 or top <= base or not 0 < upper_factor <= 1:
        raise ValueError('Ordered wing bounds and a positive compression are required')
    final_z = lambda z: z if z <= PRESERVED_Z_CM else PRESERVED_Z_CM+(z-PRESERVED_Z_CM)*upper_factor
    source_z = lambda z: z if z <= PRESERVED_Z_CM else PRESERVED_Z_CM+(z-PRESERVED_Z_CM)/upper_factor
    final_top = final_z(top)
    cornice_top = final_top-5
    cornice_bottom = cornice_top-CORNICE_DEPTH_CM
    if cornice_bottom <= PRESERVED_Z_CM:
        raise ValueError('The wing cornice must remain above the preserved precinct')
    window_base = base+350
    # The extruded pointed reveal extends 1.7 times its 65 cm thickness above
    # the nominal opening. Reserve that actual crown before placing the band.
    reveal_crown = 65*1.7
    original_height = min(1750, top-base-450)
    window_height = min(original_height,
        source_z(cornice_bottom-WINDOW_HEAD_GAP_CM)-window_base-reveal_crown)
    if window_height < 600:
        raise ValueError('Cornice would collapse the existing Gothic window bay')
    bays = list(range(x0+360, x1-250, 560))
    rods = [i for i in range(len(bays)) if i % 2 == 0 or i == len(bays)-1]
    pinnacles = [i for i in range(len(bays)) if i % 3 == 0 or i == len(bays)-1]
    return dict(version=1, bayPositionsCm=bays, rodBayIndices=rods,
        pinnacleBayIndices=pinnacles, windowBaseCm=window_base,
        windowHeightCm=window_height,
        finalWindowRevealTopCm=final_z(window_base+window_height+reveal_crown),
        cornice=dict(finalBottomCm=cornice_bottom, finalTopCm=cornice_top,
            sourceCenterZCm=source_z((cornice_bottom+cornice_top)/2),
            sourceDepthCm=CORNICE_DEPTH_CM/upper_factor,
            outwardProjectionCm=CORNICE_PROJECTION_CM),
        structuralBayPositionsUnchanged=True, finalCoordinates=False,
        integrated=False, nativeApproved=False, visualApproved=False)
