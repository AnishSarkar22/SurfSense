import assert from "node:assert/strict";
import {mkdir, mkdtemp, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import test from "node:test";
import {assertBundleAssets} from "../render-utils.mjs";

const inputFor = (src) => ({
  audio_tracks: [{src}],
  beats: [{layers: []}],
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
