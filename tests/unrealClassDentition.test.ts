import { spawnSync } from "node:child_process";
import { expect, test } from "vitest";

test("Greenskin dentition preserves curved roots, dental arches, jaw weights and body geometry", () => {
  const run = spawnSync("python", ["-B", "tests/unrealClassDentition.test.py"], { encoding: "utf8", windowsHide: true });
  expect(run.error, String(run.error)).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
