"use client";

import { buildBackendUrl } from "@/lib/env-config";
import type { FileViewerProps } from "./model";

export default function Mp4FileViewer({ primary }: FileViewerProps) {
	return (
		<div className="flex h-full items-center bg-black">
			{/* The richer Video.js player is intentionally limited to generated-video chat cards. */}
			{/* biome-ignore lint/a11y/useMediaCaption: Artifact MP4s do not include a captions file. */}
			<video
				className="block aspect-video max-h-full w-full bg-black object-contain"
				controls
				playsInline
				preload="none"
				src={buildBackendUrl(primary.content_url)}
			/>
		</div>
	);
}
