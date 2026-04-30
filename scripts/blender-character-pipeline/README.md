# Blender Character Pipeline

Generates rigged, animated `.glb` character models for War-js using Blender in headless mode. Models are output to `public/assets/models/` and loaded automatically by the game's `AssetLoader`.

---

## Prerequisites

- **Blender 3.6+** (tested on 4.x) — [blender.org](https://www.blender.org/download/)
- **Node.js 18+** — for the MCP server

### Install Blender

| Platform | Default path |
|----------|-------------|
| Linux    | `/usr/bin/blender` (or install via `sudo snap install blender --classic`) |
| macOS    | `/Applications/Blender.app/Contents/MacOS/Blender` |
| Windows  | `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe` |

If Blender is at a non-standard location, update `config.json`:

```json
{
  "blenderPath": "/your/custom/path/blender",
  "outputDir": "../../public/assets/models",
  "animScale": 1.0
}
```

---

## Claude Code integration (MCP server)

The MCP server exposes three tools directly inside Claude Code conversations:

| Tool | Description |
|------|-------------|
| `generate_character` | Generate one career's `.glb` model |
| `generate_all_characters` | Generate all 24 career models sequentially |
| `list_generated_models` | Show which models exist vs. are still missing |

### Setup

```bash
cd scripts/blender-character-pipeline/mcp-server
npm install
```

The server is pre-registered in `.claude/settings.json`. Restart Claude Code to pick it up, then use it conversationally:

> "Generate a character model for a Dwarf Slayer"
> "Generate all Chaos career models"
> "Which character models have been generated so far?"

---

## Manual usage (without Claude Code)

Run Blender directly from the repo root:

```bash
blender --background \
  --python scripts/blender-character-pipeline/blender/generate_character.py \
  -- \
  --race dwarf \
  --career "Ironbreaker" \
  --output public/assets/models/character_dwarf_ironbreaker.glb \
  --spec scripts/blender-character-pipeline/data/character_spec.json
```

Generate all 24 models with a shell loop:

```bash
declare -A CAREERS=(
  [empire]="Bright Wizard,Witch Hunter,Knight of the Blazing Sun,Warrior Priest"
  [dwarf]="Ironbreaker,Slayer,Rune Priest,Engineer"
  [high_elf]="Swordmaster,White Lion,Archmage,Shadow Warrior"
  [chaos]="Chosen,Marauder,Magus,Zealot"
  [greenskin]="Black Orc,Squig Herder,Shaman,Choppa"
  [dark_elf]="Witch Elf,Blackguard,Sorceress,Disciple of Khaine"
)

BLENDER=/usr/bin/blender
SPEC=scripts/blender-character-pipeline/data/character_spec.json
SCRIPT=scripts/blender-character-pipeline/blender/generate_character.py

for race in "${!CAREERS[@]}"; do
  IFS=',' read -ra careers <<< "${CAREERS[$race]}"
  for career in "${careers[@]}"; do
    slug=$(echo "$career" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    out="public/assets/models/character_${race}_${slug}.glb"
    echo "Generating $race / $career → $out"
    "$BLENDER" --background --python "$SCRIPT" -- \
      --race "$race" --career "$career" --output "$out" --spec "$SPEC"
  done
done
```

---

## File naming convention

Generated models follow the pattern:
```
character_<race>_<career_slug>.glb
```

Where `career_slug` is the career name lowercased with spaces replaced by underscores:

```
character_empire_bright_wizard.glb
character_empire_witch_hunter.glb
character_empire_knight_of_the_blazing_sun.glb
character_empire_warrior_priest.glb
character_dwarf_ironbreaker.glb
character_dwarf_slayer.glb
...
```

The game (`src/game/Player.ts`) probes for the career-specific model first, then the race-level model, then falls back to the procedural Three.js primitive.

---

## Embedded animations

Each generated `.glb` includes these named animation clips:

| Clip | Frames | Loop |
|------|--------|------|
| `idle` | 60 | yes |
| `walk` | 30 | yes |
| `run` | 20 | yes |
| `combat_idle` | 80 | yes |
| `attack_melee` | 30 | no |
| `attack_ranged` | 40 | no |
| `cast` | 60 | no |
| `death` | 60 | no |
| `jump` | 40 | no |

Three.js `AnimationMixer` in `Player.ts` plays `idle` on load. Additional clip switching (walk/run/combat) can be added to `Player.update()`.

---

## Directory structure

```
scripts/blender-character-pipeline/
├── config.json              ← Blender path + output dir
├── README.md                ← this file
├── blender/
│   ├── generate_character.py  ← main Blender script (CLI entry point)
│   ├── rig_utils.py           ← armature creation + animation application
│   └── anim_library.py        ← keyframe data for all 9 animation clips
├── data/
│   └── character_spec.json    ← race/career → build params (colors, weapon, helmet)
└── mcp-server/
    ├── package.json
    └── server.mjs             ← MCP tool server
```

---

## Customizing character appearance

Edit `data/character_spec.json` to adjust any race or career's appearance. No Python changes needed — the spec is read at generation time.

Key fields per race:

| Field | Description |
|-------|-------------|
| `bodyScale` | `[x, y, z]` scale — `[1.05, 0.82, 1.05]` makes dwarves short/wide |
| `skinColor` | Hex skin tone |
| `armorColor` | Base armor hex |
| `trimColor` | Accent/trim hex |
| `beard` | `true` adds a beard mesh |
| `elfEars` | `true` adds pointed ears |

Key fields per career (inside `careers`):

| Field | Description |
|-------|-------------|
| `weapon` | `sword`, `hammer`, `staff`, `axe`, `dual_axes`, `bow`, `gun`, `greatsword`, `halberd`, etc. |
| `helmetStyle` | `open_face`, `full_visor`, `hood`, `brimhat`, `horned_full`, `mohawk`, `iron_bowl`, `bone_crown`, `spired_full`, `none`, etc. |
| `robeColor` | Hex for robe overlay — `null` for no robe |
| `armorColorOverride` | Per-career armor color override — `null` to use race default |
