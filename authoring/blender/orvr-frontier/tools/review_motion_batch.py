"""Current-hash clean GLB pose sheets, rendered sequentially on two threads."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_motion

CASES = [
 ('frontier_battering_ram','ram_strike','0,.7,1.5'),
 ('frontier_oil_cauldron','oil_pour','0,1.4333333333,3.5'),
 ('frontier_field_catapult','catapult_fire','0,.3,.8'),
 ('frontier_field_catapult','catapult_reload','0,1.8,3.6'),
 ('frontier_keep_gate','gate_open','0,.65,1.3'),
 ('frontier_keep_gate','gate_close','0,.65,1.3'),
 ('frontier_draft_horse','walk','0,.25,.5,.75'),
 ('frontier_draft_horse','draft_trot','0,.1666666667,.3333333333,.5'),
]
for asset,clip,times in CASES:
    sys.argv=['review_motion.py','--','--asset',asset,'--clip',clip,'--times',times]
    review_motion.main()
