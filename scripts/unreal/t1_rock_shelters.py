"""Two-ended source-rock exploration shelters on retained ground; no terrain holes or lair admission."""
import math
from t1_bedded_outcrops import outcrop_footing
from t1_landscape_ecology import inside,segment_distance


def rock_shelter(source,height_cm,pockets,occupied,native_bounds):
    identity=source['id'];sun=identity=='sunmeadow_march'
    if not sun and identity!='cinderfen_outskirts':raise ValueError('Rock shelters require an admitted first-pair region')
    if len(native_bounds)!=2 or any(len(p)!=3 for p in native_bounds) or any(not math.isfinite(v) for p in native_bounds for v in p):raise ValueError('Invalid native shelter source bounds')
    lo,hi=native_bounds
    spans=[(b-a)/100 for a,b in zip(lo,hi)]
    if any(not .5<=v<=12 for v in spans):raise ValueError('Shelter source dimensions are outside admitted bounds')
    suffix='eastern_hollow' if sun else 'rust_sedge'
    choices=[p for p in pockets if p['id']==identity+'_pocket_'+suffix and not p['cosmeticWater']]
    if len(choices)!=1:raise ValueError('Shelter requires its exact dry exploration pocket')
    site=choices[0];cx,cz=site['x'],site['z'];last=site['approach'][-2]
    forward=(cx-last['x'],cz-last['z']);length=math.hypot(*forward)
    if length<1:raise ValueError('Shelter approach has no direction')
    fx,fz=[v/length for v in forward];wx,wz=fz,-fx;yaw=-math.degrees(math.atan2(wz,wx))
    at=lambda w,d:dict(x=cx+wx*w+fx*d,z=cz+wz*w+fz*d)
    # Wide portals retain the outdoor camera; floor samples cover the full six-metre walking lane.
    floor=[height_cm(**at(w,d)) for w in (-3,0,3) for d in range(-12,13,2)]
    if any(not math.isfinite(v) for v in floor):raise ValueError('Nonfinite shelter ground')
    for w in (-3,0,3):
        heights=[height_cm(**at(w,d)) for d in range(-12,13)]
        if any(abs(b-a)>22 for a,b in zip(heights,heights[1:])):raise ValueError('Shelter approach exceeds walkable grade')
    if 13-spans[1]*(.9+1.05)/2<6:raise ValueError('Source piers cannot preserve the six-metre walking lane')
    for d in range(-12,13,2):
        if abs(height_cm(**at(3,d))-height_cm(**at(-3,d)))>132:raise ValueError('Shelter floor cross-grade exceeds walkable grade')
    roof_bottom=max(floor)+570;roof_height=130;parts=[]
    # Unequal natural piers support a single fallen slab; both short ends remain open.
    specs=[('west_pier',-6.5,0,[.9,1.6,None]),('east_pier',6.5,.4,[1.05,1.4,None]),('fallen_cap',0,0,[16/spans[1],9/spans[0],roof_height/(spans[2]*100)])]
    for label,w,d,axes in specs:
        centre=at(w,d);width=spans[1]*axes[0];depth=spans[0]*axes[1]
        footprint=dict(**centre,width=width,depth=depth,yawDegrees=yaw)
        if label=='fallen_cap':base=roof_bottom
        else:
            base=outcrop_footing(height_cm,footprint)
            axes[2]=(roof_bottom+55-base)/(spans[2]*100)
        if not all(0<v<=5 for v in axes):raise ValueError('Shelter adaptation exceeds bounded scale')
        # Account for the source mesh's off-centre origin, including its lowest Z.
        angle=math.radians(yaw);local_x=(lo[0]+hi[0])*.5*axes[1];local_y=(lo[1]+hi[1])*.5*axes[0]
        offset_x=local_x*math.cos(angle)-local_y*math.sin(angle);offset_y=local_x*math.sin(angle)+local_y*math.cos(angle)
        location=[centre['z']*100-offset_x,centre['x']*100-offset_y,base-lo[2]*axes[2]]
        radius=math.hypot(width,depth)/2
        if not inside(centre,source['spatial']['playableOutline']) or min(segment_distance(centre,a,b) for a,b in zip(source['spatial']['playableOutline'],source['spatial']['playableOutline'][1:]+source['spatial']['playableOutline'][:1]))<radius+3:raise ValueError('Shelter leaves playable ground')
        if any(segment_distance(centre,a,b)<radius+r['width']/2+3 for r in source['paths'] for a,b in zip(r['points'],r['points'][1:])):raise ValueError('Shelter obstructs a retained road')
        if any(math.hypot(centre['x']-q['x'],centre['z']-q['z'])<radius+math.hypot(q['width'],q['depth'])/2+1 for q in occupied):raise ValueError('Shelter overlaps existing scenery')
        parts.append(dict(id=identity+'_shelter_'+label,sourceLabel=identity+('_barrow_ridge_8' if sun else '_basalt_shelf_1'),**centre,width=width,depth=depth,height=spans[2]*axes[2],scaleAxes=axes,yawDegrees=yaw,tiltDegrees=[0,0],grounding='shelter',authoredLocationCm=location))
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    if any(math.hypot(cx-a['x'],cz-a['z'])<30 for a in anchors):raise ValueError('Shelter displaces a retained gameplay anchor')
    portals=[at(0,d) for d in (-12,12)]
    route=[at(0,d) for d in (-12,-8,-4,0,4,8,12)]
    points=[[p['z']*100,p['x']*100,height_cm(**p)] for p in route]
    return dict(id=identity+'_shelter',label='Hearthroot Fallen Chamber' if sun else 'Rustsedge Fracture Shelter',pocket=site['id'],centre=dict(x=cx,z=cz),placements=parts,points=points,portals=portals,
        minimumRoofClearanceCm=570,clearWalkingWidthMetres=6,maximumSourceGrade=.22,terrainCut=False,undergroundBuilt=False,lairAccepted=False,appearanceApproved=False,walkingAccepted=False,cameraAccepted=False)
