import assert from "node:assert/strict";
import test from "node:test";
import { Video as VideoMedia, VideoSkin } from "@videojs/react/video";
import { VideoPlayer as VideoJsPlayer } from "@videojs/react/video/player";
import { Video as VideoIcon } from "lucide-react";
import { VideoPlayer } from "@/components/media/video-player";
import {
	ARTIFACT_GROUP_ORDER,
	getArtifactFormatMeta,
} from "@/features/artifacts/artifact-format-meta";
import { VIEWERS } from "@/features/artifacts/viewer-registry";
import { FILE_VIEWERS } from "@/features/file-viewers/viewer-registry";

test("VideoPlayer streams its source through the Video.js media element", () => {
	const player = VideoPlayer({ src: "/video.mp4", poster: "/poster.jpg" });
	const videoJsPlayer = player.props.children;
	const skin = videoJsPlayer.props.children;
	const video = skin.props.children;

	assert.equal(player.type, "div");
	assert.equal(videoJsPlayer.type, VideoJsPlayer);
	assert.equal(skin.type, VideoSkin);
	assert.equal(skin.props.className, "surfsense-video-player");
	assert.equal(video.type, VideoMedia);
	assert.equal(video.props.playsInline, true);
	assert.equal(video.props.preload, "none");
	assert.equal(video.props.src, "/video.mp4");
	assert.equal(video.props.poster, "/poster.jpg");
});

test("video artifacts have a dedicated Video identity and group", () => {
	const meta = getArtifactFormatMeta("video");

	assert.equal(meta.label, "Video");
	assert.equal(meta.detailLabel, "MP4");
	assert.equal(meta.groupKey, "videos");
	assert.equal(meta.groupLabel, "Videos");
	assert.equal(meta.viewingMode, "inline-media");
	assert.equal(meta.icon, VideoIcon);
	assert.equal(ARTIFACT_GROUP_ORDER.includes("videos"), true);
});

test("artifact viewer registry supports MP4 files", () => {
	assert.ok(VIEWERS["video/mp4"]);
	assert.ok(FILE_VIEWERS["video/mp4"]);
});
