"""Reconcile retained zone hashes only against exact saved streaming evidence."""
import copy
import re


def reconciled_manifest(staged, network, observed):
    if (staged.get('published') is not False or network.get('passed') is not True
            or network.get('twoClientStreaming') is not True or network.get('productionAccepted') is not False
            or network.get('map') != staged.get('baseBuild', {}).get('map')):
        raise ValueError('Exact retained campaign streaming evidence is required')
    expected = staged.get('manifest', {}).get('packageHashes')
    if (not isinstance(expected, dict) or not expected or set(observed) != set(expected)
            or any(not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value)
                   for value in [*expected.values(), *observed.values()])):
        raise ValueError('Complete observed campaign package hashes are required')
    retained = {package for zone in staged.get('baseManifest', {}).get('zones', [])
                if zone.get('id') not in ('aegis_capital', 'riftspire_capital')
                for package in zone.get('levels', {}).values()}
    changes = []
    result = copy.deepcopy(staged)
    for package, before in expected.items():
        after = observed[package]
        if before == after:
            continue
        if package not in retained or network.get('packageHashes', {}).get(package) != after:
            raise ValueError('Preserve unverified or non-zone native package changes: ' + package)
        changes.append(dict(package=package, recordedSha256=before, retainedSha256=after))
        result['manifest']['packageHashes'][package] = after
    return result, changes
