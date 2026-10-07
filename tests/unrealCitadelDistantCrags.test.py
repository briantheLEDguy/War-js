import copy
import hashlib
import json
import math
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from aegis_citadel_distant_crags import (OPTION, FROZEN_INPUTS, REFERENCE, BOOLEAN_POLICY, SHADOW_FIELDS,
    COLOR_SHADER, HEIGHT_SHADER, NORMAL_SHADER, bind_backdrop, checked_option, checked_native_policy,
    protected_records, owned_destination, read_component_policy, checked_retained_collision,
    configure_component_policy)

HERE = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = None
REVISION = 'aaaaaaaaaaaa'


class CragIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Portable contract fixtures are deliberately separate from the private
        # original prototype. Its frozen geometry still requires native review.
        global FIXTURE_ROOT
        cls.directory = tempfile.TemporaryDirectory()
        FIXTURE_ROOT = Path(cls.directory.name)
        points = [[63000,70000,14000],[112500,240000,23000],[80000,150000,14000],
                  [64000,72000,-42000],[65000,75000,16000],[66000,76000,17000],
                  [67000,77000,18000],[68000,78000,19000]]
        controls = [dict(pointCm=p) for p in points]
        mesh = dict(collision=False, positions=points, normals=[[0,0,1] for _ in points],
                    indices=[0,1,2]*4996,
                    materials=['prototype_crag_rock','prototype_crag_dark_seam','prototype_crag_snow'],
                    triangleMaterials=[0]*4126+[1]*551+[2]*319)
        blueprint = {key:[] for key in ('routeSurfaceHeightField','gates','objectives','optionalObjectives',
                     'rooms','gameplayPads','teamSpawns','spawnApproaches','spawnRelocations','stairConstruction')}
        blueprint['routes'] = [dict(id='fixture_'+str(i)) for i in range(43)]
        target = FIXTURE_ROOT / 'artifacts/unreal/aegis-citadel' / REVISION / 'blueprint.json'
        target.parent.mkdir(parents=True);target.write_text(json.dumps(blueprint))
        files = {
            'optional_distant_crags.py': b'# Portable binding fixture\n',
            'measurements.json': json.dumps(dict(distantRidgeCompositionSeeds=controls)).encode(),
            'patch-src/output/aegis_citadel_mesh.py': b'# Portable exporter binding fixture\n',
            'optional-prototype/connected-crags.mesh.json': json.dumps(mesh).encode(),
            'optional-prototype/final-hashes.json': b'{}',
        }
        files['optional-prototype/report.json'] = json.dumps(dict(compositionSeeds=controls, triangles=4996,
            connectedComponents=1, boundsCm=[[63000,70000,-42000],[112500,240000,23000]],
            meshSha256=hashlib.sha256(files['optional-prototype/connected-crags.mesh.json']).hexdigest(),
            spec=dict(materialSource={'prototype_crag_rock':dict(shadingBumpCm=.7)}))).encode()
        for name, content in files.items():
            target = FIXTURE_ROOT / REFERENCE / name
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        for name in ('unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImportLibrary.cpp',
                     'scripts/unreal/citadel_stage_contract.py'):
            target = FIXTURE_ROOT/name
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'portable source binding')
        cls.hash_patch = patch.dict('aegis_citadel_distant_crags.FROZEN_INPUTS',
            {name:hashlib.sha256(content).hexdigest() for name,content in files.items()},clear=True)
        cls.hash_patch.start()
        cls.blueprint = json.loads((FIXTURE_ROOT / 'artifacts/unreal/aegis-citadel' / REVISION / 'blueprint.json').read_text())
        cls.binding, cls.mesh = bind_backdrop(FIXTURE_ROOT, cls.blueprint, REVISION)

    @classmethod
    def tearDownClass(cls):
        cls.hash_patch.stop();cls.directory.cleanup()

    def test_opt_in_is_explicit_and_off_by_default(self):
        self.assertFalse(checked_option(''))
        self.assertTrue(checked_option(OPTION))
        for value in ('true', '1', 'connected_original', None):
            with self.assertRaises(ValueError): checked_option(value)

    def test_frozen_input_bytes_are_bound(self):
        for name, expected in FROZEN_INPUTS.items():
            self.assertEqual(hashlib.sha256((FIXTURE_ROOT / REFERENCE / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(self.binding['geometrySha256'], FROZEN_INPUTS['optional-prototype/connected-crags.mesh.json'])

    def test_changed_input_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root = Path(directory)
            target = root / 'artifacts/unreal/aegis-citadel' / REVISION / 'blueprint.json'
            target.parent.mkdir(parents=True);target.write_text(json.dumps(self.blueprint))
            first = root / REFERENCE / 'optional_distant_crags.py'
            first.parent.mkdir(parents=True);first.write_text('changed source')
            with self.assertRaisesRegex(ValueError, 'Frozen original crag input changed'):
                bind_backdrop(root, self.blueprint, REVISION)

    def test_all_gameplay_records_and_blueprint_remain_unchanged(self):
        before = copy.deepcopy(self.blueprint)
        binding, mesh = bind_backdrop(FIXTURE_ROOT, self.blueprint, REVISION)
        self.assertEqual(self.blueprint, before)
        self.assertEqual(binding['protectedGameplayRecords'], protected_records(before))
        for key in ('routes','routeSurfaceHeightField','gates','objectives','optionalObjectives',
                    'rooms','gameplayPads','teamSpawns','spawnApproaches','spawnRelocations','stairConstruction'):
            self.assertIn(key, binding['protectedGameplayRecords'])
        self.assertIsNot(mesh, self.mesh)
        self.assertEqual(len(before['routes']), 43)

    def test_mismatched_blueprint_or_revision_is_rejected(self):
        changed = copy.deepcopy(self.blueprint);changed['routes'][0]['id'] += '_changed'
        with self.assertRaisesRegex(ValueError, 'exact source blueprint'):
            bind_backdrop(FIXTURE_ROOT, changed, REVISION)
        with self.assertRaises(ValueError): bind_backdrop(FIXTURE_ROOT, self.blueprint, '../unsafe')

    def test_bound_material_roles_and_face_counts(self):
        self.assertEqual(self.mesh['materials'], ['prototype_crag_rock','prototype_crag_dark_seam','prototype_crag_snow'])
        self.assertEqual([self.mesh['triangleMaterials'].count(i) for i in range(3)], [4126,551,319])
        self.assertEqual(self.binding['prototypeMaterialSpec']['prototype_crag_rock']['shadingBumpCm'], .7)
        self.assertFalse(self.binding['nativeMaterialRecipe']['vertexDisplacement'])
        self.assertEqual(self.binding['nativeMaterialRecipe']['colorShader'], COLOR_SHADER)
        self.assertIn('65.0', COLOR_SHADER);self.assertIn('1700.0', COLOR_SHADER)
        self.assertIn('*.7', HEIGHT_SHADER);self.assertIn('ddx', NORMAL_SHADER)

    def test_bound_fixture_preserves_eight_controls_and_final_bounds(self):
        positions = self.mesh['positions']
        for row in self.binding['controls']: self.assertIn(row['pointCm'], positions)
        bounds = [[min(p[axis] for p in positions) for axis in range(3)],
                  [max(p[axis] for p in positions) for axis in range(3)]]
        self.assertEqual(bounds, [[63000,70000,-42000],[112500,240000,23000]])
        self.assertEqual(len(self.mesh['indices'])//3, 4996)
        self.assertFalse(self.mesh['collision'])

    def test_bound_fixture_snow_slots_follow_ledge_assignment(self):
        for offset, role in enumerate(self.mesh['triangleMaterials']):
            if role != 2: continue
            indices = self.mesh['indices'][offset*3:offset*3+3]
            points = [self.mesh['positions'][i] for i in indices]
            self.assertGreaterEqual(sum(p[2] for p in points)/3, 14000)
            # Exported flat corner normals retain the original material selection direction.
            normal = self.mesh['normals'][indices[0]]
            self.assertGreaterEqual(normal[2]/math.sqrt(sum(v*v for v in normal)), .6799)

    def test_no_collision_and_all_shadow_flags_are_required(self):
        result = checked_native_policy('NO_COLLISION','NO_COLLISION', dict(BOOLEAN_POLICY))
        self.assertEqual(result['collisionEnabled'], 'NO_COLLISION')
        self.assertEqual(len(SHADOW_FIELDS), 11)
        self.assertTrue(all(v is False for v in result['properties'].values()))
        with self.assertRaises(ValueError): checked_native_policy('QUERY_ONLY','NO_COLLISION', dict(BOOLEAN_POLICY))

    def test_each_enabled_or_missing_native_flag_fails(self):
        for name in BOOLEAN_POLICY:
            for replacement in (True, None, 0):
                changed = dict(BOOLEAN_POLICY);changed[name] = replacement
                with self.subTest(name=name, replacement=replacement), self.assertRaises(ValueError):
                    checked_native_policy('NO_COLLISION','NO_COLLISION', changed)
            changed = dict(BOOLEAN_POLICY);del changed[name]
            with self.assertRaises(ValueError): checked_native_policy('NO_COLLISION','NO_COLLISION', changed)

    def test_readback_uses_native_values_and_unavailable_property_fails(self):
        class Collision: NO_COLLISION = 'NO_COLLISION'
        class Unreal: CollisionEnabled = Collision
        class Component:
            def get_collision_enabled(self): return 'NO_COLLISION'
            def get_collision_profile_name(self): return 'NoCollision'
            def get_editor_property(self, name): return False
        self.assertEqual(read_component_policy(Unreal,Component())['properties'], BOOLEAN_POLICY)
        class Missing(Component):
            def get_editor_property(self, name): raise RuntimeError('unavailable native property')
        with self.assertRaises(RuntimeError): read_component_policy(Unreal,Missing())

    def test_profile_override_survives_default_mesh_collision_reload(self):
        class Collision: NO_COLLISION = 'NO_COLLISION'
        class Unreal: CollisionEnabled = Collision
        class Component:
            def __init__(self):
                self.properties = {**BOOLEAN_POLICY,'use_default_collision':True}
                self.profile = 'BlockAll';self.collision = 'QUERY_AND_PHYSICS'
            def set_collision_profile_name(self, name):
                self.profile = name;self.properties['use_default_collision'] = False
            def set_collision_enabled(self, value): self.collision = value
            def set_editor_property(self, name, value): self.properties[name] = value
            def get_collision_enabled(self): return self.collision
            def get_collision_profile_name(self): return self.profile
            def get_editor_property(self, name): return self.properties[name]
            def reload(self):
                if self.properties['use_default_collision']:
                    self.collision = 'QUERY_AND_PHYSICS';self.profile = 'BlockAll'
        unsafe = Component();unsafe.set_collision_enabled(Collision.NO_COLLISION);unsafe.reload()
        with self.assertRaises(ValueError): read_component_policy(Unreal,unsafe)
        safe = Component();configure_component_policy(Unreal,safe);safe.reload()
        self.assertEqual(read_component_policy(Unreal,safe)['collisionProfile'], 'NoCollision')
        self.assertFalse(safe.properties['use_default_collision'])

    def test_destination_is_exact_and_owned(self):
        signature = 'a'*64
        self.assertEqual(owned_destination('/Game/WorldRebuild/AegisCitadel_'+signature[:12],signature),
                         '/Game/WorldRebuild/AegisCitadel_'+signature[:12])
        for bad in ('/Game/LicensedKits/Anything','/Game/WorldRebuild/AegisCitadel_bbbbbbbbbbbb',
                    '/Game/WorldRebuild/AegisCitadel_'+signature[:12]+'/../canonical'):
            with self.assertRaises(ValueError): owned_destination(bad,signature)

    def test_no_proposal_acceptance_flags(self):
        for key in ('nativeFlagsVerified','runtimeFlagsVerified','visualApproved','traversalApproved',
                    'gameplayApproved','releaseAcceptance'):
            self.assertIs(self.binding[key], False)

    def test_retained_collision_or_transform_change_is_rejected(self):
        before = {'court': {'actorTransform':[0,0,0], 'components':{'floor':{
            'collisionEnabled':'QUERY_AND_PHYSICS','collisionProfile':'BlockAll','cast_shadow':True}}}}
        self.assertIsInstance(checked_retained_collision(before,copy.deepcopy(before)), str)
        for after in ({}, {**before,'new_actor':{}}, {'court':{'actorTransform':[1,0,0]}},
                      {'court':{'actorTransform':[0,0,0], 'components':{'floor':{'collisionEnabled':'NO_COLLISION'}}}}):
            with self.assertRaises(ValueError): checked_retained_collision(before,after)


if __name__ == '__main__': unittest.main()
