/** Local-only MCP facade for the reviewed character asset pipeline. */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  GetPromptRequestSchema,
  ListPromptsRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { cancelModelJob, getModelJob } from "../tools/model-jobs.mjs";
import { recordModelReview, startWorkflowJob } from "../tools/model-workflow.mjs";
import { structuredError } from "../tools/workspace-paths.mjs";
import { getResource, listResources } from "../pipeline-tools/character-contract.mjs";
import { startCharacterStageJob } from "../pipeline-tools/stage-workflow.mjs";

const JOB_RESPONSE = {
  type: "object",
  properties: {
    jobId: { type: "string" },
    status: { type: "string" },
    progress: { type: "number" },
  },
};

const PROVENANCE_PROPERTIES = {
  provider: {
    type: "object",
    properties: {
      name: { type: "string", description: "Local/open-source tool or original authoring workflow." },
      taskId: { type: "string" },
      modelVersion: { type: "string" },
      seed: { type: ["integer", "string"] },
    },
    required: ["name", "modelVersion"],
  },
  license: {
    type: "object",
    properties: {
      name: { type: "string" },
      sourceUrl: { type: "string" },
      termsUrl: { type: "string" },
    },
    required: ["name", "sourceUrl"],
  },
  author: { type: "string" },
  promptSha256: { type: "string" },
  referenceSha256: { type: "array", items: { type: "string" } },
};

