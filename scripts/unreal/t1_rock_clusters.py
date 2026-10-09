"""Deterministic installed-rock fitting inside retained terrain and route reserves."""
import math,zlib
from t1_rock_contact import bed_rock_body
NAMES=('SM_Small_Rock_01','SM_Small_Rock_03','SM_Small_Rock_05')


def rock_clusters(placements,meshes,height_cm):
    if len(placements)>512 or any(not isinstance(p.get('id'),str) or not p['id'] for p in placements) or len({p['id'] for p in placements})!=len(placements):raise ValueError('Invalid bounded rock placement inventory')
    for name in NAMES:
        mesh=meshes[name]
        if len(mesh['boundsOrigin'])!=3 or len(mesh['boundsExtent'])!=3:raise ValueError('Invalid rock source bounds')
        values=[*mesh['boundsOrigin'],*mesh['boundsExtent']]
        if len(values)!=6 or any(not math.isfinite(v) for v in values) or any(v<=0 for v in mesh['boundsExtent']):raise ValueError('Invalid rock source bounds')
    bodies=[];replaced=[];retained=[]
    for p in placements:
        if any(not math.isfinite(p[k]) for k in ('x','z','width','depth','height','yawDegrees')) or not all(.1<=p[k]<=100 for k in ('width','depth','height')):raise ValueError('Invalid rock parent footprint')
        made=[];count=max(1,min(5,math.ceil(p['width']/8)));step=p['width']/count;parent_heading=-math.radians(p['yawDegrees'])
        for j in range(count):
            seed=zlib.crc32((p['id']+str(j)).encode())&0xffffffff;name=NAMES[seed%len(NAMES)];bounds=meshes[name];extent=bounds['boundsExtent'];origin=bounds['boundsOrigin']
            jitter=((seed>>8)%1001/1000-.5)*18;delta=math.radians(jitter);c,s=abs(math.cos(delta)),abs(math.sin(delta))
            # Fit the rotated full bounds inside the original conservative collision reserve.
            projected_width=(extent[0]*c+extent[1]*s)*2/100;projected_depth=(extent[0]*s+extent[1]*c)*2/100
            scale=min(p['height']*100/(extent[2]*2),step*.95/projected_width,p['depth']*.9/projected_depth,8)
            if scale<.2:continue
            offset=(j-(count-1)/2)*step*.85;x=p['x']+math.cos(parent_heading)*offset;z=p['z']+math.sin(parent_heading)*offset
            yaw=(p['yawDegrees']+90+jitter+180)%360-180;heading=-math.radians(p['yawDegrees']+jitter)
            width=extent[0]*2*scale/100;depth=extent[1]*2*scale/100
            samples=[height_cm(x+math.cos(heading)*width*u/4-math.sin(heading)*depth*v/4,z+math.sin(heading)*width*u/4+math.cos(heading)*depth*v/4) for u in range(-2,3) for v in range(-2,3)]
            centre=height_cm(x,z)
            if any(not math.isfinite(v) for v in [*samples,centre]):raise ValueError('Nonfinite rock cluster footing')
            footing=min(samples)-15;visible=extent[2]*2*scale-(centre-footing)
            if visible<extent[2]*2*scale*.2:continue
            angle=math.radians(yaw)
            location=[z*100-(math.cos(angle)*origin[0]-math.sin(angle)*origin[1])*scale,x*100-(math.sin(angle)*origin[0]+math.cos(angle)*origin[1])*scale,footing-(origin[2]-extent[2])*scale]
            body=dict(id=p['id']+'_body_'+str(j),parentId=p['id'],meshName=name,location=location,scale=scale,yawDegrees=yaw,footprintCentre=[x,z],footprintWidth=width,footprintDepth=depth,parentProjectedWidth=projected_width*scale,parentProjectedDepth=projected_depth*scale,centreExposureCm=visible)
            body=bed_rock_body(body,bounds,height_cm)
            if body is not None:made.append(body)
        if made:bodies.extend(made);replaced.append(p['id'])
        else:retained.append(p['id'])
    if len(bodies)>1536:raise ValueError('Rock cluster body budget exceeded')
    return dict(bodies=bodies,replacedIds=replaced,retainedIds=retained)


def core_rock_parents(identity,states,mesh_path,origin,extent):
    """Convert only original natural outcrops; landmarks, shelters and tilted assemblies retain their source."""
    if identity not in ('sunmeadow_march','cinderfen_outskirts') or len(states)>4096 or len(origin)!=3 or len(extent)!=3 or not all(math.isfinite(v) for v in [*origin,*extent]) or not all(v>0 for v in extent):raise ValueError('Invalid core rock inventory')
    prefix=identity+('_barrow_ridge_' if identity=='sunmeadow_march' else '_basalt_shelf_');parents=[];retained=[]
    for label,state in states.items():
        if state.get('kind')!='mesh' or state.get('mesh')!=mesh_path or not label.startswith(prefix) or not label[len(prefix):].isdigit():continue
        scale,rotation,location=state['scale'],state['rotation'],state['location']
        if any(len(v)!=3 for v in (scale,rotation,location)) or not all(math.isfinite(v) for row in (scale,rotation,location) for v in row):raise ValueError('Invalid source outcrop transform')
        dimensions=[extent[1]*scale[1]*2/100,extent[0]*scale[0]*2/100,extent[2]*scale[2]*2/100]
        if abs(rotation[0])>1e-6 or abs(rotation[2])>1e-6 or not all(.1<=v<=100 for v in dimensions):
            retained.append(label);continue
        angle=math.radians(rotation[1]);c,s=math.cos(angle),math.sin(angle);u,v=origin[0]*scale[0],origin[1]*scale[1]
        parents.append(dict(id=label,sourceLabel=label,x=(location[1]+u*s+v*c)/100,z=(location[0]+u*c-v*s)/100,width=dimensions[0],depth=dimensions[1],height=dimensions[2],yawDegrees=rotation[1]))
    return dict(placements=parents,retainedIds=retained)
