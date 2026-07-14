#!/usr/bin/env node
import { runRosterBatch } from "./roster-generation.mjs";

function parseArgs(argv) {
  const result = { all: false, smoke: false, resume: false, revision: "next" };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--all") result.all = true;
    else if (token === "--smoke") result.smoke = true;
    else if (token === "--resume") result.resume = true;
    else if (["--run-id", "--kind", "--key", "--revision"].includes(token)) result[token.slice(2).replace("-", "_")] = argv[++index];
    else throw new Error(`Unknown argument: ${token}`);
  }
  return result;
}

const args = parseArgs(process.argv.slice(2));
if ((args.all || args.smoke) && !args.run_id) throw new Error("--all/--smoke requires --run-id <id>.");
if (args.all && args.smoke) throw new Error("Choose either --all or --smoke.");
if (!args.all && !args.smoke && (!args.kind || !args.key)) throw new Error("Targeted generation requires --kind and --key.");
if (args.kind && !["playable", "npc", "creature"].includes(args.kind)) throw new Error("--kind must be playable, npc, or creature.");

const report = await runRosterBatch({
  runId: args.run_id ?? "current",
  resume: args.resume,
  kind: args.all || args.smoke ? undefined : args.kind,
  key: args.all || args.smoke ? undefined : args.key,
  revision: args.revision,
  smoke: args.smoke,
});
console.log(JSON.stringify(report, null, 2));
if (report.counts.blocked > 0) process.exitCode = 1;
