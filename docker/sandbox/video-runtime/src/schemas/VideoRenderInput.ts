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
const color = z.string().min(1).max(128);
const capabilityId = z.string().regex(/^(font|video\.(component|transition|renderer))\./);

const placement = {
  id: z
    .string()
    .min(1)
    .max(64)
    .regex(/^[a-z0-9][a-z0-9_-]*$/),
  from: z.number().int().nonnegative().default(0),
  duration_in_frames: z.number().int().positive(),
  x: z.number().finite().default(0),
  y: z.number().finite().default(0),
  width: z.number().positive().max(1920).default(1920),
  height: z.number().positive().max(1080).default(1080),
  opacity: z.number().min(0).max(1).default(1),
  rotation: z.number().finite().default(0),
  scale: z.number().positive().max(20).default(1),
  z_index: z.number().int().min(-100).max(100).default(0),
  filter: z
    .object({
      blur: z.number().min(0).max(100).default(0),
      brightness: z.number().min(0).max(4).default(1),
      contrast: z.number().min(0).max(4).default(1),
      saturate: z.number().min(0).max(4).default(1),
    })
    .strict()
    .optional(),
  keyframes: z
    .array(
      z
        .object({
          frame: z.number().int().nonnegative(),
          opacity: z.number().min(0).max(1).optional(),
          x: z.number().finite().optional(),
          y: z.number().finite().optional(),
          scale: z.number().positive().max(20).optional(),
        })
        .strict(),
    )
    .max(20)
    .default([]),
};

const textLayer = z
  .object({
    type: z.enum(["text", "rich_text"]),
    ...placement,
    text: z.string().min(1).max(4000),
    color: color.default("#f8fafc"),
    font_id: capabilityId.default("font.inter"),
    font_size: z.number().min(8).max(300).default(72),
    font_weight: z.number().int().min(100).max(900).default(500),
    align: z.enum(["left", "center", "right"]).default("left"),
  })
  .strict();
const shapeLayer = z
  .object({
    type: z.literal("shape"),
    ...placement,
    shape: z.enum(["rectangle", "ellipse", "line"]).default("rectangle"),
    fill: color.default("#0f172a"),
    stroke: color.optional(),
    stroke_width: z.number().nonnegative().max(100).default(0),
    radius: z.number().nonnegative().max(960).default(0),
    gradient_to: color.optional(),
  })
  .strict();
const mediaLayer = z
  .object({
    type: z.enum(["image", "video"]),
    ...placement,
    src: publicAssetPath,
    fit: z.enum(["contain", "cover", "fill"]).default("cover"),
    muted: z.boolean().default(true),
  })
  .strict();
const svgLayer = z
  .object({
    type: z.enum(["svg", "icon"]),
    ...placement,
    path: z.string().min(1).max(20000),
    view_box: z.string().min(1).max(100).default("0 0 24 24"),
    fill: color.default("currentColor"),
    stroke: color.optional(),
  })
  .strict();
const chartLayer = z
  .object({
    type: z.literal("chart"),
    ...placement,
    chart: z.enum(["bar", "line", "metric_grid"]),
    values: z.array(z.number().finite()).min(1).max(100),
    labels: z.array(z.string().max(48)).max(100).default([]),
    color: color.default("#38bdf8"),
  })
  .strict();
const codeLayer = z
  .object({
    type: z.literal("code"),
    ...placement,
    code: z.string().min(1).max(12000),
    language: z.string().max(40).default("text"),
    highlight_lines: z.array(z.number().int().positive()).max(50).default([]),
  })
  .strict();
const connectorLayer = z
  .object({
    type: z.literal("connector"),
    ...placement,
    x2: z.number().finite(),
    y2: z.number().finite(),
    color: color.default("#94a3b8"),
    stroke_width: z.number().positive().max(40).default(4),
    arrow: z.boolean().default(false),
  })
  .strict();
const audioVisualizationLayer = z
  .object({
    type: z.literal("audio_visualization"),
    ...placement,
    samples: z.array(z.number().min(0).max(1)).min(2).max(512),
    color: color.default("#38bdf8"),
    bars: z.number().int().min(2).max(128).default(48),
  })
  .strict();
const repeatedLayer = z
  .object({
    type: z.literal("repeated"),
    ...placement,
    count: z.number().int().min(1).max(100),
    columns: z.number().int().min(1).max(20).default(5),
    gap: z.number().nonnegative().max(200).default(16),
    fill: color.default("#334155"),
    radius: z.number().nonnegative().max(200).default(12),
  })
  .strict();

