"""Atlas invariants shared by the anatomical cage builders and focused tests."""
import math

def assert_single_atlas_island(coordinates, label='face', columns=4, rows=2):
    islands=set()
    for u,v in coordinates:
        if not math.isfinite(u+v) or not (0<=u<1 and 0<=v<1):
            raise ValueError(f'{label}: atlas coordinate outside its texture')
        islands.add((math.floor(u*columns),math.floor(v*rows)))
    if len(islands)!=1:
        raise ValueError(f'{label}: face UVs interpolate across unrelated atlas islands')
