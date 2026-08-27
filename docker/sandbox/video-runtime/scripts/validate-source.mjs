import {readFile, readdir, lstat} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath, pathToFileURL} from "node:url";
import ts from "typescript";
import {authoringModules} from "./authoring-modules.mjs";

const runtimeRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const allowedPackages = new Set([
  "react",
  "remotion",
  "@remotion/fonts",
  "@remotion/media",
  "@remotion/transitions",
  ...Object.keys(authoringModules),
]);
const forbiddenIdentifiers = new Set([
  "cancelAnimationFrame",
  "eval",
  "fetch",
  "Function",
  "document",
  "localStorage",
  "location",
  "navigator",
  "process",
  "queueMicrotask",
  "require",
  "requestAnimationFrame",
  "sessionStorage",
  "WebSocket",
  "window",
  "XMLHttpRequest",
  "Worker",
  "SharedWorker",
  "EventSource",
  "setInterval",
  "setTimeout",
]);
const maxFiles = 32;
const maxBytes = 256 * 1024;

const sourceFiles = async (root, directory = root) => {
  const entries = await readdir(directory, {withFileTypes: true});
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    const metadata = await lstat(target);
    if (metadata.isSymbolicLink()) throw new Error(`Source symlinks are not allowed: ${target}`);
    if (metadata.isDirectory()) {
      files.push(...(await sourceFiles(root, target)));
      continue;
    }
    const relative = path.relative(root, target).replaceAll(path.sep, "/");
    if (!/^[a-zA-Z0-9_./-]+\.(?:ts|tsx)$/.test(relative) || relative.includes("..")) {
      throw new Error(`Unsupported source path: ${relative}`);
    }
    files.push(target);
  }
  return files;
};

const scriptKind = (filename) =>
  filename.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;

