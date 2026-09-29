"""Shared source/placement contract for supplied capital and camp characters."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'shared/data/importedPopulation.json'
OUT = ROOT / 'artifacts/unreal/imported-population'
BASE = '/Game/Characters/PopulationImports'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger():
    data = json.loads(LEDGER.read_text())
    if data['schemaVersion'] != 1:
        raise ValueError('Unsupported imported population schema')
    keys = [row['key'] for row in data['models']]
    profiles = [row['profile'] for row in data['models']]
    if len(keys) != len(set(keys)) or len(profiles) != len(set(profiles)):
        raise ValueError('Duplicate imported model identity')
    rows = data['capitalReplacements'] + data['capitalAdditions'] + [r for c in data['camps'] for r in c['members']]
    identities = [(row['zone'], row['id']) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate population identity')
    if any(row['model'] not in keys for row in rows):
        raise ValueError('Unknown population model')
    return data


def models():
    return {row['key']: row for row in ledger()['models']}


def verify_sources():
    for row in models().values():
        source = (ROOT / row['source']).resolve()
        source.relative_to(ROOT / 'unreal/AegisWar/modelImport')
        if digest(source) != row['sha256']:
            raise ValueError('Supplied model changed: ' + row['source'])


def population_records(existing):
    """Merge a copy; retained service identities and source records stay unchanged."""
    data = ledger()
    replacements = {r['id']: r for r in data['capitalReplacements']}
    result = []
    for row in existing:
        replacement = replacements.get(row['id'])
        result.append({**row, 'zone': 'aegis_capital', **({'profile': models()[replacement['model']]['profile']} if replacement else {})})
    if set(replacements) - {r['id'] for r in existing}:
        raise ValueError('Capital replacement identity is missing')
    result.extend({**r, 'profile': models()[r['model']]['profile']} for r in data['capitalAdditions'])
    return result


def require_review(evidence, expected):
    """Admission is bound to exact generated content, never a source-only flag."""
    if evidence.get('ledgerSha256') != digest(LEDGER) or evidence.get('nativeSha256') != expected:
        raise ValueError('Population review is stale')
    for field in ('materials', 'equippedMotion', 'nativeVisual'):
        if evidence.get(field) is not True:
            raise ValueError('Population review is incomplete: ' + field)


def check_zone_ownership(previous, reviewed, current, allow_reconcile=False):
    """Even approved reconciliation may only save the exact reviewed owner revision."""
    if set(reviewed) != set(current) or any(current[p] != h for p,h in reviewed.items()):
        raise ValueError('Owner zone changed after review')
    changed = {p:dict(previous=previous.get(p),current=h) for p,h in reviewed.items() if previous.get(p)!=h}
    if changed and not allow_reconcile:
        raise ValueError('Edited owner zone packages require explicitly approved reconciliation')
    return changed
