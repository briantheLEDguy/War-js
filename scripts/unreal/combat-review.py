"""Make review previews from successful native combat captures, never replace receipts."""
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "unreal/AegisWar/Saved/CombatFluidityCapture"
OUTPUT = ROOT / "artifacts/unreal/combat-playtest/review"
PROFILES = {
    "civic_battle_prelate_m": "Battle Prelate",
    "civic_sunfire_templar_m": "Sunfire Templar",
    "mire_warbrute_m": "Warbrute",
    "civic_ember_arcanist_m": "Ember Arcanist",
    "riven_ruin_oracle_m": "Ruin Oracle",
    "riven_void_magister_m": "Void Magister",
}


def main():
    receipt = json.loads((SOURCE / "frames.json").read_text(encoding="utf-8-sig"))
    if receipt.get("gameplayPassed") is not True:
        raise ValueError("Native cycle capture did not pass; refusing successful review previews.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    for profile, title in PROFILES.items():
        for view in (0, 1):
            rows = sorted(
                (row for row in receipt["frames"] if row["file"].startswith(profile + "_cycle_")
                 and row["file"].endswith(f"_{view}.png")), key=lambda row: row["file"])
            if len(rows) < 48:
                raise ValueError(f"Incomplete full-cycle capture for {profile}, view {view}")
            frames = []
            for index, row in enumerate(rows):
                if row["file"] != f"{profile}_cycle_{index:04d}_{view}.png":
                    raise ValueError(f"Missing or unordered frame: {row['file']}")
                with Image.open(SOURCE / row["file"]) as source:
                    frames.append(source.convert("RGB").resize((360, 430), Image.Resampling.LANCZOS))
            # GIF timestamps use centiseconds. Distribute rounding error instead
            # of speeding every frame up from 83.33ms to 80ms.
            origin = rows[0]["worldTime"]
            ends = [round((row["worldTime"] - origin) * 100) * 10 for row in rows]
            ends.append(round((rows[-1]["worldTime"] - origin + 1 / 12) * 100) * 10)
            durations = [ends[index + 1] - ends[index] for index in range(len(rows))]
            if min(durations) <= 0:
                raise ValueError("Non-increasing native capture times")
            filename = f"{profile}_{view}.gif"
            frames[0].save(OUTPUT / filename, save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, disposal=2)
            sheet = Image.new("RGB", (360 * 4, 458 * 2), "#171717")
            draw = ImageDraw.Draw(sheet)
            for cell in range(8):
                index = round(cell * (len(frames) - 1) / 7)
                x, y = (cell % 4) * 360, (cell // 4) * 458
                sheet.paste(frames[index], (x, y))
                draw.text((x + 8, y + 435), f"{title} {rows[index]['worldTime'] - origin:.2f}s", fill="white")
            sheet.save(OUTPUT / f"{profile}_{view}_phases.jpg", quality=90)
            results.append({"profile": profile, "view": view, "frames": len(frames),
                            "durationMs": sum(durations), "preview": filename})
    (OUTPUT / "review.json").write_text(json.dumps({
        "sourceReceipt": str(SOURCE / "frames.json"), "previews": results,
        "subjectiveAcceptance": False,
        "notes": "Native playback with moving camera framing. Review previews do not grant platform, Steam, audio-mixer or release acceptance."
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"previews": len(results), "directory": str(OUTPUT)}))


if __name__ == "__main__":
    main()
