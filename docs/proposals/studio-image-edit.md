---
status: accepted
code:
  - surfsense_local/backend/modules/artifacts/
  - surfsense_local/backend/modules/llm/providers/
  - surfsense_local/backend/modules/llm/resolution.py
  - surfsense_local/backend/worker/studio/
  - surfsense_local/frontend/src/features/studio/
---

# Editing a Studio image into its next version

> A ready image or infographic gets the Edit box that Word, PDF and web pages have. The instruction and the open version's picture go to the chosen image editing model, and what comes back is the document's next version. The `image_edit` slot, which can be filled today but which nothing reads, becomes Studio's.

Today Refine rewrites only a text spec: a Word document's or PDF's Markdown or script, or a web page's HTML ([Refine](../architecture/studio.md#refine)). An image or infographic keeps no spec and has no versions; changing one means generating a new one from the sources ([the image path](../architecture/studio.md#the-image-path)). The `image_edit` slot is in the catalog, Settings and onboarding, and FLUX.2 klein 4B fills it, but no resolver or client reads it ([selection](../architecture/local-models/selection.md)). The [local image proposal](local-image-and-video-models.md#studio) left open whether an edit replaces an image or makes a new one; a Studio Edit that made a new artifact per edit was built and taken out. This page decides: an edit is the next version of the same document.

## What changes

| | Today | With this |
|---|---|---|
| A ready image or infographic | no Edit box, no versions | the Refine box, posting to its own route; each edit is the next version |
| Its draft | an unversioned artifact | v1 of its own document, with `recipe: drafted()` |
| `image_edit` slot | chosen, read by nothing | read by Studio's edit job |
| sd-server demand | by format: `image` and `infographic` need `image_gen` | by job: an edit job needs `image_edit` |
| `ArtifactRead` | `refinable` | adds `image_editable` |

## Decisions

### An edit is a version, as a refine is

