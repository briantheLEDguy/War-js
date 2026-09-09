# Paused skylark draft — 2026-09-09

User explicitly moved animals last behind character models, equipment and
town/siege items. Root stopped animal work. No process remains active.

- `baseline/`: all three retained original prototype GLBs.
- `runtime/`: only a rebuilt v2 LOD0 candidate, unapproved.
- `masters/frontier_sunmeadow_skylark_v2.blend`: editable new candidate.
- `review/skylark_v2_build.json`: exact source/model/master hashes.
- Latest render batch: idle at phase 0 and fly at phase .25, quarter/profile.
- No Khronos, topology, full motion, LOD1/2, final visual or publication gates
  completed for v2. Do not mistake successful export for acceptance.

The new builder fixes first-action rotation recording by selecting Euler channels
before assigning bone matrices. This fix needs an actual imported idle-wing
span regression when resumed. The copied legacy prototype helpers are retained
for provenance; `build_skylark.py` is the new isolated path.
