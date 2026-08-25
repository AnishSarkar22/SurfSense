import assert from "node:assert/strict";
import {readdir, readFile} from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import Ajv2020 from "ajv/dist/2020.js";
import {riskFrames, resolvedCapabilityIds} from "../render-utils.mjs";

const {VideoRenderInputSchema} = await import("../generated/VideoRenderInput.mjs");
const index = JSON.parse(
  await readFile(
    process.env.SURFSENSE_CAPABILITY_INDEX ??
      path.resolve("generated/capabilities/index.json"),
    "utf8",
  ),
);
const registryBuildId = index.build_id;
const trustedCapabilityIds = index.capabilities.map(({id}) => id);
const root = path.resolve(import.meta.dirname, "..");
const registrySource = await readFile(
  path.join(root, "src/generated/capability-registry.ts"),
  "utf8",
);
const compositionSource = await readFile(
  path.join(root, "src/MasterComposition.tsx"),
  "utf8",
);
const renderSource = await readFile(path.join(root, "render.mjs"), "utf8");
const schemaSource = await readFile(
  path.join(root, "src/schemas/VideoRenderInput.ts"),
  "utf8",
);
const buildSource = await readFile(
  path.join(root, "scripts/build-capabilities.mjs"),
  "utf8",
);

const capabilityFiles = async (directory) => {
  const entries = await readdir(directory, {withFileTypes: true});
  const files = await Promise.all(
    entries.map(async (entry) => {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) return capabilityFiles(target);
      return /\.capabilit(?:y|ies)\.json$/.test(entry.name) ? [target] : [];
    }),
  );
  return files.flat().sort();
};

const declarations = (
  await Promise.all(
    (await capabilityFiles(path.join(root, "src/capabilities"))).map(async (file) => {
      const value = JSON.parse(await readFile(file, "utf8"));
      return Array.isArray(value) ? value : [value];
    }),
  )
).flat();
const ajv = new Ajv2020({allErrors: true, strict: true});
const validInput = {
  schema_version: 1,
  build_id: registryBuildId,
  skill_version: "test",
  fps: 30,
  width: 1920,
  height: 1080,
  duration_in_frames: 90,
  selected_capability_ids: [
    "video.renderer.master",
    "font.inter",
    "video.component.blur-out-up",
  ],
  beats: [
    {
      id: "beat-1",
      utterance_id: "utterance-1",
      start_frame: 0,
      duration_in_frames: 90,
      background: "#020617",
      layers: [
        {
          id: "trusted-title",
          type: "component",
          capability_id: "video.component.blur-out-up",
          from: 0,
          duration_in_frames: 90,
          x: 0,
          y: 0,
          width: 1920,
          height: 1080,
          opacity: 1,
          rotation: 0,
          scale: 1,
          z_index: 1,
          keyframes: [{frame: 20, opacity: 1}],
          props: {text: "Trusted atoms"},
        },
      ],
    },
  ],
  transitions: [],
  audio_tracks: [],
  captions: [],
  watermark: true,
  seed: "fixture",
};

