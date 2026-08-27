import {z} from "zod";

const publicAssetPath = z
  .string()
  .min(1)
  .max(512)
  .refine(
    (value) =>
      !value.startsWith("/") &&
      !value.includes("..") &&
      !/^[a-z][a-z0-9+.-]*:/i.test(value),
    "Asset paths must be relative to the staged public directory",
  );
const capabilityId = z.string().regex(/^(font|video\.(component|transition|renderer))\./);
const cueId = z
  .string()
  .min(1)
  .max(64)
  .regex(/^[a-z0-9][a-z0-9_-]*$/);
const referenceId = z
  .string()
  .min(1)
  .max(96)
  .regex(/^[a-z0-9][a-z0-9_.-]*$/);

export const NarrationCueSchema = z
  .object({
    cue_id: cueId,
    start_frame: z.number().int().nonnegative(),
    duration_in_frames: z.number().int().positive(),
  })
  .strict();
export const AudioTrackSchema = z
  .object({
    cue_id: cueId,
    src: publicAssetPath,
    start_frame: z.number().int().nonnegative(),
    duration_in_frames: z.number().int().positive(),
    volume: z.number().min(0).max(2).default(1),
  })
  .strict();
export const AssetSchema = z
  .object({
    id: referenceId,
    path: publicAssetPath,
    kind: z.enum(["image", "video", "audio", "svg"]),
  })
  .strict();
export const SampleFrameSchema = z
  .object({
    frame: z.number().int().nonnegative(),
    reason: z.string().min(1).max(160),
  })
  .strict();

export const VideoRenderInputSchema = z
  .object({
    schema_version: z.literal(1),
    build_id: z.string().min(8).max(128),
    fps: z.literal(30),
    max_duration_seconds: z.number().int().positive(),
    width: z.literal(1920),
    height: z.literal(1080),
    duration_in_frames: z.number().int().positive(),
    selected_capability_ids: z.array(capabilityId).max(100),
    narration_cues: z.array(NarrationCueSchema).min(1).max(12),
    audio_tracks: z.array(AudioTrackSchema).min(1).max(12),
    assets: z.array(AssetSchema).max(64),
    sample_frames: z.array(SampleFrameSchema).max(64),
    watermark: z.boolean(),
    seed: z.string().min(1).max(128),
  })
  .strict()
  .superRefine((input, context) => {
    if (input.duration_in_frames > input.max_duration_seconds * input.fps) {
      context.addIssue({code: "custom", message: "Video exceeds configured duration limit"});
    }
    const cueIds = new Set<string>();
    let expectedStart = 0;
    for (const cue of input.narration_cues) {
      if (cueIds.has(cue.cue_id)) {
        context.addIssue({code: "custom", message: `Duplicate cue ID ${cue.cue_id}`});
      }
      cueIds.add(cue.cue_id);
      if (cue.start_frame !== expectedStart) {
        context.addIssue({code: "custom", message: "Narration cues must be sequential"});
      }
      if (cue.start_frame + cue.duration_in_frames > input.duration_in_frames) {
        context.addIssue({code: "custom", message: `Cue ${cue.cue_id} exceeds duration`});
      }
      expectedStart = cue.start_frame + cue.duration_in_frames;
    }
    if (expectedStart !== input.duration_in_frames) {
      context.addIssue({code: "custom", message: "Narration cues must cover the composition"});
    }
    for (const [index, track] of input.audio_tracks.entries()) {
      const cue = input.narration_cues[index];
      if (
        !cue ||
        track.cue_id !== cue.cue_id ||
        track.start_frame !== cue.start_frame ||
        track.duration_in_frames !== cue.duration_in_frames
      ) {
        context.addIssue({code: "custom", message: "Audio tracks must match narration cues"});
      }
      if (track.start_frame + track.duration_in_frames > input.duration_in_frames) {
        context.addIssue({code: "custom", message: `Audio ${track.cue_id} exceeds duration`});
      }
    }
    const assetIds = new Set<string>();
    const assetPaths = new Map<string, string>();
    for (const asset of input.assets) {
      if (assetIds.has(asset.id)) {
        context.addIssue({code: "custom", message: `Duplicate asset ID ${asset.id}`});
      }
      if (assetPaths.has(asset.path)) {
        context.addIssue({code: "custom", message: `Duplicate asset path ${asset.path}`});
      }
      assetIds.add(asset.id);
      assetPaths.set(asset.path, asset.kind);
    }
    const sampleFrames = new Set<number>();
    for (const sample of input.sample_frames) {
      if (sampleFrames.has(sample.frame)) {
        context.addIssue({code: "custom", message: `Duplicate sample frame ${sample.frame}`});
      }
      sampleFrames.add(sample.frame);
      if (sample.frame >= input.duration_in_frames) {
        context.addIssue({code: "custom", message: `Sample frame ${sample.frame} exceeds duration`});
      }
    }
  });

export type VideoRenderInput = z.infer<typeof VideoRenderInputSchema>;
export type NarrationCue = z.infer<typeof NarrationCueSchema>;
export type VideoAsset = z.infer<typeof AssetSchema>;
