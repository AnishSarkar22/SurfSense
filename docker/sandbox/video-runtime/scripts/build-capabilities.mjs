import {createHash} from "node:crypto";
import {cp, mkdir, readFile, readdir, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = path.join(root, "src", "capabilities");
const outputDir = process.env.SURFSENSE_CAPABILITY_OUTPUT
  ? path.resolve(process.env.SURFSENSE_CAPABILITY_OUTPUT)
  : path.join(root, "generated", "capabilities");
const allowedKinds = new Set(["font", "component", "transition", "renderer"]);
const excludedNames = new Set(["slide-swap", "spring-settle"]);
const ajv = new Ajv2020({allErrors: true, strict: true});

const listMetadata = async (directory) => {
  const entries = await readdir(directory, {withFileTypes: true});
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) return listMetadata(fullPath);
      return entry.name.endsWith(".capability.json") ||
        entry.name.endsWith(".capabilities.json")
        ? [fullPath]
        : [];
    }),
  );
  return nested.flat().sort();
};

const assertStringArray = (value, field, id) => {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`${id}.${field} must be a string array`);
  }
};

const validate = (declaration) => {
  const id = declaration?.id ?? "<unknown>";
  if (
    typeof id !== "string" ||
    !/^(font|video\.(component|transition|renderer))\.[a-z0-9][a-z0-9.-]*$/.test(id)
  ) {
    throw new Error(`Invalid capability id: ${id}`);
  }
  if (!allowedKinds.has(declaration.kind)) throw new Error(`${id} has invalid kind`);
  for (const field of ["summary", "category", "tier"]) {
    if (typeof declaration[field] !== "string" || !declaration[field]) {
      throw new Error(`${id}.${field} must be non-empty`);
    }
  }
  for (const field of ["tags", "use_for", "avoid_for", "dependencies"]) {
    assertStringArray(declaration[field], field, id);
  }
  if (declaration.deterministic !== true) {
    throw new Error(`${id} must be deterministic`);
  }
  if (declaration.props_schema) {
    const validateProps = ajv.compile(declaration.props_schema);
    if (declaration.test_props && !validateProps(declaration.test_props)) {
      throw new Error(`${id}.test_props: ${ajv.errorsText(validateProps.errors)}`);
    }
  }
  if (declaration.loader) {
    const slug = id.split(".").at(-1);
    if (
      !["component", "transition"].includes(declaration.kind) ||
      declaration.loader !== `${declaration.kind}.${slug}`
    ) {
      throw new Error(`${id} has an invalid co-located loader declaration`);
    }
  }
  if ([...excludedNames].some((name) => id.endsWith(`.${name}`))) {
    throw new Error(`${id} is excluded by vendoring policy`);
  }
  return declaration;
};

const tokenize = (value) =>
  [...new Set(
    value
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[^\p{L}\p{N}]+/gu, " ")
      .trim()
      .split(/\s+/)
      .filter(Boolean),
  )];

const metadataFiles = await listMetadata(sourceDir);
const declarations = [];
const declarationSources = new Map();
for (const filename of metadataFiles) {
  const parsed = JSON.parse(await readFile(filename, "utf8"));
  for (const declaration of Array.isArray(parsed) ? parsed : [parsed]) {
    const validated = validate(declaration);
    declarations.push(validated);
    declarationSources.set(validated.id, filename);
  }
}
declarations.sort((left, right) => left.id.localeCompare(right.id));

const ids = new Set();
for (const declaration of declarations) {
  if (ids.has(declaration.id)) throw new Error(`Duplicate capability id ${declaration.id}`);
  ids.add(declaration.id);
}
const pascalCase = (slug) =>
  slug
    .split("-")
    .map((part) => `${part[0].toUpperCase()}${part.slice(1)}`)
    .join("");