export async function validateSource(sourceRoot) {
  const root = path.resolve(sourceRoot);
  const files = (await sourceFiles(root)).sort();
  if (files.length === 0 || files.length > maxFiles) {
    throw new Error(`Source package must contain 1-${maxFiles} TypeScript files`);
  }
  const sources = new Map();
  let bytes = 0;
  for (const filename of files) {
    const source = await readFile(filename, "utf8");
    bytes += Buffer.byteLength(source);
    sources.set(filename, source);
  }
  if (bytes > maxBytes) throw new Error(`Source package exceeds ${maxBytes} bytes`);

  const entry = path.join(root, "JobComposition.tsx");
  const entrySource = sources.get(entry);
  if (!entrySource) throw new Error("Source package must export JobComposition.tsx");
  const capabilityExports = JSON.parse(
    await readFile(path.join(runtimeRoot, "generated", "capability-exports.json"), "utf8"),
  );
  const importedCapabilityIds = new Set();

  for (const [filename, source] of sources) {
    const ast = ts.createSourceFile(
      filename,
      source,
      ts.ScriptTarget.ES2022,
      true,
      scriptKind(filename),
    );
    const visit = (node) => {
      if (ts.isImportDeclaration(node)) {
        const specifier = node.moduleSpecifier.text;
        if (specifier.startsWith(".")) {
          const resolved = path.resolve(path.dirname(filename), specifier);
          if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
            throw new Error(`Local import escapes source root: ${specifier}`);
          }
        } else if (!allowedPackages.has(specifier)) {
          throw new Error(`Import is not allowed: ${specifier}`);
        }
        if (specifier === "@surfsense/video/capabilities") {
          const bindings = node.importClause?.namedBindings;
          if (node.importClause?.name || !bindings || !ts.isNamedImports(bindings)) {
            throw new Error("Capabilities must use named imports");
          }
          for (const element of bindings?.elements ?? []) {
            if (element.isTypeOnly || node.importClause?.isTypeOnly) continue;
            const exportedName = element.propertyName?.text ?? element.name.text;
            const capabilityId = capabilityExports.exports[exportedName];
            if (!capabilityId) throw new Error(`Unknown capability export: ${exportedName}`);
            importedCapabilityIds.add(capabilityId);
          }
        }
      }
      if (
        (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) ||
        (ts.isIdentifier(node) && forbiddenIdentifiers.has(node.text))
      ) {
        throw new Error(`Forbidden runtime API in ${path.relative(root, filename)}: ${node.getText(ast)}`);
      }
      if (
        ts.isPropertyAccessExpression(node) &&
        ((node.expression.getText(ast) === "Math" && node.name.text === "random") ||
          (node.expression.getText(ast) === "Date" && node.name.text === "now") ||
          (node.expression.getText(ast) === "performance" && node.name.text === "now") ||
          ["getRandomValues", "randomUUID"].includes(node.name.text))
      ) {
        throw new Error(`Wall-clock or random behavior is forbidden: ${node.getText(ast)}`);
      }
      if (
        (ts.isNewExpression(node) || ts.isCallExpression(node)) &&
        ["Date", "Function"].includes(node.expression.getText(ast))
      ) {
        throw new Error(`Wall-clock or dynamic behavior is forbidden: ${node.getText(ast)}`);
      }
      if (
        ts.isElementAccessExpression(node) &&
        ts.isStringLiteral(node.argumentExpression) &&
        (forbiddenIdentifiers.has(node.argumentExpression.text) ||
          ["random", "now", "getRandomValues", "randomUUID"].includes(
            node.argumentExpression.text,
          ))
      ) {
        throw new Error(`Computed access to forbidden API: ${node.getText(ast)}`);
      }
      if (
        ts.isJsxAttribute(node) &&
        ["src", "href"].includes(node.name.getText(ast)) &&
        node.initializer &&
        ts.isStringLiteral(node.initializer) &&
        /^[a-z][a-z0-9+.-]*:/i.test(node.initializer.text)
      ) {
        throw new Error(`Remote JSX asset URL is forbidden: ${node.initializer.text}`);
      }
      if (
        ts.isStringLiteral(node) &&
        !ts.isImportDeclaration(node.parent) &&
        /^[a-z][a-z0-9+.-]*:/i.test(node.text)
      ) {
        throw new Error(`Remote or data URL is forbidden: ${node.text}`);
      }
      ts.forEachChild(node, visit);
    };
    visit(ast);
  }

  const entryAst = ts.createSourceFile(
    entry,
    entrySource,
    ts.ScriptTarget.ES2022,
    true,
    ts.ScriptKind.TSX,
  );
  const hasJobComposition = entryAst.statements.some(
    (statement) => {
      if (!statement.modifiers?.some(({kind}) => kind === ts.SyntaxKind.ExportKeyword)) {
        return false;
      }
      if (ts.isFunctionDeclaration(statement)) {
        return statement.name?.text === "JobComposition" && statement.parameters.length === 0;
      }
      if (!ts.isVariableStatement(statement)) return false;
      return statement.declarationList.declarations.some(({name, initializer}) => {
        const isFunction =
          initializer &&
          (ts.isArrowFunction(initializer) || ts.isFunctionExpression(initializer));
        return (
          ts.isIdentifier(name) &&
          name.text === "JobComposition" &&
          isFunction &&
          initializer.parameters.length === 0
        );
      });
    },
  );
  if (!hasJobComposition) {
    throw new Error(
      "JobComposition.tsx must export a zero-argument JobComposition component",
    );
  }

  const options = {
    target: ts.ScriptTarget.ES2022,
    lib: ["lib.dom.d.ts", "lib.es2022.d.ts"],
    module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.Bundler,
    jsx: ts.JsxEmit.ReactJSX,
    strict: true,
    noEmit: true,
    skipLibCheck: true,
    baseUrl: runtimeRoot,
    paths: Object.fromEntries([
      ...Object.entries(authoringModules).map(([specifier, source]) => [
        specifier,
        [source],
      ]),
      ...[...allowedPackages]
        .filter((specifier) => !specifier.startsWith("@surfsense/"))
        .flatMap((specifier) => {
          const source =
            specifier === "react"
              ? "node_modules/@types/react"
              : `node_modules/${specifier}`;
          return [
            [specifier, [source]],
            [`${specifier}/*`, [`${source}/*`]],
          ];
        }),
    ]),
  };
  const program = ts.createProgram(files, options);
  const diagnostics = ts.getPreEmitDiagnostics(program);
  if (diagnostics.length > 0) {
    throw new Error(
      ts.formatDiagnosticsWithColorAndContext(diagnostics, {
        getCanonicalFileName: (name) => name,
        getCurrentDirectory: () => root,
        getNewLine: () => "\n",
      }),
    );
  }
  return {
    root,
    files,
    bytes,
    importedCapabilityIds: [...importedCapabilityIds].sort(),
  };
}

const invokedPath = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : undefined;
if (invokedPath === import.meta.url) {
  const sourceRoot = process.argv[2];
  if (!sourceRoot || process.argv.length !== 3) {
    throw new Error("Usage: node scripts/validate-source.mjs SOURCE_DIR");
  }
  validateSource(sourceRoot)
    .then(({bytes, files, importedCapabilityIds}) =>
      console.log(
        JSON.stringify({ok: true, bytes, file_count: files.length, imported_capability_ids: importedCapabilityIds}),
      ),
    )
    .catch((error) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exitCode = 1;
    });
}
