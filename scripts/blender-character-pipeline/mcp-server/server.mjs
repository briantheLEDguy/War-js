/**
 * MCP server — exposes Blender character generation as Claude Code tools.
 *
 * Registered in .claude/settings.json under mcpServers.blender-character.
 * cwd for the server process is scripts/blender-character-pipeline/.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "child_process";
import { readFileSync, existsSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PIPELINE_ROOT = path.resolve(__dirname, "..");

// Load config relative to pipeline root
const configPath = path.join(PIPELINE_ROOT, "config.json");
if (!existsSync(configPath)) {
  process.stderr.write(`ERROR: config.json not found at ${configPath}\n`);
  process.exit(1);
}
const config = JSON.parse(readFileSync(configPath, "utf8"));

const BLENDER_PATH  = config.blenderPath ?? "/usr/bin/blender";
const SCRIPT_PATH   = path.join(PIPELINE_ROOT, "blender", "generate_character.py");
const SPEC_PATH     = path.join(PIPELINE_ROOT, "data", "character_spec.json");
// outputDir in config.json is relative to pipeline root
const OUTPUT_DIR    = path.resolve(PIPELINE_ROOT, config.outputDir ?? "../../public/assets/models");

const RACES = ["empire", "dwarf", "high_elf", "chaos", "greenskin", "dark_elf"];

// Default career per race (used by generate_all_characters)
const DEFAULT_CAREERS = {
  empire:    "Warrior Priest",
  dwarf:     "Ironbreaker",
  high_elf:  "Swordmaster",
  chaos:     "Chosen",
  greenskin: "Black Orc",
  dark_elf:  "Blackguard",
};

// All 24 careers
const ALL_CAREERS = {
  empire:    ["Bright Wizard", "Witch Hunter", "Knight of the Blazing Sun", "Warrior Priest"],
  dwarf:     ["Ironbreaker", "Slayer", "Rune Priest", "Engineer"],
  high_elf:  ["Swordmaster", "White Lion", "Archmage", "Shadow Warrior"],
  chaos:     ["Chosen", "Marauder", "Magus", "Zealot"],
  greenskin: ["Black Orc", "Squig Herder", "Shaman", "Choppa"],
  dark_elf:  ["Witch Elf", "Blackguard", "Sorceress", "Disciple of Khaine"],
};

function careerSlug(career) {
  return career.toLowerCase().replace(/\s+/g, "_");
}

function defaultOutputName(race, career) {
  return `character_${race}_${careerSlug(career)}.glb`;
}

// ── Blender runner ──────────────────────────────────────────────────────────

function runBlender(race, career, outputName) {
  return new Promise((resolve) => {
    const outPath = path.join(OUTPUT_DIR, outputName ?? defaultOutputName(race, career));

    if (!existsSync(BLENDER_PATH)) {
      resolve({
        content: [{
          type: "text",
          text: `ERROR: Blender not found at "${BLENDER_PATH}". ` +
                `Update blenderPath in scripts/blender-character-pipeline/config.json.`,
        }],
        isError: true,
      });
      return;
    }

    const args = [
      "--background",
      "--python", SCRIPT_PATH,
      "--",
      "--race",   race,
      "--career", career,
      "--output", outPath,
      "--spec",   SPEC_PATH,
    ];

    process.stderr.write(`[blender-mcp] Running: ${BLENDER_PATH} ${args.join(" ")}\n`);

    execFile(BLENDER_PATH, args, { timeout: 120_000 }, (err, stdout, stderr) => {
      if (err) {
        resolve({
          content: [{
            type: "text",
            text: `ERROR generating ${race}/${career}:\n${stderr || err.message}`,
          }],
          isError: true,
        });
      } else {
        resolve({
          content: [{
            type: "text",
            text: `OK: ${outPath}\n\n${stdout.split("\n").filter(l => l.startsWith("[WAR]")).join("\n")}`,
          }],
        });
      }
    });
  });
}

// ── MCP server setup ────────────────────────────────────────────────────────

const server = new Server(
  { name: "blender-character", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "generate_character",
      description:
        "Generate a rigged, animated .glb character model using Blender for a given " +
        "Warhammer Online race and career. Outputs to public/assets/models/.",
      inputSchema: {
        type: "object",
        properties: {
          race: {
            type: "string",
            enum: RACES,
            description: "Character race",
          },
          career: {
            type: "string",
            description:
              "Full career name exactly as in WAR (e.g. 'Warrior Priest', 'Black Orc')",
          },
          outputName: {
            type: "string",
            description:
              "Optional output filename override (e.g. 'character_empire_wp.glb'). " +
              "Defaults to character_<race>_<career_slug>.glb",
          },
        },
        required: ["race", "career"],
      },
    },
    {
      name: "generate_all_characters",
      description:
        "Generate .glb models for all 24 WAR careers (one per race/career combination). " +
        "Runs Blender sequentially — expect this to take several minutes.",
      inputSchema: {
        type: "object",
        properties: {
          racesOnly: {
            type: "array",
            items: { type: "string", enum: RACES },
            description: "Optional: limit generation to specific races",
          },
        },
      },
    },
    {
      name: "list_generated_models",
      description: "List which character .glb files have already been generated.",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;

  if (name === "generate_character") {
    return runBlender(args.race, args.career, args.outputName ?? null);
  }

  if (name === "generate_all_characters") {
    const races = (args.racesOnly && args.racesOnly.length > 0)
      ? args.racesOnly
      : RACES;

    const results = [];
    for (const race of races) {
      for (const career of ALL_CAREERS[race]) {
        process.stderr.write(`[blender-mcp] Generating ${race}/${career}...\n`);
        const result = await runBlender(race, career, null);
        results.push(`${race}/${career}: ${result.isError ? "FAILED" : "OK"}`);
      }
    }

    return {
      content: [{
        type: "text",
        text: results.join("\n"),
      }],
    };
  }

  if (name === "list_generated_models") {
    const { readdirSync } = await import("fs");
    let files = [];
    try {
      files = readdirSync(OUTPUT_DIR)
        .filter(f => f.startsWith("character_") && f.endsWith(".glb"))
        .sort();
    } catch {
      // output dir doesn't exist yet
    }

    const generated = new Set(files);
    const lines = [];
    for (const race of RACES) {
      for (const career of ALL_CAREERS[race]) {
        const expected = defaultOutputName(race, career);
        lines.push(`${generated.has(expected) ? "✓" : "✗"} ${expected}`);
      }
    }

    return {
      content: [{
        type: "text",
        text: `Generated models in ${OUTPUT_DIR}:\n\n${lines.join("\n")}`,
      }],
    };
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

// ── Start ───────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write("[blender-mcp] Server ready\n");