test("generated index and trusted registry stay in lockstep", () => {
  assert.equal(index.schema_version, 1);
  assert.equal(index.build_id, registryBuildId);
  assert.deepEqual(Object.keys(index).sort(), [
    "build_id",
    "capabilities",
    "postings",
    "schema_version",
  ]);
  assert.deepEqual(
    index.capabilities.map(({id}) => id),
    [...trustedCapabilityIds],
  );
  assert.ok(index.capabilities.every(({domain}) => domain === "video"));
  assert.ok(index.capabilities.every(({vibe}) => Array.isArray(vibe)));
  assert.ok(index.capabilities.every(({search_text}) => typeof search_text === "string"));
  assert.ok(index.capabilities.every(({declaration}) => declaration.deterministic));
  assert.ok(index.capabilities.every(({declaration}) => !("loader" in declaration)));
  assert.deepEqual(Object.keys(index.postings), [
    "all",
    "tags",
    "use_for",
    "summary",
    "vibe",
    "category",
    "avoid_for",
  ]);
  for (const field of Object.values(index.postings)) {
    for (const capabilityIds of Object.values(field)) {
      assert.ok(capabilityIds.every((id) => trustedCapabilityIds.includes(id)));
    }
  }
  assert.ok(
    index.capabilities.every(
      ({id}) => !id.endsWith(".slide-swap") && !id.endsWith(".spring-settle"),
    ),
  );
  assert.deepEqual(
    declarations.map(({id}) => id).sort(),
    [...trustedCapabilityIds].sort(),
  );
  assert.match(registrySource, new RegExp(JSON.stringify(registryBuildId)));
  for (const id of trustedCapabilityIds) {
    assert.match(registrySource, new RegExp(JSON.stringify(id)));
  }
  assert.doesNotMatch(registrySource, /slide-swap|spring-settle/);
  assert.match(buildSource, /excludedNames = new Set\(\["slide-swap", "spring-settle"\]\)/);
  assert.doesNotMatch(buildSource, /allowedLoaders/);
  assert.equal(
    declarations.filter(({kind, loader}) => kind === "component" && loader).length,
    (registrySource.match(/\(\) => import\(/g) ?? []).length,
  );
  assert.match(registrySource, /\(\) => import\("\.\.\/capabilities\//);
  assert.match(registrySource, /transitionRenderers/);
  assert.doesNotMatch(
    compositionSource,
    /video\.component\.(?:animated-bar-chart|blur-out-up)/,
  );
});

test("VideoRenderInput accepts trusted declarative layers", () => {
  const result = VideoRenderInputSchema.safeParse(validInput);
  assert.equal(result.success, true, JSON.stringify(result.error?.issues));
});

test("VideoRenderInput rejects source-era structure before capability validation", () => {
  assert.equal(
    VideoRenderInputSchema.safeParse({...validInput, scenes: [{code: "export default 1"}]})
      .success,
    false,
  );
  const invalid = structuredClone(validInput);
  invalid.beats[0].layers[0].capability_id =
    "video.component.not-in-registry";
  invalid.selected_capability_ids[2] = "video.component.not-in-registry";
  assert.equal(VideoRenderInputSchema.safeParse(invalid).success, true);
  assert.equal(trustedCapabilityIds.includes(invalid.beats[0].layers[0].capability_id), false);

  const malformedId = structuredClone(validInput);
  malformedId.selected_capability_ids.push("arbitrary");
  assert.equal(VideoRenderInputSchema.safeParse(malformedId).success, false);

  const invalidProps = structuredClone(validInput);
  invalidProps.beats[0].layers[0].props = {text: "", arbitrary: true};
  assert.equal(VideoRenderInputSchema.safeParse(invalidProps).success, true);
  const capability = index.capabilities.find(
    ({id}) => id === invalidProps.beats[0].layers[0].capability_id,
  );
  assert.equal(ajv.compile(capability.props_schema)(invalidProps.beats[0].layers[0].props), false);

  const duplicateLayerId = structuredClone(validInput);
  duplicateLayerId.beats[0].layers.push(
    structuredClone(duplicateLayerId.beats[0].layers[0]),
  );
  assert.equal(VideoRenderInputSchema.safeParse(duplicateLayerId).success, false);
});

test("risk stills cover boundaries, beat midpoints, and keyframes", () => {
  assert.deepEqual(
    riskFrames(validInput).map(({frame}) => frame),
    [0, 20, 45, 89],
  );
});

test("receipt capability resolution matches the declared used IDs", () => {
  assert.deepEqual(resolvedCapabilityIds(validInput, new Set(trustedCapabilityIds)), [
    "font.inter",
    "video.component.blur-out-up",
    "video.renderer.master",
  ]);
});

test("renderer waits for fonts and lazy capabilities before continuing", () => {
  assert.match(compositionSource, /fontCapabilities\.map/);
  assert.match(
    compositionSource,
    /Promise\.all\(\[\.\.\.fontPromises, \.\.\.componentIds\.map\(\(id\) => componentLoaders\[id\]\(\)\)\]\)/,
  );
  assert.match(compositionSource, /\.then\(\(\) => continueRender\(handle\)\)/);
  assert.match(compositionSource, /\.catch\(cancelRender\)/);
  assert.match(compositionSource, /Object\.entries\(componentLoaders\)/);
  assert.match(compositionSource, /lazy\(/);
});

test("vendored 720p capabilities are staged deterministically at output bounds", () => {
  assert.match(registrySource, /"width":1280/);
  assert.match(registrySource, /"height":720/);
  assert.match(compositionSource, /layer\.width \/ nativeCanvas\.width/);
  assert.match(compositionSource, /layer\.height \/ nativeCanvas\.height/);
  assert.match(schemaSource, /width: z\.literal\(1920\)/);
  assert.match(schemaSource, /height: z\.literal\(1080\)/);
});

test("render path is single-pass and emits the complete receipt", () => {
  assert.equal((renderSource.match(/\brenderMedia\(/g) ?? []).length, 1);
  assert.match(renderSource, /VIDEO_SANDBOX_FRAME_CONCURRENCY \?\? 2/);
  assert.match(renderSource, /concurrency: frameConcurrency/);
  assert.match(renderSource, /VIDEO_SANDBOX_MAX_CONCURRENT_RENDERS \?\? 1/);
  assert.doesNotMatch(renderSource, /\bsegment(?:ation|s)?\b|\bstitch(?:ing|ed)?\b/i);
  assert.doesNotMatch(renderSource, /@remotion\/bundler|\bbundle\(/);
  assert.match(renderSource, /new Ajv2020/);
  assert.match(renderSource, /validateProps\(layer\.capability_id, "component"/);
  for (const field of [
    "schema_version",
    "build_id",
    "skill_version",
    "input_sha256",
    "expected_duration_seconds",
    "expected_frame_count",
    "beat_sample_frames",
    "selected_capability_ids",
    "resolved_capability_ids",
    "render_settings",
    "render_seconds",
    "completed_at",
  ]) {
    assert.match(renderSource, new RegExp(`\\b${field}\\b`));
  }
  assert.match(renderSource, /pixel_format: "yuv420p"/);
  assert.match(renderSource, /audio_codec: "aac"/);
});
