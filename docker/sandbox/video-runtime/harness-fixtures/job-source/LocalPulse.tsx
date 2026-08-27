import type React from "react";
import type {NarrationCueState, VideoAsset} from "@surfsense/video";

type LocalPulseProps = {
  asset: VideoAsset;
  cue: NarrationCueState;
};

export const LocalPulse: React.FC<LocalPulseProps> = ({asset, cue}) => {
  const scale = 1 + cue.progress * 0.2;
  return (
    <img
      alt=""
      src={asset.src}
      style={{
        width: 36,
        height: 36,
        borderRadius: "50%",
        opacity: cue.active ? 1 : 0.45,
        scale: String(scale),
      }}
    />
  );
};