const lowerCamelCase = (slug) => {
  const pascal = pascalCase(slug);
  return `${pascal[0].toLowerCase()}${pascal.slice(1)}`;
};
const implementationSpecs = [];
for (const declaration of declarations.filter(({loader}) => loader)) {
  const slug = declaration.id.split(".").at(-1);
  const moduleName = pascalCase(slug);
  const modulePath = path.join(
    path.dirname(declarationSources.get(declaration.id)),
    `${moduleName}.tsx`,
  );
  const source = await readFile(modulePath, "utf8");
  const exportName =
    declaration.kind === "component" ? moduleName : `${lowerCamelCase(slug)}Style`;
  if (!new RegExp(`export const ${exportName}\\b`).test(source)) {
    throw new Error(`${declaration.id} must export ${exportName} from ${modulePath}`);
  }
  const publicImplementationExport =
    declaration.kind === "component" ? moduleName : lowerCamelCase(slug);
  if (!new RegExp(`export const ${publicImplementationExport}\\b`).test(source)) {
    throw new Error(
      `${declaration.id} must export ${publicImplementationExport} from ${modulePath}`,
    );
  }
  const importPath = path
    .relative(path.join(root, "src", "generated"), modulePath)
    .replaceAll(path.sep, "/")
    .replace(/\.tsx$/, "");
  implementationSpecs.push({
    id: declaration.id,
    kind: declaration.kind,
    exportName,
    publicExportName: moduleName,
    publicImplementationExport,
    importPath: importPath.startsWith(".") ? importPath : `./${importPath}`,
    modulePath,
  });
}
const publicExportById = new Map(
  implementationSpecs.map(({id, publicExportName}) => [id, publicExportName]),
);

const indexed = declarations.map((declaration) => {
  const search = tokenize(
    [
      declaration.id,
      declaration.summary,
      declaration.category,
      declaration.vibe ?? "",
      ...declaration.tags,
      ...declaration.use_for,
      ...declaration.avoid_for,
    ].join(" "),
  );
  const {loader: _loader, ...publicDeclaration} = declaration;
  return {
    id: declaration.id,
    kind: declaration.kind,
    domain: "video",
    category: declaration.category,
    summary: declaration.summary,
    tags: declaration.tags,
    vibe: declaration.vibe ? [declaration.vibe] : [],
    use_for: declaration.use_for,
    avoid_for: declaration.avoid_for,
    natural_frame_length: declaration.natural_frame_length ?? null,
    tier: declaration.tier === "core" ? "core" : "vetted",
    dependencies: declaration.dependencies.filter((dependency) => ids.has(dependency)),
    native_canvas: declaration.native_canvas
      ? {
          width: declaration.native_canvas.width,
          height: declaration.native_canvas.height,
        }
      : null,
    props_schema: declaration.props_schema ?? null,
    deterministic_test_props: declaration.test_props ?? null,
    upstream_docs_url: declaration.upstream_docs_url ?? null,
    vendored_revision: declaration.vendored_revision ?? null,
    declaration: {
      ...publicDeclaration,
      public_export: publicExportById.get(declaration.id) ?? null,
    },
    search_text: search.join(" "),
  };
});
const postings = {
  all: {},
  tags: {},
  use_for: {},
  summary: {},
  vibe: {},
  category: {},
  avoid_for: {},
};
const addPostings = (field, value, capabilityId) => {
  for (const token of tokenize(value)) {
    postings[field][token] ??= [];
    postings[field][token].push(capabilityId);
  }
};
for (const declaration of indexed) {
  addPostings("all", declaration.search_text, declaration.id);
  addPostings("tags", declaration.tags.join(" "), declaration.id);
  addPostings("use_for", declaration.use_for.join(" "), declaration.id);
  addPostings("summary", declaration.summary, declaration.id);
  addPostings("vibe", declaration.vibe.join(" "), declaration.id);
  addPostings("category", declaration.category, declaration.id);
  addPostings("avoid_for", declaration.avoid_for.join(" "), declaration.id);
}

const capabilityHash = createHash("sha256").update(JSON.stringify(indexed));
for (const {id, modulePath} of implementationSpecs.toSorted((left, right) =>
  left.id.localeCompare(right.id),
)) {
  capabilityHash.update(id).update("\0");
  capabilityHash.update(await readFile(modulePath));
  capabilityHash.update("\0");
}
const buildId = capabilityHash.digest("hex").slice(0, 20);
const runtimeHash = createHash("sha256").update(buildId);
for (const filename of [
  "package.json",
  "render.mjs",
  "render-utils.mjs",
  "scripts/bundle-job.mjs",
  "scripts/finalize-job.mjs",
  "scripts/validate-source.mjs",
  "src/authoring.tsx",
  "src/TrustedVideoHost.tsx",
  "src/Root.tsx",
  "src/index.ts",
  "src/job/JobComposition.tsx",
  "src/schemas/VideoRenderInput.ts",
]) {
  runtimeHash.update(filename).update(await readFile(path.join(root, filename)));
}
const runtimeBuildId = runtimeHash.digest("hex").slice(0, 20);
const index = {
  schema_version: 1,
  build_id: buildId,
  runtime_build_id: runtimeBuildId,
  capabilities: indexed,
  postings,
};

