import type React from "react";
import {Composition} from "remotion";
import {registryBuildId} from "./generated/capability-registry";
import {TrustedVideoHost} from "./TrustedVideoHost";
import {
  type VideoRenderInput,
  VideoRenderInputSchema,
} from "./schemas/VideoRenderInput";

const defaultProps: VideoRenderInput = {
  schema_version: 1,
  build_id: registryBuildId,
  fps: 30,
  max_duration_seconds: 3,
  width: 1920,
  height: 1080,
  duration_in_frames: 90,
  selected_capability_ids: ["video.renderer.master", "font.inter"],
  narration_cues: [
    {
      cue_id: "preview",
      start_frame: 0,
      duration_in_frames: 90,
    },
  ],
  audio_tracks: [],
  assets: [],
  sample_frames: [
    {
      frame: 0,
      reason: "first-content",
    },
    {
      frame: 89,
      reason: "last-content",
    },
  ],
  watermark: true,
  seed: "preview",
};

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={TrustedVideoHost}
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
