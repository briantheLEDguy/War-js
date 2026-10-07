"""Development selection changes never grant siege or release acceptance."""
import copy
import re


def integration_packages(revision):
    if not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{12}', revision):
        raise ValueError('An exact saved decor revision is required')
    prefix = '/Game/WorldRebuild/AegisCitadel_' + revision
    return dict(map=prefix + '/CampaignCandidate', routing=prefix + '/CampaignRoutingCandidate',
                population=prefix + '/Layers/Residents', scenario=prefix + '/SiegeCombinedCandidate')


def selected_config(original, previous, selected):
    """Replace only the two verified old defaults, preserving all other bytes."""
    replacements = {}
    for key in (b'GameDefaultMap=', b'EditorStartupMap='):
        old, new = key + previous.encode('ascii'), key + selected.encode('ascii')
        lines = [line for line in original.splitlines() if line.startswith(key)]
        if lines != [old]:
            raise ValueError('Startup map changed or is duplicated')
        replacements[old] = new
    # Earlier comments and longer substrings must not consume the replacement.
    return b''.join(replacements.get(line.rstrip(b'\r\n'), line.rstrip(b'\r\n'))
                    + line[len(line.rstrip(b'\r\n')):] for line in original.splitlines(keepends=True))


def development_manifests(build, manifest, receipt, city, gameplay, packages, hashes):
    """Preserve unrelated zones/services and invalidate every transferred approval."""
    if (receipt.get('schemaVersion') != 1 or receipt.get('campaignMap') != build.get('map')
            or manifest.get('mainMap') != build.get('map') or manifest.get('layer') != build.get('layer')
            or [row.get('id') for row in receipt.get('cities', [])] != ['aegis_capital', 'riftspire_capital']
            or city.get('id') != 'aegis_capital' or not city.get('sceneryLevels')
            or city.get('origin') != receipt['cities'][0].get('origin')):
        raise ValueError('Exact prior shared city/routing bindings are required')
    prior = receipt['cities'][0]
    rows = [row for row in manifest.get('zones', []) if row.get('id') == 'aegis_capital']
    if (len(rows) != 1 or rows[0].get('cityDefinition') != prior['definition']
            or rows[0].get('cityRevision') != prior['revision']
            or sorted(rows[0]['levels'].values()) != sorted(prior['sceneryLevels'] + prior['gameplayLevels'])
            or any(level not in gameplay for level in prior['gameplayLevels'])
            or len(set(city['sceneryLevels'] + gameplay)) != len(city['sceneryLevels'] + gameplay)
            or packages['population'] not in gameplay):
        raise ValueError('Original services or unique scenery/gameplay bindings changed')
    for package in [packages['map'], packages['routing'], city['definition'], *city['sceneryLevels'], *gameplay]:
        if not re.fullmatch('[a-f0-9]{64}', hashes.get(package, '')):
            raise ValueError('Complete saved native package hashes are required')
    updated_city = copy.deepcopy(city)
    updated_city['gameplayLevels'] = list(gameplay)
    updated_city['packageHashes'] = {package: hashes[package]
        for package in [city['definition'], *city['sceneryLevels'], *gameplay]}
    updated_receipt = copy.deepcopy(receipt)
    updated_receipt.update(campaignMap=packages['map'],
        campaignHashes={packages[key]: hashes[packages[key]] for key in ('map', 'routing')},
        releaseApproved=False, developmentOnly=True)
    updated_receipt['cities'][0] = updated_city
    updated_manifest = copy.deepcopy(manifest)
    updated_zone = next(row for row in updated_manifest['zones'] if row['id'] == 'aegis_capital')
    updated_zone.update(cityDefinition=city['definition'], cityRevision=city['revision'],
        levels={**{'scenery_' + str(i): value for i, value in enumerate(city['sceneryLevels'])},
                **{'gameplay_' + str(i): value for i, value in enumerate(gameplay)}})
    updated_manifest.update(mainMap=packages['map'], layer=packages['routing'], mainSha256=hashes[packages['map']],
                            developmentOnly=True, productionAccepted=False)
    for package in [build['layer'], *prior['sceneryLevels']]:
        updated_manifest['packageHashes'].pop(package, None)
    updated_manifest['packageHashes'].update(updated_city['packageHashes'])
    updated_manifest['packageHashes'].update({packages[key]: hashes[packages[key]] for key in ('map', 'routing')})
    updated_build = copy.deepcopy(build)
    updated_build.update(map=packages['map'], layer=packages['routing'], capitalSha256After=hashes[packages['map']],
                         runtimeTraversalVerified=False, visualApproved=False, developmentOnly=True)
    return updated_build, updated_manifest, updated_receipt
