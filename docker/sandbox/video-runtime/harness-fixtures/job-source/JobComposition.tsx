import type React from "react";
import {AbsoluteFill} from "remotion";
import {
  FittedText,
  SpatialGrid,
  SpatialStack,
  TimelineLayer,
  useAsset,
  useNarrationCue,
  useNarrationCues,
  useSeededRandom,
} from "@surfsense/video";
import {AnimatedBarChart} from "@surfsense/video/capabilities";
import {LocalPulse} from "./LocalPulse";

export const JobComposition: React.FC = () => {
  const cue = useNarrationCue();
  const cues = useNarrationCues();
  const icon = useAsset("surfsense-icon");
  const drift = useSeededRandom("chart-drift");
  if (!cue) return null;
  const durationInFrames = cues.at(-1)?.endFrame ?? 1;
  return (
    <AbsoluteFill
      style={{
        background: "#020617",
        color: "#f8fafc",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <TimelineLayer id="fixture chart" from={0} durationInFrames={durationInFrames + 30}>
        <SpatialGrid
          minItemWidth={600}
          gap={64}
          align="center"
          style={{height: "100%", padding: 120}}
        >
          <SpatialStack gap={32}>
            <LocalPulse asset={icon} cue={cue} />
            <FittedText
              id="fixture heading"
              maxWidth={720}
              maxLines={2}
              maxFontSize={54}
            >
              {`${cue.cueId} · frames ${cue.startFrame}–${cue.endFrame} · ${cue.durationInFrames} frames · ${Math.round(cue.progress * 100)}%`}
            </FittedText>
          </SpatialStack>
          <div style={{height: 500, minWidth: 0, translate: `${drift * 8}px 0`}}>
            <AnimatedBarChart
              data={[35, 60, 45, 80 + cues.length]}
              labels={["Q1", "Q2", "Q3", "Q4"]}
            />
          </div>
        </SpatialGrid>
      </TimelineLayer>
    </AbsoluteFill>
  );
};
