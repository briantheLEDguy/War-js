"""Soft regional strata; colour and pixel normals only, with a screen-footprint fade."""
import math
STRATA_SHADER='''float phase=(P.z/100.0+(Noise-.5)*2.0*Warp)/Wavelength;
float footprint=max(abs(ddx(phase)),abs(ddy(phase)));
float fade=1.0-smoothstep(.15,.45,footprint);
float layer=sin(phase*6.283185307179586)*fade;
return float2(1.0-Contrast*.5+Contrast*.5*layer,layer*Bump);'''


def strata_recipe(identity):
    if identity not in ('sunmeadow_march','cinderfen_outskirts'):raise ValueError('No reviewed regional strata recipe')
    sun=identity=='sunmeadow_march'
    return dict(wavelengthMetres=4.8 if sun else 6.8,warpMetres=1.4 if sun else 2.1,contrast=.16 if sun else .24,bumpHeightCm=2 if sun else 4)


def validate_strata(row):
    if row not in [strata_recipe(z) for z in ('sunmeadow_march','cinderfen_outskirts')]:raise ValueError('Unreviewed geological strata controls')


def strata_sample(height,noise,footprint,recipe):
    validate_strata(recipe)
    if any(not math.isfinite(v) for v in (height,noise,footprint)) or not 0<=noise<=1 or footprint<0:raise ValueError('Invalid strata sample')
    t=max(0,min(1,(footprint-.15)/.3));fade=1-t*t*(3-2*t)
    phase=(height+(noise-.5)*2*recipe['warpMetres'])/recipe['wavelengthMetres'];layer=math.sin(phase*math.tau)*fade
    return [1-recipe['contrast']*.5+recipe['contrast']*.5*layer,layer*recipe['bumpHeightCm']]
