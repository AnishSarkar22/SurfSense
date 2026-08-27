import type React from "react";
import {AbsoluteFill} from "remotion";
import {useNarrationCue, useSeededRandom} from "@surfsense/video";
import {AnimatedBarChart} from "@surfsense/video/capabilities";
import {LocalPulse} from "./LocalPulse";

export const JobComposition: React.FC = () => {
  const cue = useNarrationCue();
  const drift = useSeededRandom("chart-drift");
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
        <LocalPulse />
      </div>
      <div style={{fontSize: 54, position: "absolute", top: 90}}>
        Continuous composition · {cue?.cue_id ?? "between cues"}
      </div>
      <div style={{height: 500, width: 1000, translate: `${drift * 8}px 0`}}>
        <AnimatedBarChart
          data={[35, 60, 45, 80]}
          labels={["Q1", "Q2", "Q3", "Q4"]}
        />
      </div>
    </AbsoluteFill>
  );
};
