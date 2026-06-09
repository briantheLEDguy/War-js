/**
 * MCP server exposing the manifest-first Blender asset pipeline.
 *
 * cwd for the server process is scripts/blender-character-pipeline/.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PIPELINE_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(PIPELINE_ROOT, "..", "..");
const TOOL_DIR = path.join(PIPELINE_ROOT, "tools");
const BLUEPRINT_DIR = path.join(PIPELINE_ROOT, "data", "asset-blueprints");
const MODEL_DIR = path.join(REPO_ROOT, "public", "assets", "models");

function runNodeTool(script, args = [], timeout = 600_000) {
  return new Promise((resolve) => {
    execFile(
      process.execPath,
      [path.join(TOOL_DIR, script), ...args],
      { cwd: PIPELINE_ROOT, timeout },
      (err, stdout, stderr) => {
        resolve({
          content: [{
            type: "text",
            text: `${stdout.trim()}${stderr.trim() ? `\n${stderr.trim()}` : ""}`.trim(),
          }],
          isError: Boolean(err),
        });
      },
    );
  });
}

function readBlueprints() {
  if (!existsSync(BLUEPRINT_DIR)) return [];
  return readdirSync(BLUEPRINT_DIR)
    .filter((file) => file.endsWith(".asset.json"))
    .sort()
    .map((file) => {
      const filePath = path.join(BLUEPRINT_DIR, file);
      const blueprint = JSON.parse(readFileSync(filePath, "utf8"));
      return { filePath, blueprint };
    });
}

function generatedSummary() {
  const lines = [];
  for (const { blueprint } of readBlueprints()) {
    const outPath = path.join(MODEL_DIR, blueprint.output.model);
    const qcPath = outPath.replace(/\.glb$/i, ".qc.json");
    const exists = existsSync(outPath);
    const qc = existsSync(qcPath);
    const qcState = qc
      ? (JSON.parse(readFileSync(qcPath, "utf8")).qcPassed === true ? "PASS" : "FAIL")
      : "--";
    const size = exists ? `${(statSync(outPath).size / (1024 * 1024)).toFixed(2)} MB` : "-";
    lines.push(
      `${exists ? "OK" : "MISSING"} ${qcState} ${blueprint.category.padEnd(9)} ` +
      `${blueprint.assetId.padEnd(42)} ${blueprint.output.model} ${size}`,
    );
  }
  return lines.join("\n");
}

const server = new Server(
  { name: "blender-character", version: "2.0.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_asset_blueprints",
      description: "List manifest-first asset blueprints and generated output status.",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "generate_asset",
      description:
        "Generate one asset from its neutral manifest assetId, profileKey, itemKey, staticKey, output filename, or manifest filename.",
      inputSchema: {
        type: "object",
        properties: {
          ref: {
            type: "string",
            description: "assetId/profileKey/itemKey/staticKey/model filename/manifest filename.",
          },
        },
        required: ["ref"],
      },
    },
    {
      name: "generate_asset_set",
      description: "Generate every asset in a manifest set. Defaults to the small smoke set.",
      inputSchema: {
        type: "object",
        properties: {
          setName: {
            type: "string",
            description: "Manifest set name, e.g. smoke, equipment, characters, human_hero_set.",
          },
        },
      },
    },
    {
      name: "validate_asset",
      description: "Validate all asset manifests and asset-index references.",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "list_generated_assets",
      description: "List manifest outputs, file presence, size, and QC sidecar presence.",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;

  if (name === "list_asset_blueprints") {
    return runNodeTool("list-blueprints.mjs", [], 60_000);
  }

  if (name === "generate_asset") {
    return runNodeTool("generate-asset.mjs", [args.ref], 900_000);
  }

  if (name === "generate_asset_set") {
    return runNodeTool("generate-all.mjs", [args.setName ?? "smoke"], 1_800_000);
  }

  if (name === "validate_asset") {
    return runNodeTool("validate-blueprints.mjs", [], 60_000);
  }

  if (name === "list_generated_assets") {
    return {
      content: [{ type: "text", text: generatedSummary() }],
    };
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write("[blender-mcp] Manifest-first server ready\n");
