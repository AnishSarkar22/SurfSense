import type React from "react";
import {Composition} from "remotion";
import {registryBuildId} from "./generated/capability-registry";
import {MasterComposition} from "./MasterComposition";
import {
  type VideoRenderInput,
  VideoRenderInputSchema,
} from "./schemas/VideoRenderInput";

const defaultProps: VideoRenderInput = {
  schema_version: 1,
  build_id: registryBuildId,
  skill_version: "video-skill-v1",
  fps: 30,
  max_duration_seconds: 3,
  width: 1920,
  height: 1080,
  duration_in_frames: 90,
  selected_capability_ids: [
    "video.renderer.master",
    "video.component.core.primitives",
    "font.inter",
  ],
  beats: [
    {
      id: "preview",
      utterance_id: "preview",
      start_frame: 0,
      duration_in_frames: 90,
      background: "#020617",
      layers: [
        {
          id: "preview-title",
          type: "text",
          from: 0,
          duration_in_frames: 90,
          x: 240,
          y: 390,
          width: 1440,
          height: 300,
          opacity: 1,
          rotation: 0,
          scale: 1,
          z_index: 1,
          keyframes: [],
          text: "SurfSense",
          color: "#f8fafc",
          font_id: "font.inter",
          font_size: 112,
          font_weight: 600,
          align: "center",
        },
      ],
    },
  ],
  transitions: [],
  audio_tracks: [],
  captions: [],
  watermark: true,
  seed: "preview",
};

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={MasterComposition}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={90}
    defaultProps={defaultProps}
    schema={VideoRenderInputSchema}
    calculateMetadata={({props}) => ({
      durationInFrames: props.duration_in_frames,
      fps: props.fps,
      width: props.width,
      height: props.height,
    })}
  />
);
