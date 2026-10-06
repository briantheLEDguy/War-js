"""Receipt-only reconciliation after a witnessed private navigation transfer."""
import copy
import re


def updated_preparation(staged, journal, observed):
    revision = staged.get('revision', '')
    if not re.fullmatch('[a-f0-9]{12}', revision) or staged.get('published') is not False:
        raise ValueError('Only an unpublished private preparation may change')
    prefix = '/Game/WorldRebuild/AegisCitadel_' + revision
    packages = [prefix + '/CampaignCandidate', prefix + '/CampaignSiegeOverlay']
    if [staged.get('map'), staged.get('overlay')] != packages or journal.get('revision') != revision:
        raise ValueError('Navigation ownership must use the exact prepared pair')
    if staged.get('campaignNavigationOwnership') or journal.get('originalPackageHashes') != staged['packageHashes']:
        raise ValueError('Preserve changed or already reconciled preparation')
    if set(observed) != set(staged['packageHashes']) or any(
            observed[p] != h for p, h in staged['packageHashes'].items() if p not in packages):
        raise ValueError('Only the exact two private maps may change')
    if any(not re.fullmatch('[a-f0-9]{64}', observed[p]) or observed[p] == staged['packageHashes'][p]
           for p in packages):
        raise ValueError('Both transferred package bytes must have fresh hashes')
    if journal.get('newPackageHashes') != observed or journal.get('freshProcessVerified') is not True:
        raise ValueError('A separate native reload witness is required')
    rows = journal.get('reloadedActors', [])
    original = journal.get('transfer', {})
    if original.get('passed') is not True or original.get('rebuilt') is not False or len(rows) != 2:
        raise ValueError('Existing baked data must transfer without a rebuild')
    expected = {row['profile']: row for row in original.get('actors', [])}
    bounds = original.get('bounds', {})
    if (not bounds.get('before', '').startswith(packages[1] + '.')
            or not bounds.get('after', '').startswith(packages[0] + '.')):
        raise ValueError('The exact bounds must retain persistent navigation on future saves')
    if set(expected) != {'Default', 'SiegeConvoy'} or {row.get('profile') for row in rows} != set(expected):
        raise ValueError('Both distinct character and convoy profiles are required')
    for row in rows:
        old = expected[row['profile']]
        if (row.get('package') != packages[0] or row.get('actor') != old.get('after')
                or not isinstance(row.get('activeTiles'), int) or row['activeTiles'] <= 0
                or row['activeTiles'] != old.get('activeTiles')
                or not row.get('tileSnapshot') or row['tileSnapshot'] != old.get('tileSnapshot')):
            raise ValueError('Saved ownership and exact baked tile data must survive reload')
    updated = copy.deepcopy(staged)
    updated['packageHashes'] = observed.copy()
    updated['manifest']['mainSha256'] = observed[packages[0]]
    updated['manifest']['packageHashes'][packages[1]] = observed[packages[1]]
    updated['build']['capitalSha256After'] = observed[packages[0]]
    updated['build']['runtimeTraversalVerified'] = False
    updated['campaignNavigationOwnership'] = dict(version=1, verified=True,
        rebuilt=False, freshProcessVerified=True, changedPackages=packages,
        originalPackageHashes={p: staged['packageHashes'][p] for p in packages},
        packageHashes={p: observed[p] for p in packages},
        nativeGameVerified=False, convoyTraversalVerified=False, productionAdmission=False)
    return updated
