import type React from "react";
import {AbsoluteFill, Sequence} from "remotion";

export type TimelineLayerProps = {
  id: string;
  from: number;
  durationInFrames: number;
  children: React.ReactNode;
};

const assertLayerProps = ({
  id,
  from,
  durationInFrames,
}: Omit<TimelineLayerProps, "children">) => {
  if (!Number.isInteger(from) || from < 0) {
    throw new Error(`TimelineLayer ${id} requires a non-negative integer from`);
  }
  if (!Number.isInteger(durationInFrames) || durationInFrames < 1) {
    throw new Error(`TimelineLayer ${id} requires a positive integer durationInFrames`);
  }
};

export const TimelineLayer: React.FC<TimelineLayerProps> = (props) => {
  assertLayerProps(props);

  return (
    <Sequence
      from={props.from}
      durationInFrames={props.durationInFrames}
      layout="none"
      name={props.id}
    >
      <AbsoluteFill>{props.children}</AbsoluteFill>
    </Sequence>
  );
};