await mkdir(outputDir, {recursive: true});
await mkdir(path.join(root, "public", "fonts"), {recursive: true});
await mkdir(path.join(root, "src", "generated"), {recursive: true});
await mkdir(path.join(root, "generated"), {recursive: true});
await Promise.all(
  ["Inter.ttf", "Lora.ttf", "JetBrainsMono.ttf"].map((font) =>
    cp(path.join(root, "fonts", font), path.join(root, "public", "fonts", font)),
  ),
);
await writeFile(path.join(outputDir, "index.json"), `${JSON.stringify(index, null, 2)}\n`);
await writeFile(
  path.join(root, "src", "generated", "capability-registry.ts"),
  [
    "// Generated by scripts/build-capabilities.mjs. Do not edit.",
    ...implementationSpecs
      .filter(({kind}) => kind === "transition")
      .map(
        ({exportName, importPath}) =>
          `import {${exportName}} from ${JSON.stringify(importPath)};`,
      ),
    `export const registryBuildId = ${JSON.stringify(buildId)} as const;`,
    `export const runtimeBuildId = ${JSON.stringify(runtimeBuildId)} as const;`,
    `export const trustedCapabilityIds = ${JSON.stringify([...ids])} as const;`,
    "export const componentLoaders = {",
    ...implementationSpecs
      .filter(({kind}) => kind === "component")
      .map(
        ({id, exportName, importPath}) =>
          `  ${JSON.stringify(id)}: () => import(${JSON.stringify(importPath)}).then((module) => ({default: module.${exportName}})),`,
      ),
    "} as const;",
    "export const transitionRenderers = {",
    ...implementationSpecs
      .filter(({kind}) => kind === "transition")
      .map(({id, exportName}) => `  ${JSON.stringify(id)}: ${exportName},`),
    "} as const;",
    `export const fontCapabilities = ${JSON.stringify(
      declarations
        .filter(({kind}) => kind === "font")
        .map(({id, font}) => ({id, ...font})),
    )} as const;`,
    `export const fontFamilies = ${JSON.stringify(
      Object.fromEntries(
        declarations
          .filter(({kind}) => kind === "font")
          .map(({id, font}) => [id, font.family]),
      ),
    )} as const;`,
    `export const nativeCanvasById = ${JSON.stringify(
      Object.fromEntries(
        declarations
          .filter(({kind, native_canvas: nativeCanvas}) => kind === "component" && nativeCanvas)
          .map(({id, native_canvas: nativeCanvas}) => [id, nativeCanvas]),
      ),
    )} as const;`,
    "",
  ].join("\n"),
);
await writeFile(
  path.join(root, "src", "generated", "public-capabilities.ts"),
  [
    "// Generated by scripts/build-capabilities.mjs. Do not edit.",
    ...implementationSpecs.flatMap(
      ({publicExportName, publicImplementationExport, importPath}) => [
        `export {${publicImplementationExport} as ${publicExportName}} from ${JSON.stringify(importPath)};`,
        `export type {${publicExportName}Props} from ${JSON.stringify(importPath)};`,
      ],
    ),
    `export const capabilityBuildId = ${JSON.stringify(buildId)} as const;`,
    `export const capabilityIds = ${JSON.stringify([...ids])} as const;`,
    "",
  ].join("\n"),
);
await writeFile(
  path.join(root, "generated", "capability-exports.json"),
  `${JSON.stringify(
    {
      build_id: buildId,
      exports: Object.fromEntries(
        implementationSpecs.map(({id, publicExportName}) => [publicExportName, id]),
      ),
    },
    null,
    2,
  )}\n`,
);
const schemaSource = await readFile(
  path.join(root, "src", "schemas", "VideoRenderInput.ts"),
  "utf8",
);
const transpiledSchema = ts.transpileModule(schemaSource, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
  fileName: "VideoRenderInput.ts",
  reportDiagnostics: true,
});
if (transpiledSchema.diagnostics?.length) {
  throw new Error(
    ts.formatDiagnosticsWithColorAndContext(transpiledSchema.diagnostics, {
      getCanonicalFileName: (name) => name,
      getCurrentDirectory: () => root,
      getNewLine: () => "\n",
    }),
  );
}
await writeFile(
  path.join(root, "generated", "VideoRenderInput.mjs"),
  transpiledSchema.outputText,
);
console.log(`Generated ${declarations.length} capabilities (${buildId})`);
