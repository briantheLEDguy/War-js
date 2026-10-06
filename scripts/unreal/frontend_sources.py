"""Frontend bindings must resolve the current shared city definitions, never snapshots."""
import json
from pathlib import Path
from shared_city_sources import digest, package_file, source_plan as shared_plan


def source_plan(root):
    return shared_plan(root)


def stale_reason(root, receipt):
    plan = source_plan(root)
    if receipt.get('schemaVersion') != 3 or receipt.get('sourcePlan') != plan:
        return 'Shared city routing or frontend bindings changed.'
    outputs = receipt.get('outputPackages', {})
    if '/Game/UI/Frontend/CapitalPresentation' not in outputs:
        return 'Frontend binding evidence is missing.'
    for package, expected in outputs.items():
        try:
            if digest(package_file(root, package)) != expected:
                return 'Changed native package: ' + package
        except ValueError:
            return 'Missing native package: ' + package
    return None


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[2]
    try:
        receipt_file = root / 'artifacts/unreal/frontend/build.json'
        receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
        reason = stale_reason(root, receipt)
        print(reason or 'Frontend uses the current shared cities.')
        sys.exit(1 if reason else 0)
    except (ValueError, KeyError, StopIteration, OSError) as error:
        print('Cannot resolve shared city sources: ' + str(error))
        sys.exit(2)
