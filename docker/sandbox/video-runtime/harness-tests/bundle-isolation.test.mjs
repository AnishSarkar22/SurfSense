import assert from "node:assert/strict";
import {cp, mkdir, mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import test from "node:test";
import {assertBundleAssets, directoryHash} from "../render-utils.mjs";
import {bundleJob} from "../scripts/bundle-job.mjs";
import {finalizeJob} from "../scripts/finalize-job.mjs";

const inputFor = (src) => ({
  audio_tracks: [{src}],
  assets: [],
});

test("job bundles validate assets without cross-job fallback", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-bundle-isolation-"));
  const firstBundle = path.join(root, "first", "bundle");
  const secondBundle = path.join(root, "second", "bundle");
  try {
    await Promise.all([
      mkdir(path.join(firstBundle, "public"), {recursive: true}),
      mkdir(path.join(secondBundle, "public"), {recursive: true}),
    ]);
    await Promise.all([
      writeFile(path.join(firstBundle, "public", "first.wav"), "first"),
      writeFile(path.join(secondBundle, "public", "second.wav"), "second"),
    ]);

    await Promise.all([
      assertBundleAssets(inputFor("first.wav"), firstBundle),
      assertBundleAssets(inputFor("second.wav"), secondBundle),
    ]);
    await assert.rejects(
      assertBundleAssets(inputFor("first.wav"), secondBundle),
      (error) => error.code === "missing_bundle_asset",
    );
    await assert.rejects(
      assertBundleAssets(inputFor("../first.wav"), firstBundle),
      (error) => error.code === "asset_path_escape",
    );
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});

test("finalizing narration updates assets and reseals the prepared bundle", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-finalize-job-"));
  const jobDir = path.join(root, "job");
  const bundleDir = path.join(jobDir, "bundle");
  const publicDir = path.join(root, "public");
  try {
    await Promise.all([
      mkdir(path.join(bundleDir, "public"), {recursive: true}),
      mkdir(publicDir, {recursive: true}),
    ]);
    await writeFile(path.join(bundleDir, "index.html"), "bundle");
    await writeFile(path.join(publicDir, "narration.wav"), "first");
    await writeFile(
      path.join(jobDir, "job.json"),
      JSON.stringify({schema_version: 1, bundle_sha256: "0".repeat(64)}),
    );

    const first = await finalizeJob([
      "--job-dir",
      jobDir,
      "--public-dir",
      publicDir,
    ]);
    assert.equal(first.bundle_sha256, await directoryHash(bundleDir));
    assert.equal(
      await readFile(path.join(bundleDir, "public", "narration.wav"), "utf8"),
      "first",
    );

    await writeFile(path.join(publicDir, "narration.wav"), "replacement");
    const second = await finalizeJob([
      "--job-dir",
      jobDir,
      "--public-dir",
      publicDir,
    ]);
    assert.notEqual(second.bundle_sha256, first.bundle_sha256);
    assert.equal(
      await readFile(path.join(bundleDir, "public", "narration.wav"), "utf8"),
      "replacement",
    );
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});

test("representative authored project typechecks and bundles with sealed hashes", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-job-bundle-"));
  const sourceDir = path.join(root, "source");
  try {
    await cp(path.join(import.meta.dirname, "../harness-fixtures/job-source"), sourceDir, {
      recursive: true,
    });
    const first = await bundleJob([
      "--source-dir",
      sourceDir,
      "--out-dir",
      path.join(root, "first"),
    ]);
    const second = await bundleJob([
      "--source-dir",
      sourceDir,
      "--out-dir",
      path.join(root, "second"),
    ]);

    assert.deepEqual(first.imported_capability_ids, [
      "video.component.animated-bar-chart",
    ]);
    assert.equal(first.source_sha256, second.source_sha256);
    assert.equal(first.bundle_sha256, await directoryHash(path.join(root, "first/bundle")));
    assert.equal(second.bundle_sha256, await directoryHash(path.join(root, "second/bundle")));
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});
