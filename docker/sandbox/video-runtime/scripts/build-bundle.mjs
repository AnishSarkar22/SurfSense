import {rm} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "bundle");
await rm(outDir, {recursive: true, force: true});
const serveUrl = await bundle({
  entryPoint: path.join(root, "src", "index.ts"),
  publicDir: path.join(root, "public"),
  outDir,
});
if (path.resolve(serveUrl) !== path.resolve(outDir)) {
  throw new Error(`Unexpected bundle output: ${serveUrl}`);
}
console.log(`Built static video bundle at ${serveUrl}`);
