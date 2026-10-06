"""Independently audit all UE 5.8 native character capsule response channels."""


def validate_capsule_policy(p):
    def responses(value):
        return isinstance(value,list) and len(value)==64 and all(type(r) is int and r==(0 if i==8 else 2) for i,r in enumerate(value))
    if (not isinstance(p,dict) or type(p.get('version')) is not int or p['version']!=1
            or p.get('source')!='native_AWarCharacter_class_default_capsule_v1'
            or p.get('characterClass')!='/Script/AegisWar.WarCharacter' or p.get('classDefaultClass')!=p['characterClass']
            or p.get('profile')!='Custom' or p.get('classDefaultProfile')!='Custom'
            or type(p.get('collisionEnabled')) is not int or p['collisionEnabled']!=3
            or type(p.get('classDefaultCollisionEnabled')) is not int or p['classDefaultCollisionEnabled']!=3
            or type(p.get('objectChannel')) is not int or p['objectChannel']!=2
            or type(p.get('classDefaultObjectChannel')) is not int or p['classDefaultObjectChannel']!=2
            or not responses(p.get('responses')) or not responses(p.get('classDefaultResponses'))
            or p.get('matchesClassDefault') is not True or p.get('simulatingPhysics') is not False or p.get('classDefaultSimulatingPhysics') is not False):
        raise ValueError('Complete unchanged native character capsule collision policy is required.')


def validate_capsule_kinematics(p):
    import math
    def near(v,n,tolerance=1e-10):
        return type(v) in (int,float) and math.isfinite(v) and abs(v-n)<=tolerance
    def vector(v,expected):
        return isinstance(v,list) and len(v)==3 and all(near(n,expected[i]) for i,n in enumerate(v))
    if (not isinstance(p,dict) or type(p.get('version')) is not int or p['version']!=1
            or p.get('source')!='native_AWarCharacter_class_default_kinematics_v1'
            or any(not near(p.get(k),42,0) for k in ('capsuleRadiusCm','classDefaultRadiusCm','scaledRadiusCm'))
            or any(not near(p.get(k),96,0) for k in ('capsuleHalfHeightCm','classDefaultHalfHeightCm','scaledHalfHeightCm'))
            or not vector(p.get('componentScale'),[1,1,1]) or not vector(p.get('capsuleAxis'),[0,0,1])
            or not near(p.get('maxStepHeightCm'),45,0) or not near(p.get('classDefaultMaxStepHeightCm'),45,0)
            or not near(p.get('walkableFloorZ'),.71,1e-7) or p.get('classDefaultWalkableFloorZ')!=0.7099999785423279
            or not near(p.get('walkableFloorZ'),p.get('classDefaultWalkableFloorZ'),1e-7)
            or p.get('capturedRuntimeValuesPinned') is not True
            or not near(p.get('gravityScale'),1,0) or not near(p.get('classDefaultGravityScale'),1,0)
            or not vector(p.get('gravityDirection'),[0,0,-1]) or p.get('updatedComponentIsCapsule') is not True
            or p.get('matchesClassDefault') is not True):
        raise ValueError('Complete unchanged native capsule geometry and walking policy is required.')
