"""Finish an interrupted LOD2 review only after verifying the LOD0/1 checkpoint."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import reimport_review as review
path=ROOT/'review/reimport_report.json'
previous=json.loads(path.read_text())
assert previous['status']=='rendering_pending_visual_review'
assert set(previous['lods'])=={'0','1'} and len(previous['motion_frames'])==27
validation,hashes=review.check_files(ROOT/'runtime',ROOT/'runtime/validation_report.json',(0,1,2))
assert previous['model_hashes']==hashes
assert previous['validation_report_sha256']==review.digest(ROOT/'runtime/validation_report.json')
assert previous['runtime_report_sha256']==validation['stage_report_sha256']
assert previous['scene_source_sha256']==review.digest(ROOT/'source/scene.json')
for item in previous['evidence']+previous['motion_frames']:
    assert review.digest(ROOT/item['path'])==item['sha256'],item['path']
checkpoint=ROOT/'review/reimport_interrupted_report.json'
checkpoint.write_bytes(path.read_bytes())
sys.argv=['resume_reimport_review.py','--','--lods','2']
review.main()
finished=json.loads(path.read_text())
assert finished['status']=='rendered_pending_visual_review' and set(finished['lods'])=={'2'}
for field in ('validation_report_sha256','runtime_report_sha256','scene_source_sha256'):
    assert finished[field]==previous[field],field
previous['lods'].update(finished['lods'])
previous['evidence'].extend(finished['evidence'])
review.check_files(ROOT/'runtime',ROOT/'runtime/validation_report.json',(0,1,2))
previous.update(status='rendered_pending_visual_review',complete_evidence=True,
                resumed_checkpoint_sha256=review.digest(checkpoint),resume_policy='Verified exact input and image hashes before rendering only missing LOD2; retained actual LOD0/1 and 27 motion renders')
path.write_text(json.dumps(previous,indent=2)+'\n')
print('RESUMED_REIMPORT_COMPLETE',len(previous['evidence']),flush=True)
