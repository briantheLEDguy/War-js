import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from citadel_collision_policy import validate_capsule_policy as validate
from citadel_collision_policy import validate_capsule_kinematics
from fixtures.citadelCapsulePolicy import capsule_kinematics_policy


def policy():
    return dict(version=1,source='native_AWarCharacter_class_default_capsule_v1',
        characterClass='/Script/AegisWar.WarCharacter',classDefaultClass='/Script/AegisWar.WarCharacter',
        profile='Custom',classDefaultProfile='Custom',collisionEnabled=3,classDefaultCollisionEnabled=3,
        objectChannel=2,classDefaultObjectChannel=2,responses=[0 if i==8 else 2 for i in range(64)],
        classDefaultResponses=[0 if i==8 else 2 for i in range(64)],matchesClassDefault=True,simulatingPhysics=False,classDefaultSimulatingPhysics=False)


class CapsulePolicyTests(unittest.TestCase):
    def test_geometry_and_walking_limits_cannot_drift_or_accept_numeric_bool_aliases(self):
        validate_capsule_kinematics(capsule_kinematics_policy())
        for key,value in [('version',True),('scaledRadiusCm',21),('scaledHalfHeightCm',48),
                ('maxStepHeightCm',90),('walkableFloorZ',.2),('gravityScale',0),('gravityScale',True),
                ('componentScale',[.5,.5,.5]),('capsuleAxis',[0,1,0]),('gravityDirection',[0,0,1]),
                ('updatedComponentIsCapsule',False),('matchesClassDefault',False)]:
            p=capsule_kinematics_policy();p[key]=value
            with self.assertRaises(ValueError):validate_capsule_kinematics(p)
        p=capsule_kinematics_policy();p['capsuleRadiusCm']=p['classDefaultRadiusCm']=p['scaledRadiusCm']=21
        with self.assertRaises(ValueError):validate_capsule_kinematics(p)

    def test_exact_native_capsule_with_visibility_block_is_supported(self):
        validate(policy())

    def test_every_channel_is_independently_required(self):
        for channel in range(64):
            for field in ('responses','classDefaultResponses'):
                p=policy();p[field][channel]=1
                with self.assertRaises(ValueError):validate(p)
        for field in ('responses','classDefaultResponses'):
            for value in (None,[],[2]*32,[2]*65,[True]*64):
                p=policy();p[field]=value
                with self.assertRaises(ValueError):validate(p)

    def test_profile_label_or_equal_tampered_defaults_cannot_replace_physics(self):
        for key,value in [('version',True),('profile','Pawn'),('collisionEnabled',1),('objectChannel',0),
                ('characterClass','/Script/AegisWar.WarEnemy'),('simulatingPhysics',True),('matchesClassDefault',False)]:
            p=policy();p[key]=value
            with self.assertRaises(ValueError):validate(p)
        p=policy();p['responses'][0]=p['classDefaultResponses'][0]=0
        with self.assertRaises(ValueError):validate(p)


if __name__=='__main__':unittest.main()
