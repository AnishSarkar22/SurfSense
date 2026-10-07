import Image from "next/image";
import heroScene from "@/components/homepage/home/home-hero-scene.webp";

/**
 * The dithered landscape behind the homepage hero and closing CTA, filling its
 * positioned parent.
 *
 * `next/image` serves AVIF or WebP at the width each screen needs, from the
 * 3104px master, and inlines a tiny blurred preview so the scene shows before
 * the image arrives. Quality 85: at 75 the dither dots start to smudge.
 *
 * `sizes` is the width the scene is drawn at, not the box width: the 2:1 image
 * covers its box, so in a tall box it renders twice the box height wide.
 */
export function HomeScene({ sizes, priority = false }: { sizes: string; priority?: boolean }) {
	return (
		<Image
			src={heroScene}
			alt=""
			fill
			priority={priority}
			sizes={sizes}
			quality={85}
			placeholder="blur"
			draggable={false}
			className="object-cover object-center select-none"
		/>
	);
}
