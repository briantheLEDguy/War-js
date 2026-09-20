"""Sequential, thread-capped checks of the current atomic three-LOD export."""
import subprocess,sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
BLENDER='C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
KEY='frontier_cinderfen_dark_elf_supply_officer'
for lod in range(3):
    checks=[('inspect_tool_clearance.py',[f'--lod={lod}']),
            ('inspect_equipment_attachment.py',[f'--lod={lod}']),
            ('inspect_arm_volume.py',[f'--lod={lod}',f'--source={WORK}/runtime/{KEY}_lod{lod}.glb',f'--report=arm-volume-lod{lod}.json']),
            ('inspect_export_motion.py',[f'--lod={lod}',f'--asset={KEY}']),
            ('inspect_garment_clearance.py',[f'--lod={lod}']),
            ('inspect_boot_welt.py',[f'--lod={lod}'])]
    for script,args in checks:
        log=WORK/'review'/f'{Path(script).stem}_lod{lod}.log'
        print(f'Checking LOD{lod}: {script}',flush=True)
        with log.open('w') as out:
            result=subprocess.run([BLENDER,'--background','--threads','2','--python-exit-code','1','--python',str(WORK/'tools'/script),'--',*args],stdout=out,stderr=subprocess.STDOUT)
        if result.returncode:
            print(log.read_text()[-3000:],flush=True);sys.exit(result.returncode)
subprocess.run(['node',str(WORK/'tools/validate_inhabitants.mjs')],check=True)
subprocess.run([sys.executable,str(WORK/'tools/test_exports.py')],check=True)
