import {createHash} from "node:crypto";
import {cp, mkdir, mkdtemp, readFile, rename, rm} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath, pathToFileURL} from "node:url";
import {bundle} from "@remotion/bundler";
import {atomicWriteJson, directoryHash} from "../render-utils.mjs";
import {validateSource} from "./validate-source.mjs";

const runtimeRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const option = (argv, name) => {
  const index = argv.indexOf(name);
  if (index === -1) {
    throw new Error(`Missing ${name}`);
  }
  if (!argv[index + 1] || argv.indexOf(name, index + 1) !== -1) {
    throw new Error(`Invalid ${name}`);
  }
  return path.resolve(argv[index + 1]);
};

const sourcePackageHash = async ({files, root}) => {
  const hash = createHash("sha256");
  for (const filename of files) {
    hash.update(path.relative(root, filename).replaceAll(path.sep, "/"));
    hash.update("\0");
    hash.update(await readFile(filename));
    hash.update("\0");
  }
  return hash.digest("hex");
};

export async function bundleJob(argv = process.argv.slice(2)) {
  const sourceDir = option(argv, "--source-dir");
  const outDir = option(argv, "--out-dir");
  if (argv.length !== 4) {
    throw new Error(
      "Usage: node scripts/bundle-job.mjs --source-dir SOURCE --out-dir JOB",
    );
  }
  if (outDir === sourceDir || outDir.startsWith(`${sourceDir}${path.sep}`)) {
    throw new Error("Prepared job output must not overlap source");
  }

  const validation = await validateSource(sourceDir);
  const index = JSON.parse(
    await readFile(
      process.env.SURFSENSE_CAPABILITY_INDEX ??
        path.join(runtimeRoot, "generated", "capabilities", "index.json"),
      "utf8",
    ),
  );
  const parent = path.dirname(outDir);
  await mkdir(parent, {recursive: true});
  const staging = await mkdtemp(path.join(parent, ".video-job-"));
  const stagedPublic = path.join(staging, "public");
  const stagedBundle = path.join(staging, "bundle");
  try {
    await cp(path.join(runtimeRoot, "public"), stagedPublic, {recursive: true});
    const trustedJobModule = path.join(runtimeRoot, "src", "job", "JobComposition");
    const serveUrl = await bundle({
      entryPoint: path.join(runtimeRoot, "src", "index.ts"),
      publicDir: stagedPublic,
      outDir: stagedBundle,
      rootDir: runtimeRoot,
      webpackOverride: (config) => ({
        ...config,
        resolve: {
          ...config.resolve,
          alias: {
            ...(config.resolve?.alias ?? {}),
            [`${trustedJobModule}$`]: path.join(sourceDir, "JobComposition.tsx"),
            "@surfsense/video$": path.join(runtimeRoot, "src", "authoring.tsx"),
            "@surfsense/video/capabilities$": path.join(
              runtimeRoot,
              "src",
              "generated",
              "public-capabilities.ts",
            ),
          },
        },
      }),
    });
    if (path.resolve(serveUrl) !== path.resolve(stagedBundle)) {
      throw new Error(`Unexpected bundle output: ${serveUrl}`);
    }
    const manifest = {
      schema_version: 1,
      source_sha256: await sourcePackageHash(validation),
      bundle_sha256: await directoryHash(stagedBundle),
      runtime_build_id: index.runtime_build_id,
      capability_build_id: index.build_id,
      imported_capability_ids: validation.importedCapabilityIds,
    };
    await atomicWriteJson(path.join(staging, "job.json"), manifest);
    await rm(outDir, {recursive: true, force: true});
    await rename(staging, outDir);
    console.log(JSON.stringify({ok: true, job_dir: outDir, ...manifest}));
    return manifest;
  } catch (error) {
    await rm(staging, {recursive: true, force: true});
    throw error;
  }
}

const invokedPath = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : undefined;
if (invokedPath === import.meta.url) {
  bundleJob().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
