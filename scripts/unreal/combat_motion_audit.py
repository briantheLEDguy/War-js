"""Conservative geometric checks; these do not replace multi-view human review."""
import math


def audit_heavy_path(samples):
    """Reject the front-only clock sweep; inspect actual head/pelvis positions."""
    frames=[{key.rsplit('/',1)[-1]:point for key,point in row['joints'].items()} for row in samples]
    if len(frames)<3 or any('vfx_weapon_tip' not in frame or 'hips' not in frame for frame in frames):
        raise ValueError('Missing heavy-weapon path samples')
    tips=[frame['vfx_weapon_tip'] for frame in frames]
    rear=max(tip[1]-frame['hips'][1] for tip,frame in zip(tips,frames))
    forward=max(frame['hips'][1]-tip[1] for tip,frame in zip(tips,frames))
    sagittal=max(point[1] for point in tips)-min(point[1] for point in tips)
    lateral=max(point[0] for point in tips)-min(point[0] for point in tips)
    if rear<.30 or forward<.70 or sagittal<1.20:
        raise ValueError('Heavy strike lacks a rear load and forward delivery')
    if lateral>sagittal:
        raise ValueError('Heavy strike is predominantly a frontal clock sweep')
    return {'rearHeadReachMeters':rear,'forwardHeadReachMeters':forward,
            'sagittalTravelMeters':sagittal,'lateralTravelMeters':lateral}


def audit_samples(samples):
    if len(samples) < 3:
        raise ValueError('At least three whole-body samples are required')
    frames = [{key.rsplit('/',1)[-1]: point for key,point in sample['joints'].items()} for sample in samples]
    required = ['hips','chest'] + [bone+side for side in ('L','R')
                                 for bone in ('upper_arm_','forearm_','hand_','thigh_','shin_','foot_')]
    for frame in frames:
        if any(bone not in frame for bone in required): raise ValueError('Missing whole-body joint')
        if any(len(point)!=3 or not all(math.isfinite(n) for n in point) for point in frame.values()):
            raise ValueError('Nonfinite or malformed joint')
    max_drift, max_stretch, max_support_error = 0.,0.,0.
    for frame in frames:
        for side in ('L','R'):
            max_drift=max(max_drift,math.dist(frame['foot_'+side],frames[0]['foot_'+side]))
            for start,end in [('upper_arm_','forearm_'),('forearm_','hand_'),('thigh_','shin_'),('shin_','foot_')]:
                reference=math.dist(frames[0][start+side],frames[0][end+side])
                max_stretch=max(max_stretch,abs(math.dist(frame[start+side],frame[end+side])-reference))
        # Pelvis projection must remain over the two planted soles. This is a
        # support-envelope check, not a claim to simulate a body's center of mass.
        for axis,sole_margin in [(0,.09),(1,.17)]:
            lo=min(frame['foot_L'][axis],frame['foot_R'][axis])-sole_margin
            hi=max(frame['foot_L'][axis],frame['foot_R'][axis])+sole_margin
            max_support_error=max(max_support_error,lo-frame['hips'][axis],frame['hips'][axis]-hi)
    if max_drift > .008: raise ValueError('Planted foot slides')
    if max_stretch > .001: raise ValueError('Limb length changes')
    if max_support_error > .005: raise ValueError('Pelvis leaves planted support envelope')
    hips_travel=max(math.dist(frame['hips'],frames[0]['hips']) for frame in frames)
    hands_travel=max(math.dist(frame['hand_'+side],frames[0]['hand_'+side]) for frame in frames for side in ('L','R'))
    if hands_travel > .15 and hips_travel < .01:
        raise ValueError('Large upper-body gesture has no lower-body weight transfer')
    return {'maxFootDriftMeters':max_drift,'maxLimbLengthChangeMeters':max_stretch,
            'maxSupportEnvelopeErrorMeters':max_support_error,'pelvisTravelMeters':hips_travel,
            'handTravelMeters':hands_travel,'visualApproval':False}
