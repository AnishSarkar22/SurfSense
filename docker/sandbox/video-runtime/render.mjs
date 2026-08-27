import {execFile} from "node:child_process";
import {existsSync} from "node:fs";
import {mkdir, mkdtemp, readFile, rename, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import {fileURLToPath, pathToFileURL} from "node:url";
import {promisify} from "node:util";
import {
  makeCancelSignal,
  renderMedia,
  renderStill,
  selectComposition,
} from "@remotion/renderer";
import {
  assertBundleAssets,
  assertDurationLimit,
  atomicWriteJson,
  directoryHash,
  inputHash,
  neutralSampleFrames,
  resolvedCapabilityIds,
} from "./render-utils.mjs";

const {VideoRenderInputSchema} = await import("./generated/VideoRenderInput.mjs");
const rootDir = path.dirname(fileURLToPath(import.meta.url));
const capabilityIndexPath =
  process.env.SURFSENSE_CAPABILITY_INDEX ??
  path.join(rootDir, "generated", "capabilities", "index.json");
const browserExecutable =
  process.env.SURFSENSE_VIDEO_BROWSER_EXECUTABLE ??
  path.join(
    rootDir,
    "node_modules",
    ".remotion",
    "chrome-headless-shell",
    "linux64",
    "chrome-headless-shell-linux64",
    "chrome-headless-shell",
  );
const progressPath = path.join(rootDir, "progress.json");
const cancelMarkerPath = path.join(rootDir, "cancel");
const timeoutInMilliseconds = Number(
  process.env.VIDEO_SANDBOX_RENDER_FRAME_TIMEOUT_MS ?? 7000,
);
const maxConcurrentRenders = Number(
  process.env.VIDEO_SANDBOX_MAX_CONCURRENT_RENDERS ?? 1,
);
const frameConcurrency = Number(
  process.env.VIDEO_SANDBOX_FRAME_CONCURRENCY ?? 2,
);
const execFileAsync = promisify(execFile);
if (!Number.isFinite(timeoutInMilliseconds) || timeoutInMilliseconds < 7000) {
  throw new Error("VIDEO_SANDBOX_RENDER_FRAME_TIMEOUT_MS must be at least 7000");
}
if (!Number.isInteger(maxConcurrentRenders) || maxConcurrentRenders < 1) {
  throw new Error("VIDEO_SANDBOX_MAX_CONCURRENT_RENDERS must be a positive integer");
}
if (!Number.isInteger(frameConcurrency) || frameConcurrency < 1) {
  throw new Error("VIDEO_SANDBOX_FRAME_CONCURRENCY must be a positive integer");
}

function progressWriter() {
  let pending = Promise.resolve();
  return {
    write(snapshot) {
      pending = pending.then(() =>
        atomicWriteJson(progressPath, {
          ...snapshot,
          updated_at: new Date().toISOString(),
        }),
      );
    },
    flush: () => pending,
  };
}

function cancellationController() {
  let requested = false;
  let activeCancel;
  const request = () => {
    requested = true;
    activeCancel?.();
  };
  const poll = () => {
    if (existsSync(cancelMarkerPath)) request();
    return requested;
  };
  const assertActive = () => {
    if (!poll()) return;
    const error = new Error("Render cancelled");
    error.code = "cancelled";
    throw error;
  };
  const withSignal = async (operation) => {
    assertActive();
    const {cancelSignal, cancel} = makeCancelSignal();
    activeCancel = cancel;
    if (poll()) cancel();
    try {
      return await operation(cancelSignal);
    } catch (error) {
      if (requested || String(error?.message).includes("got cancelled")) {
        const cancelled = new Error("Render cancelled");
        cancelled.code = "cancelled";
        throw cancelled;
      }
      throw error;
    } finally {
      activeCancel = undefined;
    }
  };
  process.on("SIGINT", request);
  process.on("SIGTERM", request);
  return {
    assertActive,
    poll,
    withSignal,
    dispose() {
      process.off("SIGINT", request);
      process.off("SIGTERM", request);
    },
  };
}

async function acquireAdmission(cancellation) {
  const slotsDir = path.join(tmpdir(), "surfsense-video-runtime-slots");
  await mkdir(slotsDir, {recursive: true});
  while (true) {
    cancellation.assertActive();
    for (let slot = 0; slot < maxConcurrentRenders; slot += 1) {
      const slotPath = path.join(slotsDir, String(slot));
      try {
        await mkdir(slotPath);
        return () => rm(slotPath, {recursive: true, force: true});
      } catch (error) {
        if (error?.code !== "EEXIST") throw error;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

const diagnostic = (error, phase) => ({
  ok: false,
  phase,
  code: error?.code ?? "video_render_error",
  message: error instanceof Error ? error.message : String(error),
  ...(error?.issues ? {issues: error.issues} : {}),
});

async function loadInput(propsPath) {
  const source = await readFile(propsPath, "utf8");
  const result = VideoRenderInputSchema.safeParse(JSON.parse(source));
  if (!result.success) {
    const error = new Error("VideoRenderInput failed Zod validation");
    error.code = "invalid_props";
    error.issues = result.error.issues;
    throw error;
  }
  const index = JSON.parse(await readFile(capabilityIndexPath, "utf8"));
  if (index.schema_version !== result.data.schema_version) {
    throw new Error(
      `Capability schema mismatch: input=${result.data.schema_version}, index=${index.schema_version}`,
    );
  }
  if (index.build_id !== result.data.build_id) {
    throw new Error(
      `Capability build mismatch: input=${result.data.build_id}, index=${index.build_id}`,
    );
  }
  const trustedIds = new Set(index.capabilities.map(({id}) => id));
  const unknown = result.data.selected_capability_ids.filter((id) => !trustedIds.has(id));
  if (unknown.length > 0) {
    const error = new Error(`Unknown selected capability IDs: ${unknown.join(", ")}`);
    error.code = "invalid_capability";
    throw error;
  }
  return {
    input: result.data,
    source,
    index,
    trustedIds,
  };
}

async function loadPreparedJob(jobDir, input, index) {
  const manifest = JSON.parse(await readFile(path.join(jobDir, "job.json"), "utf8"));
  const serveUrl = path.join(jobDir, "bundle");
  if (
    manifest.schema_version !== 1 ||
    manifest.capability_build_id !== index.build_id ||
    manifest.runtime_build_id !== index.runtime_build_id
  ) {
    throw new Error("Prepared job build identity does not match the video runtime");
  }
  const actualBundleHash = await directoryHash(serveUrl);
  if (manifest.bundle_sha256 !== actualBundleHash) {
    const error = new Error("Prepared job bundle hash mismatch");
    error.code = "bundle_hash_mismatch";
    throw error;
  }
  const undeclared = manifest.imported_capability_ids.filter(
    (id) => !input.selected_capability_ids.includes(id),
  );
  if (undeclared.length > 0) {
    throw new Error(`Job source imported undeclared capabilities: ${undeclared.join(", ")}`);
  }
  return {manifest, serveUrl};
}

async function select(input, serveUrl) {
  if (!existsSync(serveUrl)) {
    throw new Error(`Prebuilt video bundle does not exist: ${serveUrl}`);
  }
  const composition = await selectComposition({
    serveUrl,
    id: "Main",
    inputProps: input,
    browserExecutable,
  });
  assertDurationLimit(composition, input.max_duration_seconds);
  if (
    composition.width !== 1920 ||
    composition.height !== 1080 ||
    composition.fps !== 30 ||
    composition.durationInFrames !== input.duration_in_frames
  ) {
    throw new Error("Selected composition metadata does not match VideoRenderInput");
  }
  return composition;
}

async function renderStills({
  cancellation,
  composition,
  input,
  outputPath,
  progress,
  samples,
  serveUrl,
}) {
  const parent = path.dirname(outputPath);
  await mkdir(parent, {recursive: true});
  const staging = await mkdtemp(path.join(parent, ".risk-stills-"));
  try {
    for (const [index, sample] of samples.entries()) {
      await cancellation.withSignal((cancelSignal) =>
        renderStill({
          composition,
          serveUrl,
          output: path.join(
            staging,
            `${String(index + 1).padStart(2, "0")}-${sample.frame}.png`,
          ),
          frame: sample.frame,
          inputProps: input,
          timeoutInMilliseconds,
          browserExecutable,
          cancelSignal,
        }),
      );
      progress.write({
        phase: "stills",
        progress: (index + 1) / (samples.length + 1),
        frame: sample.frame,
        reason: sample.reason,
      });
    }
    const columns = Math.min(4, samples.length);
    const rows = Math.ceil(samples.length / columns);
    await execFileAsync("ffmpeg", [
      "-y",
      "-v",
      "error",
      "-pattern_type",
      "glob",
      "-i",
      path.join(staging, "*.png"),
      "-vf",
      `scale=480:270,tile=${columns}x${rows}:padding=8:margin=8`,
      "-frames:v",
      "1",
      path.join(staging, "contact-sheet.png"),
    ]);
    await rm(outputPath, {recursive: true, force: true});
    await rename(staging, outputPath);
  } catch (error) {
    await rm(staging, {recursive: true, force: true});
    throw error;
  }
}

export async function render(argv = process.argv.slice(2)) {
  const bundleOption = argv.indexOf("--job-dir");
  if (
    bundleOption === -1 ||
    !argv[bundleOption + 1] ||
    argv.indexOf("--job-dir", bundleOption + 1) !== -1
  ) {
    throw new Error(
      "Usage: node render.mjs --job-dir job --preflight props.json | " +
        "--job-dir job --stills props.json outdir | " +
        "--job-dir job props.json out.mp4",
    );
  }
  const jobDir = path.resolve(argv[bundleOption + 1]);
  const positional = argv.filter(
    (_, index) => index !== bundleOption && index !== bundleOption + 1,
  );
  const mode =
    positional[0] === "--preflight"
      ? "preflight"
      : positional[0] === "--stills"
        ? "stills"
        : "render";
  const propsArg = mode === "render" ? positional[0] : positional[1];
  const outputArg = mode === "render" ? positional[1] : positional[2];
  const expected = mode === "preflight" ? 2 : mode === "stills" ? 3 : 2;
  if (
    !propsArg ||
    (mode !== "preflight" && !outputArg) ||
    positional.length !== expected
  ) {
    throw new Error(
      "Usage: node render.mjs --job-dir job --preflight props.json | " +
        "--job-dir job --stills props.json outdir | " +
        "--job-dir job props.json out.mp4",
    );
  }

  const propsPath = path.resolve(propsArg);
  const outputPath = outputArg ? path.resolve(outputArg) : undefined;
  const progress = progressWriter();
  const cancellation = cancellationController();
  let phase = "validate";
  let releaseAdmission;
  const startedAt = Date.now();
  try {
    progress.write({phase, progress: 0});
    const {input, source, index, trustedIds} = await loadInput(propsPath);
    const {manifest, serveUrl} = await loadPreparedJob(jobDir, input, index);
    await assertBundleAssets(input, serveUrl);
    cancellation.assertActive();
    phase = "select_composition";
    progress.write({phase, progress: 0});
    const composition = await select(input, serveUrl);
    const samples = neutralSampleFrames(input);
    const resolvedIds = resolvedCapabilityIds(
      input,
      trustedIds,
      manifest.imported_capability_ids,
    );
    const baseReceipt = {
      schema_version: input.schema_version,
      build_id: index.build_id,
      capability_build_id: index.build_id,
      runtime_build_id: index.runtime_build_id,
      input_sha256: inputHash(source),
      source_sha256: manifest.source_sha256,
      bundle_sha256: manifest.bundle_sha256,
      expected_duration_seconds: input.duration_in_frames / input.fps,
      expected_frame_count: input.duration_in_frames,
      sample_frames: samples,
      selected_capability_ids: [...input.selected_capability_ids].sort(),
      imported_capability_ids: [...manifest.imported_capability_ids].sort(),
      resolved_capability_ids: resolvedIds,
      selected_capability_count: input.selected_capability_ids.length,
      resolved_capability_count: resolvedIds.length,
      render_settings: {
        codec: "h264",
        audio_codec: "aac",
        pixel_format: "yuv420p",
        width: 1920,
        height: 1080,
        fps: 30,
      },
    };

    if (mode === "preflight") {
      const result = {...baseReceipt, ok: true, phase: "preflight"};
      progress.write({phase: "preflight", progress: 1});
      await progress.flush();
      console.log(JSON.stringify(result));
      return result;
    }

    releaseAdmission = await acquireAdmission(cancellation);
    if (mode === "stills") {
      phase = "stills";
      progress.write({phase, progress: 0});
      await renderStills({
        cancellation,
        composition,
        input,
        outputPath,
        progress,
        samples,
        serveUrl,
      });
      progress.write({phase, progress: 1});
      await progress.flush();
      return;
    }

    phase = "render";
    await mkdir(path.dirname(outputPath), {recursive: true});
    const extension = path.extname(outputPath) || ".mp4";
    const stagedOutput = `${outputPath.slice(0, -extension.length)}.partial-${process.pid}-${Date.now()}${extension}`;
    progress.write({phase, progress: 0, rendered_frames: 0});
    try {
      await cancellation.withSignal((cancelSignal) =>
        renderMedia({
          composition,
          serveUrl,
          codec: "h264",
          audioCodec: "aac",
          pixelFormat: "yuv420p",
          enforceAudioTrack: true,
          outputLocation: stagedOutput,
          inputProps: input,
          chromiumOptions: {enableMultiProcessOnLinux: true},
          timeoutInMilliseconds,
          concurrency: frameConcurrency,
          browserExecutable,
          cancelSignal,
          onProgress: ({progress: fraction, renderedFrames, encodedFrames}) => {
            cancellation.poll();
            progress.write({
              phase,
              progress: fraction,
              rendered_frames: renderedFrames,
              encoded_frames: encodedFrames,
              frame_count: composition.durationInFrames,
            });
          },
        }),
      );
      cancellation.assertActive();
      await rename(stagedOutput, outputPath);
      await atomicWriteJson(`${outputPath}.render.json`, {
        ...baseReceipt,
        render_seconds: (Date.now() - startedAt) / 1000,
      });
    } catch (error) {
      await rm(stagedOutput, {force: true});
      throw error;
    }
    progress.write({phase, progress: 1, rendered_frames: composition.durationInFrames});
    await progress.flush();
  } catch (error) {
    progress.write({phase, progress: 0, error: diagnostic(error, phase)});
    await progress.flush();
    if (error && typeof error === "object") error.diagnostic = diagnostic(error, phase);
    throw error;
  } finally {
    cancellation.dispose();
    await releaseAdmission?.();
  }
}

const invokedPath = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : undefined;
if (invokedPath === import.meta.url) {
  render().catch((error) => {
    console.error(JSON.stringify(error?.diagnostic ?? diagnostic(error, "arguments")));
    process.exitCode = 1;
  });
}
