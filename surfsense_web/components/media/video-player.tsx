"use client";

import { Video, VideoSkin } from "@videojs/react/video";
import { VideoPlayer as VideoJsPlayer } from "@videojs/react/video/player";
import { cn } from "@/lib/utils";

export interface VideoPlayerProps {
	src: string;
	poster?: string;
	className?: string;
}

export function VideoPlayer({ src, poster, className }: VideoPlayerProps) {
	return (
		<div className={cn("aspect-video max-h-full w-full overflow-hidden bg-black", className)}>
			<VideoJsPlayer>
				{/* Embedding surfaces own their edges; retain only Video.js playback controls. */}
				<VideoSkin className="surfsense-video-player">
					<Video src={src} poster={poster} playsInline preload="auto" />
				</VideoSkin>
			</VideoJsPlayer>
		</div>
	);
}
