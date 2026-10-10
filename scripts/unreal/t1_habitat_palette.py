"""Bounded habitat colour weights and private regional rock adaptation; source textures stay unchanged."""
import math

HABITAT=dict(patchMetres=[37,13],macroMetres=71,dryThresholds=[.28,.72],dryMaximum=.75,forestMaximum=.92,macroMinimum=.68,macroRange=.4,regionalMix=.22)

def habitat_weights(canopy,coarse,fine,macro):
    if any(not math.isfinite(v) or not 0<=v<=1 for v in (canopy,coarse,fine,macro)):raise ValueError('Invalid habitat sample')
    patch=(coarse+.5*fine)/1.5;lo,hi=HABITAT['dryThresholds'];u=max(0,min(1,(patch-lo)/(hi-lo)))
    dry=u*u*(3-2*u)*(1-canopy)*HABITAT['dryMaximum']
    return dict(forest=min(1,canopy*HABITAT['forestMaximum']+dry),macro=HABITAT['macroMinimum']+HABITAT['macroRange']*macro,regional=HABITAT['regionalMix']*(1-canopy))

NOISE_HLSL=' float noise(float2 p) {float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i).x,hash(i+float2(1,0)).x,f.x),lerp(hash(i+float2(0,1)).x,hash(i+1).x,f.x),f.y); }\n'

def habitat_hlsl(canopy):
    g=HABITAT;a,b=g['patchMetres'];lo,hi=g['dryThresholds']
    return f"float patch=(h.noise(p/{a})+.5*h.noise(p/{b}))/1.5;\nfloat dry=smoothstep({lo},{hi},patch)*(1-{canopy})*{g['dryMaximum']};\nfloat habitatForest=saturate({canopy}*{g['forestMaximum']}+dry);\nfloat habitatMacro={g['macroMinimum']}+{g['macroRange']}*h.noise(p/{g['macroMetres']});\n"

def installed_rock_palette(identity,tint):
    if identity not in ('sunmeadow_march','cinderfen_outskirts') or len(tint)!=4 or any(not math.isfinite(v) or v<0 or v>16 for v in tint):raise ValueError('Invalid installed rock palette')
    if identity=='sunmeadow_march':return dict(tint=list(tint),factor=1,desaturation=None)
    return dict(tint=[v*.35 for v in tint[:3]]+[tint[3]],factor=.35,desaturation=.35)
