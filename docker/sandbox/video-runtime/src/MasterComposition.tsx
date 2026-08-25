import {loadFont} from "@remotion/fonts";
import {Audio} from "@remotion/media";
import type React from "react";
import {lazy, Suspense, useEffect, useState} from "react";

import {
  AbsoluteFill,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import {CorePrimitive} from "./components/CorePrimitives";
import {
  componentLoaders,
  fontCapabilities,
  nativeCanvasById,
  registryBuildId,
  transitionRenderers,
  trustedCapabilityIds,
} from "./generated/capability-registry";
import type {
  VideoLayer,
  VideoRenderInput,
} from "./schemas/VideoRenderInput";

const fontPromises = fontCapabilities.map(({family, file, format, weight}) =>
  loadFont({family, url: staticFile(file), format, weight: String(weight)}),
);
const lazyComponents = Object.fromEntries(
  Object.entries(componentLoaders).map(([id, loader]) => [
    id,
    lazy(
      loader as unknown as () => Promise<{
        default: React.ComponentType<Record<string, unknown>>;
      }>,
    ),
  ]),
) as Record<
  string,
  React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>
>;
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
    const componentIds = selectedIds.filter(
      (id): id is keyof typeof componentLoaders => id in componentLoaders,
    );
    Promise.all([...fontPromises, ...componentIds.map((id) => componentLoaders[id]())])
      .then(() => continueRender(handle))
      .catch(cancelRender);
  }, [cancelRender, continueRender, handle, selectedIds]);
  return null;
};

const CapabilityStage: React.FC<{
  layer: Extract<VideoLayer, {type: "component"}>;
}> = ({layer}) => {
  const Component = lazyComponents[layer.capability_id];
  const nativeCanvas =
    nativeCanvasById[layer.capability_id as keyof typeof nativeCanvasById];
  if (!Component || !nativeCanvas) {
    throw new Error(`No trusted component adapter for ${layer.capability_id}`);
  }
  const outerStyle: React.CSSProperties = {
    position: "absolute",
    left: layer.x,
    top: layer.y,
    width: layer.width,
    height: layer.height,
    opacity: layer.opacity,
    overflow: "hidden",
    zIndex: layer.z_index,
  };
  const stageStyle: React.CSSProperties = {
    width: nativeCanvas.width,
    height: nativeCanvas.height,
    transformOrigin: "top left",
    scale: `${(layer.width / nativeCanvas.width).toFixed(8)} ${(layer.height / nativeCanvas.height).toFixed(8)}`,
  };

  return (
    <div style={outerStyle}>
      <div style={stageStyle}>
        <Suspense fallback={null}>
          <Component {...layer.props} />
        </Suspense>
      </div>
    </div>
  );
};

const BeatMotion: React.FC<{
  beat: VideoRenderInput["beats"][number];
  transitions: VideoRenderInput["transitions"];
}> = ({beat, transitions}) => {
  const frame = useCurrentFrame();
  const incoming = transitions.find(({to_beat_id}) => to_beat_id === beat.id);
  const outgoing = transitions.find(({from_beat_id}) => from_beat_id === beat.id);
  let transitionStyle: React.CSSProperties = {};
  const transition = incoming ?? outgoing;
  if (transition) {
    const localStart = transition.start_frame - beat.start_frame;
    const progress = interpolate(
      frame,
      [localStart, localStart + transition.duration_in_frames],
      [0, 1],
      {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
    );
    const entering = Boolean(incoming);
    const renderer =
      transitionRenderers[
        transition.capability_id as keyof typeof transitionRenderers
      ];
    if (!renderer) {
      throw new Error(
        `No trusted transition adapter for ${transition.capability_id}`,
      );
    }
    transitionStyle = renderer({
      progress,
      entering,
      props: transition.props,
    });
  }

  return (
    <AbsoluteFill
      style={{
        background: beat.background,
        ...transitionStyle,
        overflow: "hidden",
      }}
    >
      {beat.layers.map((layer) => (
        <Sequence
          key={`${beat.id}-layer-${layer.id}`}
          from={layer.from}
          durationInFrames={layer.duration_in_frames}
          layout="none"
        >
          {layer.type === "component" ? (
            <CapabilityStage layer={layer} />
          ) : (
            <CorePrimitive layer={layer} />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const Captions: React.FC<{captions: VideoRenderInput["captions"]}> = ({
  captions,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const timeMs = (frame / fps) * 1000;
  const caption = captions.find(({startMs, endMs}) => startMs <= timeMs && endMs > timeMs);
  if (!caption) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 220,
        right: 220,
        bottom: 72,
        padding: "14px 24px",
        borderRadius: 14,
        background: "rgba(2, 6, 23, .78)",
        color: "white",
        font: "600 38px/1.25 Inter, sans-serif",
        textAlign: "center",
        zIndex: 9000,
      }}
    >
      {caption.text}
    </div>
  );
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

export const MasterComposition: React.FC<VideoRenderInput> = (input) => {
  if (input.build_id !== registryBuildId) {
    throw new Error(
      `Capability build mismatch: input=${input.build_id}, renderer=${registryBuildId}`,
    );
  }
  return (
    <AbsoluteFill style={{background: "#020617"}}>
      <ResourcePreloader selectedIds={input.selected_capability_ids} />
      {input.beats.map((beat) => (
        <Sequence
          key={beat.id}
          from={beat.start_frame}
          durationInFrames={beat.duration_in_frames}
          premountFor={30}
        >
          <BeatMotion beat={beat} transitions={input.transitions} />
        </Sequence>
      ))}
      {input.audio_tracks.map((track) => (
        <Sequence
          key={track.utterance_id}
          from={track.start_frame}
          durationInFrames={track.duration_in_frames}
          layout="none"
        >
          <Audio src={staticFile(track.src)} volume={track.volume} />
        </Sequence>
      ))}
      <Captions captions={input.captions} />
      {input.watermark ? <Watermark /> : null}
    </AbsoluteFill>
  );
};
