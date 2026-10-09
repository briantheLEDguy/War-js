"""Scene recipes use source width/depth/height; Unreal meshes use depth/width/height."""
import math


def source_scale_to_native(axes):
    if not isinstance(axes,(list,tuple)) or len(axes)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=20 for v in axes):
        raise ValueError('Scene scale requires bounded positive source width/depth/height')
    return [axes[1],axes[0],axes[2]]
