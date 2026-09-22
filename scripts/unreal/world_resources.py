"""Validated source bindings for authored campaign gathering visuals."""
import math
import json
import re
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2]/'migration/world-resource-sources.json'


def validate_catalog_append(previous, candidate, source_catalog):
    """Permit reviewed additions only; no implicit reapproval of changed live bindings."""
    for key in ('schemaVersion','sourceContentSha256','productionAccepted'):
        if previous.get(key) != candidate.get(key): raise ValueError('Existing visual catalog revision changed')
    key = lambda row:(row['purpose'],row['zone'],row['entity'])
    old = {key(row):row for row in previous['bindings']}
    new = {key(row):row for row in candidate['bindings']}
    if len(old)!=len(previous['bindings']) or len(new)!=len(candidate['bindings']):
        raise ValueError('Duplicate visual catalog identity')
    if any(new.get(identity)!=row for identity,row in old.items()):
        raise ValueError('Existing visual binding changed or disappeared')
    if any(candidate['packageHashes'].get(package)!=digest for package,digest in previous['packageHashes'].items()):
        raise ValueError('Previously reviewed native package changed')
    reviewed = {(row['zone'],row['entity']):row for row in source_catalog['bindings']}
    for identity in new.keys()-old.keys():
        row = new[identity]; review = reviewed.get((row['zone'],row['entity']))
        if (row['purpose']!='resource' or not review or row['visualProp']!=review['visualProp']
                or row['sourceModel']!=review['model'] or row['sourceSha256']!=review['sourceSha256']):
            raise ValueError('New visual binding lacks its exact source review')


def resource_bindings(source, registry, catalog=None):
    catalog = json.loads(CATALOG.read_text()) if catalog is None else catalog
    if catalog.get('schemaVersion') != 1 or catalog.get('reviewState') != 'development' or catalog.get('productionAccepted') is not False:
        raise ValueError('Resource source catalog is not an explicit development review')
    reviewed = {}
    for row in catalog['bindings']:
        key = (row['zone'],row['entity'])
        if key in reviewed or not re.fullmatch('[a-f0-9]{64}',row['sourceSha256']):
            raise ValueError('Invalid or duplicate resource source binding')
        reviewed[key] = row
    nodes, props = source.get('resourceNodes', []), source.get('props', [])
    if len({n['id'] for n in nodes}) != len(nodes) or len({p['id'] for p in props}) != len(props):
        raise ValueError('Duplicate resource or visual identity')
    by_id = {p['id']: p for p in props}
    ready, pending = [], []
    for node in nodes:
        prop = by_id.get(node.get('visualPropId'))
        if not prop:
            raise ValueError('Resource visual is missing: ' + node['id'])
        review = reviewed.get((source['id'],node['id']))
        if not review:
            pending.append({'zone': source['id'], 'id': node['id'], 'reason': 'native-resource-visual-pending'})
            continue
        binding = registry.get(review['assetKey'], {})
        if (binding.get('approvalState') != 'approved' or binding.get('runtimeReady') is not True
                or binding.get('model') != review['model'] or binding.get('modelSha256') != review['sourceSha256']
                or prop['id'] != review['visualProp'] or prop['kind'] != review['sourceKind']
                or node['kind'] != review['resourceKind']
                or prop.get('heightMode','terrain') != review['heightMode']
                or (prop.get('model') is not None and prop['model'] != review['model'])):
            raise ValueError('Resource source binding changed: ' + node['id'])
        for axis in ('x', 'y', 'z'):
            a, b = node.get(axis, 0), prop.get(axis, 0)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not math.isfinite(a+b) or abs(a-b) > 1e-6:
                raise ValueError('Resource and visual positions differ: ' + node['id'])
        ready.append({'zone': source['id'], 'node': node, 'prop': prop, 'model': review['model'],
                      'assetKey':review['assetKey'], 'sourceSha256': binding['modelSha256']})
    return ready, pending
