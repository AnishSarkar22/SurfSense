"use client";

import { Video, VideoPlayer as VideoJsPlayer, VideoSkin } from "@videojs/react/video";
import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";

const squarePlayerStyle = { "--media-border-radius": "0px" } as CSSProperties;

export interface VideoPlayerProps {
	src: string;
	poster?: string;
	className?: string;
}

export function VideoPlayer({ src, poster, className }: VideoPlayerProps) {
	return (
		<div className={cn("aspect-video max-h-full w-full overflow-hidden bg-black", className)}>
			<VideoJsPlayer>
				<VideoSkin className="h-full w-full" style={squarePlayerStyle}>
					<Video
						className="h-full w-full object-contain"
						src={src}
						poster={poster}
						playsInline
						preload="metadata"
					/>
				</VideoSkin>
			</VideoJsPlayer>
		</div>
	);
}
