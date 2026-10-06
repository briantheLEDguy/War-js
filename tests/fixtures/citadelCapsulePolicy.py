import math


def capsule_collision_policy():
    return dict(version=1,source='native_AWarCharacter_class_default_capsule_v1',
        characterClass='/Script/AegisWar.WarCharacter',classDefaultClass='/Script/AegisWar.WarCharacter',
        profile='Custom',classDefaultProfile='Custom',collisionEnabled=3,classDefaultCollisionEnabled=3,
        objectChannel=2,classDefaultObjectChannel=2,responses=[0 if i==8 else 2 for i in range(64)],
        classDefaultResponses=[0 if i==8 else 2 for i in range(64)],matchesClassDefault=True,
        simulatingPhysics=False,classDefaultSimulatingPhysics=False)


def capsule_kinematics_policy():
    return dict(version=1,source='native_AWarCharacter_class_default_kinematics_v1',
        capsuleRadiusCm=42,capsuleHalfHeightCm=96,classDefaultRadiusCm=42,classDefaultHalfHeightCm=96,
        scaledRadiusCm=42,scaledHalfHeightCm=96,componentScale=[1,1,1],capsuleAxis=[0,0,1],
        maxStepHeightCm=45,classDefaultMaxStepHeightCm=45,walkableFloorZ=0.7100000381469727,
        classDefaultWalkableFloorZ=0.7099999785423279,gravityScale=1,classDefaultGravityScale=1,
        gravityDirection=[0,0,-1],capturedRuntimeValuesPinned=True,updatedComponentIsCapsule=True,matchesClassDefault=True)
