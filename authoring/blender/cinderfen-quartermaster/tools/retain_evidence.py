"""Bind inspection inputs to the current build before running final gates."""
import hashlib,json
from pathlib import Path

WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
KEY='frontier_cinderfen_greenskin_quartermaster'
files=list((WORK/'tools').glob('inspect_*.py'))
files += [WORK/'tools'/name for name in ('test_exports.py','validate_inhabitants.mjs','run_quality.py','review_inhabitants.py','retain_evidence.py')]
files += [WORK/'foundation-provenance.json',WORK/'source/fitting-foundations.json',WORK/'source/foundation-inspection.json',WORK/'review/carrier-fit.json',WORK/'review/source-layer-preflight.json',WORK/'review/inhabitant.html']
records=[]
for path in sorted(set(files)):
    data=path.read_bytes()
    records.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
path=WORK/'review'/f'{KEY}_build.json';report=json.loads(path.read_text())
report['validationSourceFiles']=records
path.write_text(json.dumps(report,separators=(',',':'))+'\n')
print('Retained '+str(len(records))+' exact validation inputs.')
