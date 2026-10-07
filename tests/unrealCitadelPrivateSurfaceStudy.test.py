"""Portable failure controls; these do not execute Unreal or validate pixels."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
REPO = next(p for p in Path(__file__).resolve().parents if (p / 'package.json').is_file())
sys.path.insert(0, str(REPO / 'scripts/unreal'))
HELPER = Path(__file__).resolve().parents[1] / 'scripts/unreal/citadel_private_surface_study.py'
if not HELPER.is_file():
    HELPER = REPO / 'scripts/unreal/citadel_private_surface_study.py'
loader = importlib.util.spec_from_file_location('private_surface_proposal', HELPER)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class Reflected:
    def __init__(self, **properties):
        self.properties = properties

    def get_editor_property(self, key):
        return self.properties[key]

    def set_editor_property(self, key, value):
        self.properties[key] = value


class Node(Reflected):
    def __init__(self, name, klass, **properties):
        super().__init__(**properties)
        self.name, self.klass = name, klass

    def get_name(self):
        return self.name

    def get_class(self):
        return types.SimpleNamespace(get_name=lambda: self.klass)

    def get_path_name(self):
        return '/Transient/Material.' + self.name


def edge(node=None, output_index=0, mask=(0, 0, 0, 0, 0)):
    return Reflected(expression=node, output_index=output_index,
                     **dict(zip(('mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a'), mask)))


def native_pins(node):
    if node.klass == 'MaterialExpressionMultiply':
        inputs = [('A', node.properties['a']), ('B', edge())]
    elif node.klass == 'MaterialExpressionCustom':
        inputs = [(row.properties['input_name'], row.properties['input']) for row in node.properties['inputs']]
    else:
        inputs = []
    return dict(schemaVersion=1, readOnly=True, available=True, expression=node.get_path_name(),
        inputs=[dict(inputIndex=index, input_name=name,
            node=row.properties['expression'].get_name() if row.properties['expression'] else None,
            **{key: row.properties[key] for key in ('output_index', 'mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a')})
            for index, (name, row) in enumerate(inputs)],
        outputs=[copy.deepcopy(row.properties) for row in node.properties.get('outputs', [])])


NATIVE_API = types.SimpleNamespace(describe_material_expression_pins=lambda node: json.dumps(native_pins(node)))


def original_graph():
    return dict(nodes=dict(albedo=dict(klass='MaterialExpressionTextureSample',
        values=dict(texture='/original/ashlar', const_coordinate=0), pins=dict(coordinates=dict(node=None))),
        normal=dict(klass='MaterialExpressionMaterialFunctionCall', values=dict(material_function='/height'),
            pins=dict(height=dict(node='source_height', output_index=0, mask_r=1))),
        rough=dict(klass='MaterialExpressionConstant', values=dict(r=.9), pins={})),
        roots={key: dict(node='albedo' if key == 'MP_BASE_COLOR' else 'normal' if key == 'MP_NORMAL'
                        else 'rough' if key == 'MP_ROUGHNESS' else None,
                        output_index=0, mask=0, mask_r=0, mask_g=0, mask_b=0, mask_a=0)
               for key in study.ROOT_PROPERTIES}, materialProperties=dict(two_sided=False, tangent_space_normal=True))


class PrivateSurfaceTests(unittest.TestCase):
    def test_absent_switch_does_not_touch_missing_source(self):
        self.assertIsNone(study.selected_specs({}, 'arbitrary_legacy_mode', '/does/not/exist', '/missing', None))

    def test_unknown_selector_and_conflicting_mode_fail(self):
        for key in (study.SURFACE_SWITCH, study.MOUNTAIN_SWITCH):
            with self.assertRaises(ValueError):
                study.selected_specs({key: 'typo'}, 'base', '/missing', '/missing', None)
        with self.assertRaises(ValueError):
            study.selected_specs({study.SURFACE_SWITCH: study.SURFACE_MODE}, 'alpine_relief', '/missing', '/missing', None)

    def test_selected_surface_and_mountain_are_independent_and_signature_bound(self):
        # The repository test must not require private native/source artifacts.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'artifacts/unreal/aegis-citadel/aaaaaaaaaaaa'
            source.mkdir(parents=True)
            # Synthetic callback fixtures; private native files are not required.
            import importlib.util
            fixture_spec=importlib.util.spec_from_file_location('bridge_fixture',Path(__file__).with_name('unrealCitadelRetainedMountainBridge.test.py'))
            fixture=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture)
            candidate,inspection=fixture.synthetic_fixture()
            faces=source/'terrain-carves/hall-carve-rendered-faces.json';faces.parent.mkdir();faces.write_bytes(b'synthetic rendered-face binding')
            candidate['terrainCarves'][0]['nativeReadback']=dict(renderedFaces=dict(path='terrain-carves/hall-carve-rendered-faces.json',
                sha256=hashlib.sha256(faces.read_bytes()).hexdigest()))
            inspection['candidateSha256']=fixture.adapter.digest(candidate)
            (source / 'candidate.json').write_text(json.dumps(candidate))
            (source / 'blueprint.json').write_text(json.dumps(dict(routes=[dict(id='fixture_route')], objectives=[])))
            specs = {role: dict(baseColor='public/fixture_color.png', height='public/fixture_height.png')
                     for role in study.PALETTE}
            specs['carved_stone'] = dict(tint=[.32, .37, .44], roughness=.86, metallic=0)
            (source / 'assets-source.json').write_text(json.dumps(dict(materialSpecs=specs)))
            for name in ('aegis_citadel_stone_material.py', 'aegis_citadel_mountain_material.py',
                         'stage-aegis-citadel.py', 'citadel_stage_contract.py', 'world_actor_state.py',
                         'citadel_retained_mountain_bridge.py','citadel_retained_mountain_adapter.py'):
                file = root / 'scripts/unreal' / name
                file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(b'portable source binding')
            for name in ('Private/WarImportLibrary.cpp', 'Public/WarImportLibrary.h',
                         'Private/WarMaterialInstanceReadback.cpp','Private/WarVectorParameterReadback.cpp'):
                file = root / 'unreal/AegisWar/Source/AegisWarEditorTools' / name
                file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(b'portable native accessor binding')
            for name in ('fixture_color.png', 'fixture_height.png'):
                file = root / 'public' / name
                file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(b'portable texture binding')
            surface = study.selected_specs({study.SURFACE_SWITCH: study.SURFACE_MODE}, 'lumen_hardware', root, source, candidate)
            mountain = study.selected_specs({study.MOUNTAIN_SWITCH: study.MOUNTAIN_MODE}, 'base', root, source, candidate,inspection)
            both = study.selected_specs({study.SURFACE_SWITCH: study.SURFACE_MODE,
                study.MOUNTAIN_SWITCH: study.MOUNTAIN_MODE}, 'lumen_software', root, source, candidate,inspection)
            self.assertIsNone(surface['mountainMode'])
            self.assertIsNone(mountain['surfaceMode'])
            self.assertEqual(both['masonryPalette'], study.PALETTE)
            self.assertEqual(len({json.dumps(s, sort_keys=True) for s in (surface, mountain, both)}), 3)
            study.verify_bindings(root, both)
            for flag in ('geometryChanged', 'collisionChanged', 'fixturesChanged', 'exposureChanged',
                         'canopyChanged', 'rendererStateVerified', 'nativeMaterialsCompiled', 'visualApproved', 'releaseAcceptance'):
                self.assertIs(both[flag], False)
            self.assertIs(both['mountainTextureRepeatApplied'], False)
            self.assertIs(both['sculptureAddsNormalInput'], False)
            changed = copy.deepcopy(candidate)
            changed['sourceHashes']['arbitrary'] = '0' * 64
            with self.assertRaises(ValueError):
                study.selected_specs({study.SURFACE_SWITCH: study.SURFACE_MODE}, 'base', root, source, changed)

    def test_source_byte_drift_and_path_escape_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root / 'source'; p.write_bytes(b'first')
            spec = dict(sourceBindings={'source': hashlib.sha256(p.read_bytes()).hexdigest()})
            study.verify_bindings(root, spec)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                study.verify_bindings(root, spec)
            with self.assertRaises(ValueError):
                study.verify_bindings(root, dict(sourceBindings={'../outside': '0' * 64}))

    def test_exact_added_color_graph_preserves_every_source_node(self):
        before = original_graph()
        added = dict(private_color=dict(klass='MaterialExpressionCustom', values=dict(code=study.LUMINANCE_SHADER),
                                       pins=dict(Raw=dict(node='albedo'), Palette=dict(node='palette'))))
        after = copy.deepcopy(before); after['nodes'].update(added)
        after['roots']['MP_BASE_COLOR'] = dict(node='private_color', output_index=0,
            mask=0, mask_r=0, mask_g=0, mask_b=0, mask_a=0)
        study.checked_graph_change(before, after, added, 'private_color')
        self.assertEqual(before, original_graph())
        for mutate in (
            lambda g: g['nodes']['albedo']['values'].update(const_coordinate=1),
            lambda g: g['nodes']['normal']['pins']['height'].update(mask_r=0),
            lambda g: g['nodes']['rough']['values'].update(r=.4),
            lambda g: g['roots']['MP_NORMAL'].update(node=None),
            lambda g: g['materialProperties'].update(two_sided=True),
            lambda g: g['roots']['MP_WORLD_POSITION_OFFSET'].update(node='private_color'),
            lambda g: g['roots']['MP_BASE_COLOR'].update(node='albedo'),
            lambda g: g['roots']['MP_BASE_COLOR'].update(mask_r=1),
            lambda g: g['roots']['MP_CUSTOMIZED_UVS3'].update(node='private_color'),
            lambda g: g['roots']['MP_DISPLACEMENT'].update(node='private_color'),
        ):
            changed = copy.deepcopy(after); mutate(changed)
            with self.assertRaises(RuntimeError):
                study.checked_graph_change(before, changed, added, 'private_color')
        with self.assertRaises(RuntimeError):
            study.checked_graph_change(before, after, {'albedo': added['private_color']}, 'private_color')

    def test_native_pins_record_masks_and_reject_incomplete_wrong_or_reordered_evidence(self):
        source = Node('source_texture', 'MaterialExpressionTextureSample')
        node = Node('multiply', 'MaterialExpressionMultiply', a=edge(source, 0, (1, 1, 1, 1, 0)))
        document = native_pins(node)
        unreal = types.SimpleNamespace(WarImportLibrary=types.SimpleNamespace(
            describe_material_expression_pins=lambda unused: json.dumps(document)))
        actual = study._pins(unreal, node)['inputs'][0]
        self.assertEqual(actual['node'], 'source_texture')
        self.assertEqual([actual[k] for k in ('output_index', 'mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a')], [0, 1, 1, 1, 1, 0])
        for mutate in (lambda d: d.update(readOnly=False), lambda d: d.update(available=False),
                       lambda d: d.update(expression='/wrong'), lambda d: d['inputs'][0].pop('mask_b'),
                       lambda d: d['inputs'].reverse(), lambda d: d['inputs'][0].update(mask_b=True),
                       lambda d: d['inputs'][0].update(output_index=-1)):
            document = native_pins(node); mutate(document)
            with self.assertRaises(RuntimeError): study._pins(unreal, node)
        document = native_pins(node); document['inputs'][1]['output_index'] = -1
        self.assertEqual(study._pins(unreal, node)['inputs'][1]['output_index'], -1)
        document['inputs'][1]['output_index'] = -2
        with self.assertRaises(RuntimeError): study._pins(unreal, node)
        with self.assertRaises(ValueError):
            study._primitive(float('nan'))

    def test_graph_readback_rejects_unknown_nodes_without_silent_skips(self):
        node = Node('unknown', 'MaterialExpressionUnreviewed')
        unreal = types.SimpleNamespace(MaterialEditingLibrary=types.SimpleNamespace(get_material_expressions=lambda material: [node]))
        with self.assertRaises(RuntimeError):
            study.graph_readback(unreal, object())

    def test_original_masonry_graph_rejects_wrong_pins_texture_tint_uv_and_channels(self):
        Scalar = type('Scalar', (Node,), {})
        Vector = type('Vector', (Node,), {})
        Sample = type('Sample', (Node,), {})
        Multiply = type('Multiply', (Node,), {})
        texture = types.SimpleNamespace(get_path_name=lambda:
            '/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Textures/T_ashlar_baseColor.T_ashlar_baseColor')
        color = Sample('color', 'MaterialExpressionTextureSample'); color.texture = texture
        tint = Vector('tint', 'MaterialExpressionConstant3Vector')
        tint.constant = types.SimpleNamespace(r=.45, g=.5, b=.57, a=1)
        base = Multiply('multiply', 'MaterialExpressionMultiply', a=edge(color, 0, (1, 1, 1, 1, 0)))
        rough = Scalar('rough', 'MaterialExpressionConstant', r=.9)
        metal = Scalar('metal', 'MaterialExpressionConstant', r=0)
        roots = dict(MP_BASE_COLOR=base, MP_ROUGHNESS=rough, MP_METALLIC=metal)
        inputs = {base: [color, tint], color: [None, None]}
        library = types.SimpleNamespace(get_material_property_input_node=lambda material, prop: roots[prop],
            get_inputs_for_material_expression=lambda material, node: inputs[node])
        unreal = types.SimpleNamespace(WarImportLibrary=NATIVE_API, MaterialEditingLibrary=library, MaterialProperty=types.SimpleNamespace(
            MP_BASE_COLOR='MP_BASE_COLOR', MP_ROUGHNESS='MP_ROUGHNESS', MP_METALLIC='MP_METALLIC'),
            MaterialExpressionConstant=Scalar, MaterialExpressionConstant3Vector=Vector,
            MaterialExpressionTextureSample=Sample, MaterialExpressionMultiply=Multiply)
        spec = dict(baseColor='public/ashlar.png', roughness=.9, metallic=0, tint=[.45, .5, .57])
        with patch.object(study, 'graph_readback', return_value=original_graph()):
            study.source_nodes(unreal, object(), 'stone', spec, 'aaaaaaaaaaaa')
            cases = [
                (lambda: inputs.update({base: [tint, color]}), lambda: inputs.update({base: [color, tint]})),
                (lambda: setattr(color, 'texture', types.SimpleNamespace(get_path_name=lambda: '/wrong.texture')),
                 lambda: setattr(color, 'texture', texture)),
                (lambda: setattr(tint.constant, 'r', .8), lambda: setattr(tint.constant, 'r', .45)),
                (lambda: base.properties['a'].properties.update(mask_b=0),
                 lambda: base.properties['a'].properties.update(mask_b=1)),
                (lambda: inputs.update({color: [tint]}), lambda: inputs.update({color: [None, None]})),
                (lambda: rough.properties.update(r=.2), lambda: rough.properties.update(r=.9)),
            ]
            for change, restore in cases:
                change()
                with self.assertRaises((RuntimeError, ValueError)):
                    study.source_nodes(unreal, object(), 'stone', spec, 'aaaaaaaaaaaa')
                restore()

    def test_missing_reflected_graph_property_fails_instead_of_omitting_evidence(self):
        node = Node('source', 'MaterialExpressionConstant')
        unreal = types.SimpleNamespace(WarImportLibrary=NATIVE_API, MaterialEditingLibrary=types.SimpleNamespace(
            get_material_expressions=lambda material: [node], get_material_expression_input_names=lambda node: [],
            get_inputs_for_material_expression=lambda material, node: []))
        with self.assertRaises(KeyError):
            study.graph_readback(unreal, object())

    def test_custom_shader_reads_actual_pin_channel_and_source(self):
        rgb = Reflected(output_name='RGB', mask=1, mask_r=1, mask_g=1, mask_b=1, mask_a=0)
        default = Reflected(output_name='', mask=0, mask_r=0, mask_g=0, mask_b=0, mask_a=0)
        source = Node('texture', 'MaterialExpressionTextureSample', outputs=[rgb])
        palette = Node('palette', 'MaterialExpressionConstant3Vector', outputs=[default])
        def execute(drift):
            shader = Node('new', 'MaterialExpressionCustom')
            class Library:
                @staticmethod
                def create_material_expression(material, klass): return shader
                @staticmethod
                def connect_material_expressions(node, output, target, pin):
                    for row in target.properties['inputs']:
                        if row.get_editor_property('input_name') == pin:
                            mask = (1, 1, 1, 1, 0) if output == 'RGB' else (0, 0, 0, 0, 0)
                            row.set_editor_property('input', edge(node, 0, mask))
                    return True
                @staticmethod
                def connect_material_property(node, output, prop):
                    if drift:
                        node.properties['inputs'][0].properties['input'].properties.update(drift)
                    return True
            unreal = types.SimpleNamespace(WarImportLibrary=NATIVE_API, MaterialEditingLibrary=Library, MaterialExpressionCustom=object,
                CustomInput=Reflected, CustomMaterialOutputType=types.SimpleNamespace(CMOT_FLOAT3='float3'),
                MaterialProperty=types.SimpleNamespace(MP_BASE_COLOR='baseColor'))
            return study._new_shader(unreal, object(), 'reviewed', study.LUMINANCE_SHADER,
                                     dict(Raw=(source, 'RGB'), Palette=(palette, '')))
        execute(None)
        for drift in ({'expression': palette}, {'output_index': 1}, {'mask_a': 1}, {'mask_g': 0}):
            with self.assertRaises(RuntimeError):
                execute(drift)

    def test_actor_material_binding_preserves_gameplay_transform_visibility_and_collision(self):
        before = dict(className='StaticMeshActor', transform=[0, 0, 0, 1], tags=['unchanged'],
            components=[dict(name='mesh', mesh='/original/mesh', collision='BlockAll', collisionEnabled='QueryAndPhysics',
                             visible=True, materials=['/original/stone.stone', '/original/gold.gold'])])
        mapping = {'/original/stone': '/owned/cool.cool'}
        after = copy.deepcopy(before); after['components'][0]['materials'][0] = '/owned/cool.cool'
        result = study.actor_binding_readback(before, after, mapping)
        self.assertEqual(result[0]['slot'], 0)
        for key, value in (('collision', 'NoCollision'), ('visible', False), ('mesh', '/other/mesh')):
            changed = copy.deepcopy(after); changed['components'][0][key] = value
            with self.assertRaises(RuntimeError): study.actor_binding_readback(before, changed, mapping)
        changed = copy.deepcopy(after); changed['transform'][0] = 1
        with self.assertRaises(RuntimeError): study.actor_binding_readback(before, changed, mapping)
        with self.assertRaises(RuntimeError): study.actor_binding_readback(before, before, mapping)

    def test_each_surface_role_needs_actual_component_coverage(self):
        readback = [dict(bindings=[dict(actualMaterial='/owned/a'), dict(actualMaterial='/owned/b')])]
        self.assertEqual(study.verify_role_coverage(readback, ['/owned/a', '/owned/b']), {'/owned/a': 1, '/owned/b': 1})
        with self.assertRaises(RuntimeError): study.verify_role_coverage(readback, ['/owned/a', '/owned/missing'])

    def test_sculpture_coverage_requires_actual_rendered_triangles_not_unused_slots(self):
        document = dict(schemaVersion=1, readOnly=True, available=True, valid=True, invalidValues=0,
            mesh='/source/sculpture.mesh', lod=0, policy='actual_render_index_order_oriented_triangle_corners',
            triangles=[dict(materialIndex=9), dict(materialIndex=9), dict(materialIndex=8)])
        self.assertEqual(study.checked_sculpture_faces(document, '/source/sculpture.mesh', 9), 2)
        for change in (dict(readOnly=False), dict(available=False), dict(valid=False), dict(invalidValues=False),
                       dict(invalidValues=1), dict(lod=1), dict(mesh='/wrong'), dict(triangles=[]),
                       dict(triangles=[dict(materialIndex=8)]), dict(triangles=[dict(materialIndex=True)])):
            changed = copy.deepcopy(document); changed.update(change)
            with self.assertRaises(RuntimeError):
                study.checked_sculpture_faces(changed, '/source/sculpture.mesh', 9)

    def test_all_five_named_sculptures_are_required(self):
        self.assertEqual(len(study.SCULPTURE_IDS), 5)
        with self.assertRaises(RuntimeError):
            study.sculpture_binding_readbacks(None, [], dict(sourceMaterialRoles=['carved_stone'],
                requiredSculptures=list(study.SCULPTURE_IDS)), object())

    def test_destinations_outside_exact_private_root_fail_before_duplication(self):
        for target in ('/Game/Capitals/aegis_capital', '/Game/WorldRebuild/AegisCitadel_wrong'):
            with self.assertRaises(RuntimeError):
                study.create_surfaces(None, target, '423a3d57fd65', {}, {'surfaceMode': study.SURFACE_MODE}, None)

    def test_color_only_study_has_no_geometry_uv_or_normal_mutation_calls(self):
        tree = ast.parse(HELPER.read_text())
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertFalse(attributes & {'set_static_mesh', 'set_collision_enabled', 'set_actor_transform',
                                     'set_actor_scale3d', 'MaterialExpressionTextureCoordinate'})
        self.assertNotIn('weather_carved_stone', {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)})
        self.assertEqual(set(study.PALETTE), {'stone', 'limestone', 'flagstone', 'paving_inlay'})


if __name__ == '__main__':
    unittest.main()
