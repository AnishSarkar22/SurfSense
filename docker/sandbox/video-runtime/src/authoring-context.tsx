import {createContext, useContext} from "react";
import type {VideoRenderInput} from "./schemas/VideoRenderInput";

const VideoRuntimeContext = createContext<VideoRenderInput | null>(null);

export const VideoRuntimeProvider = VideoRuntimeContext.Provider;

export const useTrustedVideoRuntime = (): VideoRenderInput => {
  const input = useContext(VideoRuntimeContext);
  if (!input) {
    throw new Error("SurfSense video helpers must be used inside TrustedVideoHost");
  }
  return input;
};
