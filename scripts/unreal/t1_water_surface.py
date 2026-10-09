"""Bounded, non-cardinal ripple recipe shared by native material construction and checks."""
import math


def water_surface(identity):
    if identity not in ('sunmeadow_march','cinderfen_outskirts'):
        raise ValueError('No admitted shallow-water region')
    sun=identity=='sunmeadow_march'
    return dict(waves=[dict(angle=a,wavelengthMetres=w,cyclesPerSecond=s,slope=v,phase=p)
        for a,w,s,v,p in ((.21,4.6,.016,.023,.17),(1.13,7.3,-.011,.016,.61),(2.41,2.9,.023,.014,.38))],
        noiseMetres=11.7,phaseWarp=.23,roughness=.16,opacity=.18,specular=.5,
        color=[.025,.045,.055] if sun else [.045,.043,.034],
        scattering=[.0008,.001,.0014] if sun else [.0024,.0021,.0014],
        absorption=[.003,.0016,.0008] if sun else [.004,.0045,.005])


def ripple_normal(x_metres,y_metres,seconds,noise,recipe):
    """Reference normal: cosmetic slopes only, independent of collision and terrain height."""
    if any(not math.isfinite(v) for v in (x_metres,y_metres,seconds,noise)) or not 0<=noise<=1:
        raise ValueError('Ripple inputs must be finite; reviewed channel noise is normalized')
    x=y=0
    for w in recipe['waves']:
        dx,dy=math.cos(w['angle']),math.sin(w['angle'])
        phase=(x_metres*dx+y_metres*dy)/w['wavelengthMetres']+seconds*w['cyclesPerSecond']+w['phase']+noise*recipe['phaseWarp']
        slope=math.sin(phase*math.tau)*w['slope'];x+=dx*slope;y+=dy*slope
    length=math.sqrt(1+x*x+y*y)
    return [x/length,y/length,1/length]
