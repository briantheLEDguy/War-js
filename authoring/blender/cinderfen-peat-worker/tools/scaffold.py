"""Retain a bounded snapshot of the published fitting implementation."""
from pathlib import Path
import hashlib,json
WORK=Path(__file__).resolve().parents[1]
SOURCE=WORK.parent/'frontier-population/tools'
names=['build_inhabitants.py','tailored_clothing.py','surface_garments.py','tailored_locomotion.py','export_tangents.py','apron_clearance.py','apron_details.py','surface_bindings.py','workwear_finish.py','fitted_boot_details.py','inspect_arm_volume.py','inspect_export_motion.py','review_inhabitants.py','validate_inhabitants.mjs']
records=[]
for name in names:
    origin=SOURCE/name;data=origin.read_bytes()
    target=WORK/'tools'/name
    if target.exists():continue
    target.write_bytes(data)
    records.append({'source':origin.relative_to(WORK.parents[2]).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'snapshot':target.relative_to(WORK).as_posix()})
(WORK/'source/fitting-foundations.json').write_text(json.dumps(records,indent=2)+'\n')
