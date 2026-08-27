import {loadFont} from "@remotion/fonts";
import {Audio} from "@remotion/media";
import type React from "react";
import {useEffect, useState} from "react";
import {AbsoluteFill, Sequence, staticFile, useDelayRender} from "remotion";
import {VideoRuntimeProvider} from "./authoring-context";
import {
  fontCapabilities,
  registryBuildId,
  trustedCapabilityIds,
} from "./generated/capability-registry";
import {JobComposition} from "./job/JobComposition";
import type {VideoRenderInput} from "./schemas/VideoRenderInput";

const fontPromises = fontCapabilities.map(({family, file, format, weight}) =>
  loadFont({family, url: staticFile(file), format, weight: String(weight)}),
);
const trustedIds = new Set<string>(trustedCapabilityIds);

const ResourcePreloader: React.FC<{selectedIds: string[]}> = ({selectedIds}) => {
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const [handle] = useState(() => delayRender("Loading trusted video capabilities"));

  useEffect(() => {
    const unknown = selectedIds.filter((id) => !trustedIds.has(id));
    if (unknown.length > 0) {
      cancelRender(new Error(`Unknown capability IDs: ${unknown.join(", ")}`));
      return;
    }
    Promise.all(fontPromises)
      .then(() => continueRender(handle))
      .catch(cancelRender);
  }, [cancelRender, continueRender, handle, selectedIds]);
  return null;
};

const Watermark: React.FC = () => (
  <div
    style={{
      position: "absolute",
      right: 36,
      bottom: 30,
      width: 46,
      height: 46,
      display: "grid",
      placeItems: "center",
      borderRadius: 999,
      background: "rgba(2,6,23,.46)",
      zIndex: 9999,
    }}
  >
    <img src={staticFile("icon-128.svg")} alt="" style={{width: 29, height: 29}} />
  </div>
);

export const TrustedVideoHost: React.FC<VideoRenderInput> = (input) => {
  if (input.build_id !== registryBuildId) {
    throw new Error(
      `Capability build mismatch: input=${input.build_id}, renderer=${registryBuildId}`,
    );
  }
  return (
    <AbsoluteFill style={{background: "#020617"}}>
      <ResourcePreloader selectedIds={input.selected_capability_ids} />
      <VideoRuntimeProvider value={input}>
        <JobComposition />
      </VideoRuntimeProvider>
      {input.audio_tracks.map((track) => (
        <Sequence
          key={track.cue_id}
          from={track.start_frame}
          durationInFrames={track.duration_in_frames}
          layout="none"
        >
          <Audio src={staticFile(track.src)} volume={track.volume} />
        </Sequence>
      ))}
      {input.watermark ? <Watermark /> : null}
    </AbsoluteFill>
  );
};
