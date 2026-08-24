"use client";

import { VideoPlayer } from "@/components/media/video-player";
import { buildBackendUrl } from "@/lib/env-config";
import type { FileViewerProps } from "./model";

export default function Mp4FileViewer({ primary }: FileViewerProps) {
	return (
		<div className="flex h-full items-center bg-black">
			<VideoPlayer src={buildBackendUrl(primary.content_url)} />
		</div>
	);
}
