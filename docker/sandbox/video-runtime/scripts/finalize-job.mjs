import {cp, readFile} from "node:fs/promises";
import path from "node:path";
import {pathToFileURL} from "node:url";
import {atomicWriteJson, directoryHash} from "../render-utils.mjs";

const option = (argv, name) => {
  const index = argv.indexOf(name);
  if (
    index === -1 ||
    !argv[index + 1] ||
    argv.indexOf(name, index + 1) !== -1
  ) {
    throw new Error(`Invalid ${name}`);
  }
  return path.resolve(argv[index + 1]);
};

export async function finalizeJob(argv = process.argv.slice(2)) {
  if (argv.length !== 4) {
    throw new Error(
      "Usage: node scripts/finalize-job.mjs --job-dir JOB --public-dir PUBLIC",
    );
  }
  const jobDir = option(argv, "--job-dir");
  const publicDir = option(argv, "--public-dir");
  const bundleDir = path.join(jobDir, "bundle");
  const manifestPath = path.join(jobDir, "job.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  await cp(publicDir, path.join(bundleDir, "public"), {
    recursive: true,
    force: true,
  });
  const finalized = {
    ...manifest,
    bundle_sha256: await directoryHash(bundleDir),
  };
  await atomicWriteJson(manifestPath, finalized);
  console.log(JSON.stringify({ok: true, job_dir: jobDir, ...finalized}));
  return finalized;
}

const invokedPath = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : undefined;
if (invokedPath === import.meta.url) {
  finalizeJob().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
