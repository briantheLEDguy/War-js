import copy
import importlib.util
from pathlib import Path
import unittest
import math

spec=importlib.util.spec_from_file_location('motion_audit',Path(__file__).resolve().parents[1]/'scripts/unreal/combat_motion_audit.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
spec=importlib.util.spec_from_file_location('two_handed_motion',Path(__file__).resolve().parents[1]/'scripts/unreal/two_handed_motion.py')
heavy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(heavy)


class WholeBodyAuditTests(unittest.TestCase):
    def frames(self):
        joints={'hips':[0,0,1],'chest':[0,0,1.4]}
        for side,x in [('L',.12),('R',-.12)]:
            for bone,y,z in [('thigh_',0,1),('shin_',-.06,.55),('foot_',0,.1),
                             ('upper_arm_',0,1.45),('forearm_',-.18,1.25),('hand_',-.35,1.1)]:
                joints[bone+side]=[x,y,z]
        return [{'joints':copy.deepcopy(joints)} for _ in range(3)]

    def test_accepts_stationary_planted_reference(self):
        self.assertEqual(audit.audit_samples(self.frames())['maxFootDriftMeters'],0)

    def test_sliding_entire_body_is_rejected_even_with_rigid_limbs(self):
        frames=self.frames()
        for point in frames[1]['joints'].values(): point[0]+=.03
        with self.assertRaisesRegex(ValueError,'foot slides'): audit.audit_samples(frames)

    def test_reaching_by_stretching_forearm_is_rejected(self):
        frames=self.frames()
        frames[1]['joints']['hand_L'][1]-=.10
        with self.assertRaisesRegex(ValueError,'Limb length'): audit.audit_samples(frames)

    def test_unbalanced_hip_translation_is_rejected(self):
        frames=self.frames()
        frames[1]['joints']['hips'][0]=.4
        with self.assertRaisesRegex(ValueError,'support envelope'): audit.audit_samples(frames)

    def test_nonfinite_and_missing_data_fail(self):
        frames=self.frames()
        frames[1]['joints']['hips'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite'): audit.audit_samples(frames)
        del frames[1]['joints']['foot_L']
        with self.assertRaisesRegex(ValueError,'Missing'): audit.audit_samples(frames)


    def test_large_arm_gesture_requires_lower_body_response(self):
        frames=self.frames()
        for bone in ('upper_arm_L','forearm_L','hand_L'):
            frames[1]['joints'][bone][1]-=.25
        with self.assertRaisesRegex(ValueError,'weight transfer'): audit.audit_samples(frames)


class HeavyWeaponTests(unittest.TestCase):
    def test_old_front_only_clock_sweep_is_rejected(self):
        rows=[{'joints':{'hips':[0,0,1], 'vfx_weapon_tip':[math.sin(a),-.5,1+math.cos(a)]}}
              for a in [i*math.pi/20 for i in range(41)]]
        with self.assertRaisesRegex(ValueError,'rear load'): audit.audit_heavy_path(rows)

    def test_rear_to_front_overhead_path_is_accepted(self):
        rows=[{'joints':{'hips':[0,0,1], 'vfx_weapon_tip':[-.3,y,z]}}
              for y,z in [(-.4,1.8),(.65,2.0),(-.1,2.4),(-1.1,.3),(-.4,1.8)]]
        self.assertGreater(audit.audit_heavy_path(rows)['sagittalTravelMeters'],1.5)

    def test_pitch_interpolation_stays_in_swing_plane(self):
        for i in range(101):
            pitch=1.17+(-2.72-1.17)*i/100
            axis=heavy.shaft_axis(pitch,-.15)
            self.assertAlmostEqual(axis[0],-.15)
            self.assertAlmostEqual(sum(n*n for n in axis),1)
        self.assertLess(heavy.shaft_axis(-math.pi/2,-.15)[1],-.98)

    def test_transit_keeps_velocity_but_load_hold_is_stationary(self):
        keys=[(0,(0,)),(.6,(1,)),(.8,(1,)),(.94,(.2,)),(1.08,(-2.7,)),(1.4,(-2.7,))]
        self.assertEqual(heavy.curve(keys,.7),(1.,))
        before=(heavy.curve(keys,.94)[0]-heavy.curve(keys,.93999)[0])/.00001
        after=(heavy.curve(keys,.94001)[0]-heavy.curve(keys,.94)[0])/.00001
        self.assertLess(before,-1)
        self.assertAlmostEqual(before,after,delta=.01)


if __name__=='__main__': unittest.main()
