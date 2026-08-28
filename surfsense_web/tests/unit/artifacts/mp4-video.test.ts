import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
	Video as VideoJsMedia,
	VideoPlayer as VideoJsPlayer,
	VideoSkin,
} from "@videojs/react/video";
import { Video as VideoIcon } from "lucide-react";
import { VideoPlayer } from "@/components/shared/video-player";
import {
	ARTIFACT_GROUP_ORDER,
	getArtifactFormatMeta,
} from "@/features/artifacts/artifact-format-meta";
import { VIEWERS } from "@/features/artifacts/viewer-registry";
import { FILE_VIEWERS } from "@/features/file-viewers/viewer-registry";

test("shared VideoPlayer composes the Video.js video preset", () => {
	const player = VideoPlayer({ src: "/video.mp4", poster: "/poster.jpg" });
	const videoJsPlayer = player.props.children;
	const skin = videoJsPlayer.props.children;
	const media = skin.props.children;

	assert.equal(videoJsPlayer.type, VideoJsPlayer);
	assert.equal(skin.type, VideoSkin);
	assert.equal(skin.props.style["--media-border-radius"], "0px");
	assert.equal(media.type, VideoJsMedia);
	assert.equal(media.props.playsInline, true);
	assert.equal(media.props.preload, "metadata");
	assert.equal(media.props.src, "/video.mp4");
	assert.equal(media.props.poster, "/poster.jpg");
});

test("only the generated-video chat card uses the shared Video.js player", () => {
	const chatCard = readFileSync(
		new URL("../../../components/tool-ui/save-artifact.tsx", import.meta.url),
		"utf8"
	);
	const fileViewer = readFileSync(
		new URL("../../../features/file-viewers/mp4-file-viewer.tsx", import.meta.url),
		"utf8"
	);

	assert.match(chatCard, /components\/shared\/video-player/);
	assert.doesNotMatch(fileViewer, /components\/shared\/video-player/);
	assert.doesNotMatch(chatCard, /video-presentation\/mp4-player/);
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