const tools = [
  {
    name: "assemble_base_character",
    description: "Validate a canonical body archetype and stage a base-character assembly plan around the shared skeleton/rest pose.",
    inputSchema: {
      type: "object",
      properties: {
        bodyFamily: { type: "string" },
        bodyVariant: { type: "string", enum: ["m", "f"] },
        bodyModel: { type: "string", description: "Optional workspace-relative GLB to inspect or use as the source body." },
      },
      required: ["bodyFamily", "bodyVariant"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "fit_wearable",
    description: "Stage a typed skinned or loose wearable fit. Rigid items are rejected and must use attach_rigid_item.",
    inputSchema: {
      type: "object",
      properties: {
        assetId: { type: "string" },
        slot: { type: "string" },
        kind: { type: "string", enum: ["skinned", "loose"] },
        method: { type: "string", enum: ["data_transfer_nearest_face_interpolated", "surface_deform", "cloth_pinned"] },
        sourceModel: { type: "string" },
        bodyFamily: { type: "string" },
        bodyVariant: { type: "string", enum: ["m", "f"] },
      },
      required: ["assetId", "slot", "kind", "method"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "apply_body_mask",
    description: "Stage a reversible body-region mask backed by a named vertex group and Mask modifier.",
    inputSchema: { type: "object", properties: { maskId: { type: "string" } }, required: ["maskId"] },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "attach_rigid_item",
    description: "Stage explicit socket/bone-parent attachment for rigid equipment with a named offset profile.",
    inputSchema: {
      type: "object",
      properties: {
        itemId: { type: "string" },
        slot: { type: "string", enum: ["weapon", "shield", "lantern", "pouch", "scabbard"] },
        socketId: { type: "string" },
        offsetProfile: { type: "string" },
        method: { type: "string", enum: ["bone_parent", "child_of"] },
      },
      required: ["itemId", "socketId"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "validate_pose_pack",
    description: "Validate a model against the canonical pose-pack/export structure before visual approval.",
    inputSchema: {
      type: "object",
      properties: { modelPath: { type: "string" }, posePackId: { type: "string", default: "core_v1" } },
      required: ["modelPath"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "render_turntable",
    description: "Stage deterministic turntable/four-view review for a model after pose validation.",
    inputSchema: {
      type: "object",
      properties: { modelPath: { type: "string" }, preset: { type: "string" }, posePackId: { type: "string", default: "core_v1" } },
      required: ["modelPath"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "export_asset",
    description: "Stage the canonical runtime GLB export contract. Promotion remains a separate human-reviewed operation.",
    inputSchema: {
      type: "object",
      properties: { modelPath: { type: "string" }, target: { type: "string", enum: ["glb"] }, profileId: { type: "string", default: "runtime_glb_v1" } },
      required: ["modelPath"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "create_body_family",
    description: "Prepare a pinned MPFB 2.0.16 body recipe, or ingest a body GLB generated locally from that recipe. No network or paid API is used.",
    inputSchema: {
      type: "object",
      properties: {
        bodyFamily: { type: "string", enum: ["civic_humanoid_v2", "mire_brutish_v1"] },
        bodyVariant: { type: "string", enum: ["m", "f"] },
        animationProfile: {
          type: "string",
          enum: ["unarmed", "battle_prelate_hammer"],
          default: "unarmed",
          description: "Canonical animation profile embedded in a locally generated body.",
        },
        sourceModel: { type: "string", description: "Optional workspace-relative GLB generated by local MPFB." },
        qcPath: { type: "string" },
        assetId: { type: "string" },
        outputModel: { type: "string" },
        runtime: { type: "object" },
        ...PROVENANCE_PROPERTIES,
      },
      required: ["bodyFamily", "bodyVariant"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "ingest_generated_candidate",
    description: "Copy a local GLB candidate into an immutable job workspace and record hashes, license, provider, family, skeleton, and draft lifecycle.",
    inputSchema: {
      type: "object",
      properties: {
        sourcePath: { type: "string" },
        qcPath: { type: "string" },
        assetId: { type: "string" },
        displayName: { type: "string" },
        category: { type: "string", enum: ["character", "body", "armor", "weapon", "jewel", "prop", "terrain"] },
        outputModel: { type: "string" },
        bodyFamily: { type: "string" },
        bodyVariant: { type: "string", enum: ["m", "f"] },
        skeletonId: { type: "string", default: "humanoid_game_v2" },
        bindPoseId: { type: "string", default: "a_pose_v2" },
        runtime: { type: "object" },
        ...PROVENANCE_PROPERTIES,
      },
      required: ["sourcePath", "assetId", "bodyFamily", "bodyVariant", "provider", "license"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "build_modular_set",
    description: "Validate and stage exactly nine independently segmented local armor modules. Fused candidates are rejected instead of silently promoted.",
    inputSchema: {
      type: "object",
      properties: {
        setId: { type: "string" },
        bodyFamily: { type: "string" },
        bodyVariant: { type: "string", enum: ["m", "f"] },
        skeletonId: { type: "string", default: "humanoid_game_v2" },
        bindPoseId: { type: "string", default: "a_pose_v2" },
        bodyModel: { type: "string" },
        provenance: {
          type: "object",
          properties: {
            provider: PROVENANCE_PROPERTIES.provider,
            license: PROVENANCE_PROPERTIES.license,
            author: PROVENANCE_PROPERTIES.author,
            promptSha256: PROVENANCE_PROPERTIES.promptSha256,
            referenceSha256: PROVENANCE_PROPERTIES.referenceSha256,
          },
          required: ["provider", "license"],
        },
        modules: {
          type: "object",
          description: "Keys: head, shoulders, chest, hands, waist, legs, feet, back, tabard.",
          additionalProperties: {
            type: "object",
            properties: {
              modelPath: { type: "string" },
              qcPath: { type: "string" },
              assetId: { type: "string" },
              outputModel: { type: "string" },
              itemKey: { type: "string" },
              displayName: { type: "string" },
              skinned: { type: "boolean" },
              coveredRegions: { type: "array", items: { type: "string" } },
            },
            required: ["modelPath", "qcPath"],
          },
        },
      },
      required: ["setId", "bodyFamily", "bodyVariant", "bodyModel", "modules", "provenance"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "validate_model_asset",
    description: "Run strict manifest/index/QC validation for a blueprint, or validate a workspace GLB against its hash-bound QC sidecar.",
    inputSchema: {
      type: "object",
      properties: {
        ref: { type: "string" },
        modelPath: { type: "string" },
        qcPath: { type: "string" },
        assetId: { type: "string" },
        strict: { type: "boolean", default: true },
      },
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "render_model_review",
    description: "Render four orthographic review views and optional hash-bound animation evidence in local Blender. The focused profile samples side/back locomotion and front/side melee key phases. No cloud renderer is called.",
    inputSchema: {
      type: "object",
      properties: {
        modelPath: { type: "string" },
        ref: { type: "string" },
        sourceJobId: { type: "string" },
        assetId: { type: "string" },
        reviewType: { type: "string", enum: ["bare_body", "fully_equipped"] },
        includeAnimations: { type: "boolean", default: false },
        animationEvidenceProfile: {
          type: "string",
          enum: ["midpoint", "locomotion_melee_key_phases"],
          default: "midpoint",
        },
        requiredClips: { type: "array", items: { type: "string" } },
        resolution: { type: "integer", minimum: 256, maximum: 2048, default: 768 },
        timeoutMs: { type: "integer", minimum: 1000 },
      },
      required: ["reviewType"],
    },
    outputSchema: JOB_RESPONSE,
  },
  {
    name: "get_model_job",
    description: "Read durable status, progress, structured errors, results, and artifact paths for a model job.",
    inputSchema: { type: "object", properties: { jobId: { type: "string" } }, required: ["jobId"] },
  },
  {
    name: "cancel_model_job",
    description: "Request cancellation of a queued or running local model job and terminate its Blender subprocess when possible.",
    inputSchema: { type: "object", properties: { jobId: { type: "string" } }, required: ["jobId"] },
  },
  {
    name: "record_model_review",
    description: "Record an explicit human approval or rejection. Approval requires bare/equipped four-view renders, all animation clips, and affirmative anatomy/material/seam/clipping checks.",
    inputSchema: {
      type: "object",
      properties: {
        targetJobId: { type: "string" },
        decision: { type: "string", enum: ["approved", "rejected"] },
        reviewer: { type: "string" },
        bareBodyRenderJobId: { type: "string" },
        equippedRenderJobId: { type: "string" },
        checks: {
          type: "object",
          properties: {
            anatomyNatural: { type: "boolean" },
            materialsPbr: { type: "boolean" },
            seamsAcceptable: { type: "boolean" },
            clippingAcceptable: { type: "boolean" },
            animationsAcceptable: { type: "boolean" },
          },
        },
        notes: { type: "string" },
      },
      required: ["targetJobId", "decision", "reviewer"],
    },
  },
  {
    name: "promote_model_set",
    description: "Hash-check and atomically publish an explicitly approved bundle, then rebuild the deterministic approved-only runtime registry.",
    inputSchema: { type: "object", properties: { targetJobId: { type: "string" } }, required: ["targetJobId"] },
    outputSchema: JOB_RESPONSE,
  },
];

function result(value, isError = false) {
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
    ...(isError ? { isError: true } : {}),
  };
}

const server = new Server(
  { name: "war-js-local-character-pipeline", version: "3.0.0" },
  { capabilities: { tools: {}, resources: {}, prompts: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: listResources() }));

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;
  return {
    contents: [{ uri, mimeType: "application/json", text: JSON.stringify(getResource(uri), null, 2) }],
  };
});

const prompts = [
  {
    name: "repair_fit_failure",
    description: "Classify a fit failure, choose the typed remediation path, and rerun only the failed stage.",
    arguments: [
      { name: "assetId", description: "Asset under review", required: true },
      { name: "failureReport", description: "Overlap, weight, or socket validation report", required: true },
    ],
  },
  {
    name: "build_test_character",
    description: "Build a minimal canonical body plus one rigid and one skinned test item before scaling the roster.",
    arguments: [{ name: "bodyVariant", description: "Canonical body variant", required: false }],
  },
];

server.setRequestHandler(ListPromptsRequestSchema, async () => ({ prompts }));

server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  const name = request.params.name;
  const args = request.params.arguments ?? {};
  if (name === "repair_fit_failure") {
    return {
      description: "Repair a typed modular-character fit failure.",
      messages: [{ role: "user", content: { type: "text", text: `Inspect ${args.assetId ?? "the asset"} and classify the failure as rigid socket, skinned wearable, or loose garment. Use the wearable-slots and body-masks resources, call only the matching remediation tool, then rerun validate_pose_pack. Failure report:\n${args.failureReport ?? "(not supplied)"}` } }],
    };
  }
  if (name === "build_test_character") {
    return {
      description: "Build the smallest useful model-pipeline fixture.",
      messages: [{ role: "user", content: { type: "text", text: `Use body variant ${args.bodyVariant ?? "m"}. Assemble one canonical base body, attach one rigid socketed item, fit one chest wearable with nearest-face weight transfer, apply the under_chest body mask, validate core_v1, render review views, and leave the result draft-only until human approval.` } }],
    };
  }
  throw new Error(`Unknown MCP prompt: ${name}`);
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  try {
    if (["create_body_family", "ingest_generated_candidate", "build_modular_set", "validate_model_asset", "render_model_review", "promote_model_set"].includes(name)) {
      return result(startWorkflowJob(name, args));
    }
    if (["assemble_base_character", "fit_wearable", "apply_body_mask", "attach_rigid_item", "validate_pose_pack", "render_turntable", "export_asset"].includes(name)) {
      return result(startCharacterStageJob(name, args));
    }
    if (name === "get_model_job") return result(getModelJob(args.jobId));
    if (name === "cancel_model_job") return result(cancelModelJob(args.jobId));
    if (name === "record_model_review") return result(recordModelReview(args));
    return result({ error: { code: "UNKNOWN_TOOL", message: `Unknown tool: ${name}`, retryable: false } }, true);
  } catch (error) {
    return result({ error: structuredError(error) }, true);
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write("[character-pipeline-mcp] local-only reviewed asset server ready\n");
