import assert from "node:assert/strict";
import {mkdtemp, rm, symlink, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import test from "node:test";
import {validateSource} from "../scripts/validate-source.mjs";

const fixture = path.resolve(import.meta.dirname, "../harness-fixtures/job-source");

test("valid source typechecks and reports imported capabilities", async () => {
  const result = await validateSource(fixture);
  assert.deepEqual(result.importedCapabilityIds, [
    "video.component.animated-bar-chart",
  ]);
  assert.equal(result.files.length, 2);
});

for (const [name, source, expected] of [
  [
    "network APIs",
    `export const JobComposition = () => { fetch("https://example.com"); return null; };`,
    /Forbidden runtime API/,
  ],
  [
    "runtime randomness",
    `export const JobComposition = () => <div>{Math.random()}</div>;`,
    /Wall-clock or random behavior/,
  ],
  [
    "crypto randomness",
    `export const JobComposition = () => <div>{crypto.getRandomValues(new Uint8Array(1))[0]}</div>;`,
    /Wall-clock or random behavior/,
  ],
  [
    "remote asset expressions",
    `export const JobComposition = () => <img src={"https://example.com/image.png"} />;`,
    /Remote JSX asset URL/,
  ],
  [
    "data asset URLs",
    `export const JobComposition = () => <img src="data:image/png;base64,AAAA" />;`,
    /Remote JSX asset URL/,
  ],
  [
    "protocol-relative asset URLs",
    `export const JobComposition = () => <a href="//example.com">Example</a>;`,
    /Remote JSX asset URL/,
  ],
  [
    "conditional React hooks",
    `import {useState} from "react";
const Conditional = ({show}: {show: boolean}) => {
  if (!show) return null;
  const [value] = useState(0);
  return <div>{value}</div>;
};
export const JobComposition = () => <Conditional show />;`,
    /React Hooks validation failed.*called conditionally/,
  ],
  [
    "dynamic imports",
    `export const JobComposition = () => { import("react"); return null; };`,
    /Forbidden runtime API/,
  ],
  [
    "unapproved packages",
    `import x from "lodash"; export const JobComposition = () => x;`,
    /Import is not allowed/,
  ],
  [
    "runtime artifacts",
    `import {Artifact} from "remotion"; export const JobComposition = () => <Artifact filename="output.json" content="{}" />;`,
    /Reserved runtime API/,
  ],
  [
    "escaping local imports",
    `import "../outside"; export const JobComposition = () => null;`,
    /Local import escapes source root/,
  ],
  [
    "entrypoint props",
    `export const JobComposition = ({title}: {title: string}) => <div>{title}</div>;`,
    /zero-argument JobComposition/,
  ],
]) {
  test(`source policy rejects ${name}`, async () => {
    const root = await mkdtemp(path.join(tmpdir(), "surfsense-source-policy-"));
    try {
      await writeFile(path.join(root, "JobComposition.tsx"), source);
      await assert.rejects(validateSource(root), expected);
    } finally {
      await rm(root, {recursive: true, force: true});
    }
  });
}

test("source policy permits URL-like prose outside resource attributes", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-source-policy-"));
  try {
    await writeFile(
      path.join(root, "JobComposition.tsx"),
      `export const JobComposition = () => <div>Today: scale across enterprise software. Visit https://example.com.</div>;`,
    );
    await validateSource(root);
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});

test("source policy rejects package manifests", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-source-policy-"));
  try {
    await writeFile(
      path.join(root, "JobComposition.tsx"),
      "export const JobComposition = () => null;",
    );
    await writeFile(path.join(root, "package.json"), "{}");
    await assert.rejects(validateSource(root), /Unsupported source path/);
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});

test("source policy rejects symlinks", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "surfsense-source-policy-"));
  try {
    await writeFile(
      path.join(root, "JobComposition.tsx"),
      "export const JobComposition = () => null;",
    );
    await symlink(path.join(root, "JobComposition.tsx"), path.join(root, "Linked.tsx"));
    await assert.rejects(validateSource(root), /Source symlinks are not allowed/);
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});
