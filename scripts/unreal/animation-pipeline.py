"""Run a character's local animation recipe, stopping on the first failed stage.

python scripts/unreal/animation-pipeline.py battle-prelate-two-handed --review
Use --from-stage verify for a read-only recheck of saved native assets.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    recipes = sorted(path.stem for path in (TOOLS / "animation-recipes").glob("*.json"))
    parser.add_argument("recipe", choices=recipes)
    parser.add_argument("--from-stage", default="prepare")
    parser.add_argument("--review", action="store_true", help="Also render native front/side review frames")
    parser.add_argument("--unreal", default=os.environ.get("WAR_UNREAL_EDITOR", "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"))
    parser.add_argument("--blender", default=shutil.which("blender") or "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe")
    args = parser.parse_args()
    recipe = json.loads((TOOLS / "animation-recipes" / (args.recipe + ".json")).read_text())
    names = [stage["name"] for stage in recipe["stages"]]
    if recipe["schemaVersion"] != 1 or args.from_stage not in names:
        parser.error("Unsupported recipe or starting stage")
    output = (ROOT / recipe["output"]).resolve()
    output.relative_to(ROOT / "artifacts")
    output.mkdir(parents=True, exist_ok=True)
    for stage in recipe["stages"][names.index(args.from_stage):]:
        if stage["name"] in ("review", "preview") and not args.review:
            continue
        script = (TOOLS / stage["script"]).resolve()
        script.relative_to(TOOLS)
        if stage["engine"] == "blender":
            command = [args.blender, "--background", "--python-exit-code", "1", "--python", str(script)]
        elif stage["engine"] == "python":
            command = [sys.executable, str(script)]
        else:
            command = [args.unreal, str(ROOT / "unreal/AegisWar/AegisWar.uproject"), "-unattended",
                       "-AllowCommandletRendering" if stage["engine"] == "unreal-render" else "-nullrhi",
                       "-run=pythonscript", "-script=" + str(script), "-abslog=" + str(output / (stage["name"] + ".log"))]
        log = output / (stage["name"] + "-console.log")
        print(f'{recipe["character"]}: {stage["name"]} ({log.relative_to(ROOT)})', flush=True)
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode:
            raise SystemExit(f'{stage["name"]} failed ({result.returncode}); inspect {log}')
    print("Recipe complete. Native imports remain development-only until visual acceptance.")


if __name__ == "__main__":
    main()
