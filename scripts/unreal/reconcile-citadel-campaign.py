"""Update private preparation metadata; never rewrite Content or canonical receipts."""
import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import package_file
from citadel_routing_reconciliation import reconciled_manifest

digest = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision', required=True)
parser.add_argument('--network-evidence', required=True)
args = parser.parse_args()
if not re.fullmatch('[a-f0-9]{12}', args.revision):
    raise ValueError('An explicit private revision is required')
directory = ROOT / 'artifacts/unreal/aegis-citadel' / args.revision
receipt = directory / 'publication-candidate.json'
evidence = (ROOT / args.network_evidence).resolve()
evidence.relative_to((ROOT / 'artifacts/unreal/world-portals/network').resolve())
if evidence.name != 'report.json':
    raise ValueError('A retained native streaming report is required')
original = receipt.read_bytes()
staged = json.loads(original)
if staged.get('revision') != args.revision or staged.get('retainedDependencyReconciliation'):
    raise ValueError('Preserve another or already reconciled preparation')
network = json.loads(evidence.read_text())
observed = {package: digest(package_file(ROOT, package)) for package in staged['manifest']['packageHashes']}
for hashes in (staged['packageHashes'], staged['sourceHashes']):
    if any(digest(package_file(ROOT, package)) != expected for package, expected in hashes.items()):
        raise ValueError('A protected preparation or source package changed')
updated, changes = reconciled_manifest(staged, network, observed)
if not changes:
    raise ValueError('No stale retained-zone hashes require reconciliation')
backup = directory / 'publication-candidate-before-routing-reconciliation.json'
if backup.exists():
    raise ValueError('Preserve the existing reconciliation backup')
backup.write_bytes(original)
updated['retainedDependencyReconciliation'] = dict(version=1,
    recordedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    originalPreparationSha256=digest(backup),
    streamingEvidence=dict(file=evidence.relative_to(ROOT).as_posix(), sha256=digest(evidence)),
    changes=changes, nativePackagesRewritten=False, canonicalReceiptsRewritten=False,
    traversalAcceptance=False, productionAdmission=False)
if ({package: digest(package_file(ROOT, package)) for package in observed} != observed
        or receipt.read_bytes() != original):
    raise ValueError('Native packages or preparation changed during reconciliation')
temporary = directory / 'publication-candidate.reconciliation.tmp'
temporary.write_text(json.dumps(updated, indent=2) + '\n')
temporary.replace(receipt)
print(json.dumps(dict(reconciled=True, revision=args.revision, changes=changes,
                     nativePackagesRewritten=False, canonicalReceiptsRewritten=False)))