const coreLeaf = z.discriminatedUnion("type", [
  textLayer,
  shapeLayer,
  mediaLayer,
  svgLayer,
  chartLayer,
  codeLayer,
  connectorLayer,
  audioVisualizationLayer,
  repeatedLayer,
]);
const groupLayer = z
  .object({
    type: z.literal("group"),
    ...placement,
    layout: z.enum(["free", "row", "column", "grid"]).default("free"),
    gap: z.number().nonnegative().max(200).default(0),
    clip: z.boolean().default(false),
    children: z.array(coreLeaf).max(50),
  })
  .strict();
const capabilityLayer = z
  .object({
    type: z.literal("component"),
    ...placement,
    capability_id: capabilityId,
    props: z.record(z.string(), z.json()),
  })
  .strict();

export const VideoLayerSchema = z.union([coreLeaf, groupLayer, capabilityLayer]);
export const VideoBeatSchema = z
  .object({
    id: z.string().min(1).max(100),
    utterance_id: z.string().min(1).max(100),
    start_frame: z.number().int().nonnegative(),
    duration_in_frames: z.number().int().positive(),
    background: color.default("#020617"),
    layers: z.array(VideoLayerSchema).max(100),
  })
  .strict()
  .superRefine((beat, context) => {
    const ids = new Set<string>();
    beat.layers.forEach((layer, index) => {
      if (ids.has(layer.id)) {
        context.addIssue({
          code: "custom",
          message: `Duplicate layer ID ${layer.id} in beat ${beat.id}`,
          path: ["layers", index, "id"],
        });
      }
      ids.add(layer.id);
    });
  });
export const VideoTransitionSchema = z
  .object({
    capability_id: capabilityId,
    from_beat_id: z.string().min(1).max(100),
    to_beat_id: z.string().min(1).max(100),
    start_frame: z.number().int().nonnegative(),
    duration_in_frames: z.number().int().min(1).max(120),
    props: z.record(z.string(), z.json()).default({}),
  })
  .strict();
export const CaptionSchema = z
  .object({
    text: z.string(),
    startMs: z.number().nonnegative(),
    endMs: z.number().positive(),
    timestampMs: z.number().nullable(),
    confidence: z.number().min(0).max(1).nullable(),
  })
  .strict()
  .refine(({startMs, endMs}) => endMs > startMs, "Caption endMs must exceed startMs");
export const AudioTrackSchema = z
  .object({
    utterance_id: z.string().min(1).max(100),
    src: publicAssetPath,
    start_frame: z.number().int().nonnegative(),
    duration_in_frames: z.number().int().positive(),
    volume: z.number().min(0).max(2).default(1),
  })
  .strict();

export const VideoRenderInputSchema = z
  .object({
    schema_version: z.literal(1),
    build_id: z.string().min(8).max(128),
    skill_version: z.string().min(1).max(128),
    fps: z.literal(30),
    max_duration_seconds: z.number().int().positive(),
    width: z.literal(1920),
    height: z.literal(1080),
    duration_in_frames: z.number().int().positive(),
    selected_capability_ids: z.array(capabilityId).min(1).max(100),
    beats: z.array(VideoBeatSchema).min(1).max(12),
    transitions: z.array(VideoTransitionSchema).max(11).default([]),
    audio_tracks: z.array(AudioTrackSchema).max(12).default([]),
    captions: z.array(CaptionSchema).max(2000).default([]),
    watermark: z.boolean().default(true),
    seed: z.string().min(1).max(128),
  })
  .strict()
  .superRefine((input, context) => {
    if (input.duration_in_frames > input.max_duration_seconds * input.fps) {
      context.addIssue({code: "custom", message: "Video exceeds configured duration limit"});
    }
    const ids = new Set(input.selected_capability_ids);
    for (const beat of input.beats) {
      if (beat.start_frame + beat.duration_in_frames > input.duration_in_frames) {
        context.addIssue({code: "custom", message: `Beat ${beat.id} exceeds duration`});
      }
      for (const layer of beat.layers) {
        if ("capability_id" in layer && !ids.has(layer.capability_id)) {
          context.addIssue({
            code: "custom",
            message: `Undeclared capability ${layer.capability_id}`,
          });
        }
        if (layer.from + layer.duration_in_frames > beat.duration_in_frames) {
          context.addIssue({
            code: "custom",
            message: `Layer in beat ${beat.id} exceeds beat duration`,
          });
        }
      }
    }
    for (const transition of input.transitions) {
      if (!ids.has(transition.capability_id)) {
        context.addIssue({
          code: "custom",
          message: `Undeclared transition ${transition.capability_id}`,
        });
      }
    }
  });

export type VideoRenderInput = z.infer<typeof VideoRenderInputSchema>;
export type VideoLayer = z.infer<typeof VideoLayerSchema>;
