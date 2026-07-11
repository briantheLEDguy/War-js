const target = process.argv[2] ?? "procedural character assets";

console.error(
  `[model-pipeline] ${target} proxy synchronization is retired. ` +
    "Use the review-gated body-family and modular-set workflow; emergency Three.js fallbacks remain available.",
);
process.exitCode = 1;
