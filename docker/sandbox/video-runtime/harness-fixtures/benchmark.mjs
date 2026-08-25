import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm, stat} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import {performance} from "node:perf_hooks";

const root = path.resolve(import.meta.dirname, "..");
const durations = process.argv.slice(2).length
  ? process.argv.slice(2).map(Number)
  : [30, 60, 180];
if (durations.some((duration) => ![30, 60, 180].includes(duration))) {
  throw new Error("Benchmark durations must be selected from: 30, 60, 180");
}

const indexPath =
  process.env.SURFSENSE_CAPABILITY_INDEX ??
  path.join(root, "generated", "capabilities", "index.json");
const required = [
  path.join(root, "bundle", "index.html"),
  path.join(root, "generated", "VideoRenderInput.mjs"),
  indexPath,
];
for (const file of required) {
  try {
    await stat(file);
  } catch {
    throw new Error(
      `Benchmark prerequisite is missing: ${file}. Build the image or run npm run build once.`,
    );
  }
}

const run = (command, args, options = {}) =>
  new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
      ...options,
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => (stdout += chunk));
    child.stderr?.on("data", (chunk) => (stderr += chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve({stdout, stderr});
      else {
        reject(
          new Error(
            `${command} ${args.join(" ")} failed (${code})\n${stderr || stdout}`,
          ),
        );
      }
    });
  });

const measure = async (work, phase, args) => {
  const memoryFile = path.join(work, `${phase}.max-rss-kb`);
  const started = performance.now();
  await run("/usr/bin/time", [
    "-f",
    "%M",
    "-o",
    memoryFile,
    process.execPath,
    "render.mjs",
    "--bundle-dir",
    path.join(root, "bundle"),
    ...args,
  ]);
  return {
    seconds: Number(((performance.now() - started) / 1000).toFixed(3)),
    max_rss_kb: Number((await readFile(memoryFile, "utf8")).trim()),
  };
};

const catalogStarted = performance.now();
const capabilityIndex = JSON.parse(await readFile(indexPath, "utf8"));
const catalogLoadMs = Number((performance.now() - catalogStarted).toFixed(3));

for (const durationSeconds of durations) {
  const work = await mkdtemp(path.join(tmpdir(), `surfsense-video-${durationSeconds}s-`));
  try {
    const input = path.join(work, "input.json");
    const stills = path.join(work, "stills");
    const output = path.join(work, `${durationSeconds}s.mp4`);
    await run(process.execPath, [
      "harness-fixtures/smoke-input.mjs",
      input,
      String(durationSeconds),
    ]);
    const preflight = await measure(work, "preflight", ["--preflight", input]);
    const riskStills = await measure(work, "stills", ["--stills", input, stills]);
    const render = await measure(work, "render", [input, output]);
    const outputBytes = (await stat(output)).size;
    const receipt = JSON.parse(await readFile(`${output}.render.json`, "utf8"));
    console.log(
      JSON.stringify({
        fixture_seconds: durationSeconds,
        frame_count: durationSeconds * 30,
        build_id: capabilityIndex.build_id,
        catalog_load_ms: catalogLoadMs,
        preflight,
        stills: riskStills,
        render,
        output_bytes: outputBytes,
        receipt_render_seconds: receipt.render_seconds,
      }),
    );
  } finally {
    await rm(work, {recursive: true, force: true});
  }
}
