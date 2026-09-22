"""Pure ownership and manifest rules for the native campaign's independently loaded levels."""
import hashlib
import json
import math

BATCHES = [
    ['sunmeadow_march', 'cinderfen_outskirts', 'wardens_hollow', 'cindermaw_pit'],
    ['brightfen_approach', 'ashen_steppe', 'mireglass_den', 'ashfang_pit'],
    ['greybrook_crossing', 'bleakroot_causeway', 'briarwatch_den', 'rotwreath_nest'],
    ['glassriver_ford', 'gorepine_pass', 'glassriver_depths', 'gorepine_warrens'],
    ['ironwood_redoubt', 'vilemere_heights', 'stormbarrow_lair', 'nightglass_hollow'],
    ['highvale_rampart', 'obsidian_scar', 'highvale_sanctum', 'obsidian_maw'],
    ['aegis_crownworks', 'rift_crownworks'], ['dawnline_expanse', 'shatterline_expanse'],
    ['aegis_gate_fortress', 'rift_gate_fortress'], ['aegis_capital', 'riftspire_capital'],
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def owner_zone(zones, position):
    if len(position) != 3 or not all(math.isfinite(value) for value in position):
        raise ValueError('Invalid actor position')
    matches = [zone['id'] for zone in zones if all(
        abs(position[axis] - zone['origin'][axis]) <= zone['size'] * 50 for axis in (0, 1))]
    if len(matches) != 1:
        raise ValueError('Actor has missing or ambiguous zone ownership: ' + str(position))
    return matches[0]


def validate_partition(before, after):
    """Level/name changes are excluded upstream; authored state must survive exactly."""
    if set(before) != set(after):
        raise ValueError('Partition changed actor identities')
    changed = [key for key in before if before[key] != after[key]]
    if changed:
        raise ValueError('Partition changed actor state: ' + ', '.join(changed[:10]))


def zone_manifest(plan, receipt, levels, actor_counts, source_maps):
    expected = {zone for batch in BATCHES for zone in batch}
    if {row['id'] for row in plan['zones']} != expected or set(levels) != expected:
        raise ValueError('Manifest must cover the entire original campaign')
    zones = []
    for row in plan['zones']:
        zone = row['id']
        source = source_maps[zone]
        routes = [route for route in plan['routes'] if route['zoneId'] == zone]
        if not routes:
            raise ValueError('Zone has no routes: ' + zone)
        bindings = [{'id':item['id'], 'parts':item.get('parts', 1)}
                    for item in receipt['scenery'] if item['zone'] == zone]
        pending = {key: [item for item in receipt.get(key, []) if item['zone'] == zone]
                   for key in ('pendingScenery', 'pendingGameplay', 'pendingResources')}
        zones.append({
            'id':zone, 'name':row['name'], 'batch':next(i+1 for i,b in enumerate(BATCHES) if zone in b),
            'sourceSha256':plan['sourceHashes'][zone], 'origin':row['origin'], 'levels':levels[zone],
            'actorCount':actor_counts[zone], 'dependencies':sorted({route['targetZoneId'] for route in routes}),
            'routes':[route['id'] for route in routes], 'sceneryBindings':bindings,
            'sourceContentCounts':{key:len(source.get(key, [])) for key in (
                'props', 'npcs', 'enemies', 'resourceNodes', 'craftingStations', 'rvrObjectives')},
            'artDirection':source.get('artDirection'), 'outstanding':pending,
            'acceptance':{'environment':'partial', 'gameplay':'partial', 'traversal':'pending',
                          'visual':'pending', 'network':'pending', 'release':'blocked'},
        })
    return {'schemaVersion':1, 'developmentOnly':True, 'zones':zones, 'productionAccepted':False}
