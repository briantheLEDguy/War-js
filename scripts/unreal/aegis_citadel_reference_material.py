"""Bounded private comparisons; native frames are still required for approval."""
import copy

REFERENCE_MATERIAL_MODES = ('material_control', 'material_lighting_control')
MASONRY_PALETTE = dict(stone=[.20, .26, .34, 1], limestone=[.29, .35, .43, 1],
                      flagstone=[.40, .46, .54, 1], paving_inlay=[.24, .31, .40, 1])
CARVED_PALETTE = dict(baseColor=[.06, .072, .09, 1])


def reference_material_comparison(mode, fixtures):
    if mode not in REFERENCE_MATERIAL_MODES:
        raise ValueError('Unknown reference material comparison')
    requests = copy.deepcopy(fixtures)
    if mode == 'material_lighting_control':
        by_id = {row['id']: row for row in requests}
        if len(by_id) != len(requests) or not {'sun', 'soft_sky_fill', 'ambient_sky'}.issubset(by_id):
            raise ValueError('Exact named lighting fixtures are required')
        by_id['sun']['properties'].update(intensity=6500, temperature=5200, light_source_angle=3)
        by_id['soft_sky_fill']['properties'].update(intensity=650)
        by_id['ambient_sky']['properties'].update(intensity=.55)
    return requests, copy.deepcopy(CARVED_PALETTE), copy.deepcopy(MASONRY_PALETTE)


def reference_cloud_comparison(fixture):
    """Retain the signed canopy rather than falling back to Engine defaults."""
    if not isinstance(fixture, dict) or not isinstance(fixture.get('materialInstance'), dict):
        raise ValueError('The signed candidate canopy is required')
    instance = fixture['materialInstance']
    fields = (fixture.get('properties'), instance.get('scalarParameters'), instance.get('vectorParameters'))
    if any(not isinstance(field, dict) or not field for field in fields):
        raise ValueError('Complete candidate canopy properties and parameters are required')
    return tuple(copy.deepcopy(field) for field in fields)
