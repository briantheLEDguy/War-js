"""Validate fresh physical and visual siege evidence against the installed city."""
import json
from shared_city_sources import digest, package_file, source_plan


def current_review(root):
    city = next(c for c in source_plan(root)['cities'] if c['id'] == 'aegis_capital')
    file = package_file(root, '/Game/Capitals/Siege/AegisCapital_Siege')
    review = json.loads((root/'artifacts/unreal/shared-cities/siege-review.json').read_text())
    if review.get('cityRevision') != city['revision'] or review.get('mapSha256') != digest(file):
        raise ValueError('Siege review is for a different city or overlay')
    def evidence(name):
        row = review[name]
        path = (root/row['path']).resolve()
        path.relative_to(root.resolve())
        if digest(path) != row['sha256']:
            raise ValueError('Changed siege evidence: ' + name)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    walk, convoy, client = (evidence(name) for name in ('traversal', 'convoy', 'client'))
    for report in (walk, convoy, client):
        if report.get('passed') is not True or any(report.get(k) != review[k] for k in ('cityRevision', 'mapSha256')):
            raise ValueError('Physical proof is failed or obsolete')
    if walk.get('routesCompleted') != 7 or len(walk.get('walkers', [])) != 12 or any(
            w.get('jumped') is not True or w.get('distanceCm', 0) < 1000 for w in walk['walkers']):
        raise ValueError('Complete twelve-character traversal is required')
    if convoy.get('checkpoints') != 3 or any(convoy.get(k) is not True for k in (
            'stoppedWithoutEscort', 'stoppedWithoutCrew', 'overlapRecoveredWithoutDamage', 'ramStrikeAdvanced', 'gateCollisionVerified')):
        raise ValueError('Convoy behavior evidence is incomplete')
    if len(convoy.get('vehicles', [])) != 2 or any(v.get('travelCm', 0) < 24000 for v in convoy['vehicles']):
        raise ValueError('Both vehicles must complete the physical route')
    if client.get('gateCollisionVerified') is not True or client.get('ownershipStandards') != 4 or client.get('engineersReady') != 4 or client.get('captures') != 4:
        raise ValueError('Replicated convoy evidence is incomplete')
    if review.get('visualReviewed') is not True or not review.get('visualNotes') or len(review.get('frames', [])) < 4:
        raise ValueError('Current rendered siege review is required')
    for row in review['frames']:
        path = (root/row['path']).resolve()
        path.relative_to(root.resolve())
        if digest(path) != row['sha256']:
            raise ValueError('Changed visual review frame')
    return city, review
