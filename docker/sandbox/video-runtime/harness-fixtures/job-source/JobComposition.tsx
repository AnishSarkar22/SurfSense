import type React from "react";
import {AbsoluteFill} from "remotion";
import {
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
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        background: "#020617",
        color: "#f8fafc",
        display: "flex",
        fontFamily: "Inter, sans-serif",
        justifyContent: "center",
      }}
    >
      <div style={{position: "absolute", left: 120, top: 100}}>
        <LocalPulse asset={icon} cue={cue} />
      </div>
      <div style={{fontSize: 54, position: "absolute", top: 90}}>
        {cue.cueId} · frames {cue.startFrame}–{cue.endFrame} ·{" "}
        {cue.durationInFrames} frames · {Math.round(cue.progress * 100)}%
      </div>
      <div style={{height: 500, width: 1000, translate: `${drift * 8}px 0`}}>
        <AnimatedBarChart
          data={[35, 60, 45, 80 + cues.length]}
          labels={["Q1", "Q2", "Q3", "Q4"]}
        />
      </div>
    </AbsoluteFill>
  );
};