- **Each version is its own artifact,** under the keys a refine already writes: `version: {root, number, parent}` in `artifact_metadata` ([script documents](../architecture/studio.md#script-documents)). The `artifact_versions` table the [file agent proposal](file-agent/03-editable-artifacts.md) designs replaces them later for every format at once.
- **The recipe points at the base, not at its bytes:** `{"kind": "image_edit", "instruction", "base_artifact_id"}`. Deleting the document deletes every version, so the base cannot go while a later version names it.
- **The edit reads the open version's own file.** Edits chain: editing v3 starts from v3's picture, not v1's.
- **Regenerate repeats the edit** on the same base, for a new sample. A draft's Regenerate still draws from the sources and replaces v1 in place.
- **Image drafts become v1.** A draft records its version and `recipe: drafted()`, so the list groups versions and the viewer's switcher shows them. An image made before this change becomes v1 when it is first edited, by the fallback `create_refine_version` already takes for a base without a version.
- **The body stays findable:** the base's body, then `Edited: <instruction>`. An infographic's brief no longer matches its picture exactly after an edit; the instruction records how it moved.
- **No chat model.** The instruction goes to the edit model as written. Rewriting it first would add a model call, and a wait for the chat model, to every edit.
- **No retry.** Every failure is a `NonRetryableImageError`, as for an image draft, and Huey does not retry an edit, as it does not retry a refine: the user asked for one call, and Retry asks again.

### Its own slice and route, the same box

- **`modules/artifacts/image_edits/`**, beside `studio_documents/`, not inside it: Refine's spec, its window check and its figures do not apply to a picture. It holds the checks, the version it creates, and the route.
- **`POST /artifacts/{id}/image-edit`** with `{instruction}`, 1 to 2,000 characters, as Refine's; `202` with the pending version. Each refusal is a `409` whose `detail` is `{message, code}`:
  - `already_generating`, as Refine;
  - `version_unfinished`, as Refine;
  - `not_editable`: not a ready image or infographic with its picture;
  - `needs_image_edit`, new: nothing fills the `image_edit` slot, or what fills it is gone. It mirrors Refine's `needs_chat`.
- **`ArtifactRead.image_editable`** is true for a ready `image` or `infographic` with a `primary` file.
- **The box is Refine's** ([`refine-box.tsx`](../../surfsense_local/frontend/src/features/studio/refine-box.tsx)), given the call it submits. It floats over the media viewer when `refinable || image_editable`. The version list and switcher need nothing new once images carry version keys ([`artifact-versions.ts`](../../surfsense_local/frontend/src/features/studio/artifact-versions.ts)).

### The model layer

- **`ImageEditor`**, beside `ImageGenerator` in [`protocols.py`](../../surfsense_local/backend/modules/llm/providers/protocols.py): `edit(model, prompt, image) -> GeneratedImage`.
- **`resolve_image_edit()`** in [`resolution.py`](../../surfsense_local/backend/modules/llm/resolution.py), as `resolve_image_generation()` is, reading `ModelType.IMAGE_EDIT`.
- **The remote editor** posts multipart `/images/edits` with `image`, `prompt` and `model`. The response is the `data[]` that generation already reads, so the bounded read, the normalising, the URL's egress check and the MIME check move out of [`image.py`](../../surfsense_local/backend/modules/llm/providers/openai_compatible/image.py) into a file both clients use. It sends one image and no `input_fidelity`, which only some GPT image models take.
- **The local editor** posts sd-server's native `POST /sdcpp/v1/img_gen` and polls `GET /sdcpp/v1/jobs/{id}` each second, inside the same text-runtime hold and model wait as [`generator.py`](../../surfsense_local/backend/modules/llm/providers/sdcpp/generator.py). The body is `{prompt, ref_images: [<data URL>], width, height, output_format: "png"}`; the result is `result.images[0].b64_json`. A `failed` job, a `404`, a `410` or a `429` fails the edit.

### Why `img_gen`, and not the edit routes sd-server also has

Read at the pinned `master-869-07a85c7`:

| Route | What it does with the picture |
|---|---|
| `POST /v1/images/edits` | makes the first upload both a reference and the `init_image` (`routes_openai.cpp`), at the default strength of 0.75: the result is the input re-noised, not an edit |
| `POST /sdapi/v1/img2img` | AUTOMATIC1111's shape: `init_images` and `denoising_strength`, the same |
| `POST /sdcpp/v1/img_gen` | `ref_images` alone, which is how every edit model sd.cpp documents is run (`-r`, never `-i`) |

- **sd.cpp picks the reference preset** from the model's architecture (`flux2`, `longcat`, `qwen`), so the launch needs no `--ref-image-args`.
- **The request sends the base's width and height.** A native request starts from the launch settings, and the catalog gives klein no size, so an edit model launched at another size would crop or stretch the picture.
- **Steps and guidance stay launch flags,** as the [local image proposal](local-image-and-video-models.md#launch-flags) has them: the native request copies them from the launch. klein fills both slots from the same files, so its edit settings are its image settings.
- **Results are kept 600 seconds** after a job ends. The job polls each second, so it never meets a `410` unless it was stopped for that long.

### sd-server demand is per job

[`local_image_demand.py`](../../surfsense_local/backend/modules/artifacts/local_image_demand.py) maps a format to the image type its catalog row requires. An edit's format is still `image` or `infographic`, so Electron would launch the image model's files, and the edit would wait two minutes for weights that never load. The demand reads the job's recipe instead: an `image_edit` recipe needs `image_edit`. When one model fills both slots, as klein does, nothing reloads between drawing an image and editing it.

### Cancel

- **A queued sd.cpp job** is cancelled with `POST /sdcpp/v1/jobs/{id}/cancel`.
- **A generating one cannot be** (`cancel_generating: false` in `/sdcpp/v1/capabilities`). The cancel ends the demand at once and Electron stops sd-server, as for an image today.

## Which models edit

The rule is the slot's own: a model that edits by instruction, from the picture as a reference image. A local model is one whose catalog entry names `edit`; a remote one takes an image in and gives one out ([`classifier.py`](../../surfsense_local/backend/modules/llm/catalog/remote/classifier.py)). Nothing new gates it.

| | Model | Why |
|---|---|---|
| **Local, now** | FLUX.2 klein 4B | the only curated edit model: Apache-2.0, 4 steps, and the same download fills both image slots |
| **Local, next** | LongCat-Image-Edit Turbo | renders exact lettering, given in quotes, which infographics need; curated only if its GGUF edits correctly on the pinned sd.cpp ([local image proposal](local-image-and-video-models.md#image-editing)) |
| **Local, later** | Qwen-Image-Edit-2511 | 17.9 GB; waits for a 32 GB machine's measurement |
| **Remote** | an OpenAI-compatible `/images/edits` model, such as gpt-image-1 | the remote editor above |
| **To review** | Boogu Edit, Mage-Flow-Edit | the pinned sd.cpp runs both now; licence and a GGUF are unchecked |

Not editors:

- **SD 1.5, SDXL, Z-Image Turbo, ERNIE-Image Turbo, LongCat-Image.** They can only re-noise a picture (image-to-image, inpainting); they do not follow an instruction and they rewrite lettering. Their entries name no `edit`, and stay so.
- **instruct-pix2pix and CosXL-Edit**, the edit models of AUTOMATIC1111's era, which sd.cpp runs but which current edit models outclass.
- **FLUX.1 Kontext dev**, for its licence.

## Not in this

- **A mask or a selected region.** sd.cpp and the remote route both take one; an interface to draw it is its own design.
- **The agent editing an image.** The agent makes no images today.
- **A second infographic path** that rewrites the brief and draws again. If klein garbles an infographic's lettering, infographic edits wait for LongCat instead.

## Steps

1. **Spike, in the scratchpad.** One klein edit through `img_gen` on the pinned sd-server: the output's size, whether the picture's layout survives, an infographic's lettering, the time. The result decides whether infographics are in step 4.
2. **The editors.** `ImageEditor`, the local and remote clients, the shared response reading, `resolve_image_edit()`.
3. **Demand per job.** `local_image_demand` reads the recipe.
4. **Versions for images.** Drafts record v1; the `image_edits/` slice, its route, `image_editable`, the job's branch and `media/visual/edit/`.
5. **The box.** The Refine box over the media viewer, and the new refusal's sentence in every language.
6. **Docs.** [studio.md](../architecture/studio.md) (the image path, Refine, routes, viewers), [selection.md](../architecture/local-models/selection.md) (`image_edit` is read by Studio), the [local image proposal](local-image-and-video-models.md)'s open question closed, and an ADR: an edit is a version, which reverses the Edit that was taken out.

## Known gaps

- Lettering after an edit is not measured on klein or LongCat.
- No edit has run on the pinned sd-server yet; the route's behaviour above is read from its source, not measured.
