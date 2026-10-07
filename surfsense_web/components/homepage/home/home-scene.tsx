import Image from "next/image";
import heroScene from "@/components/homepage/home/home-hero-scene.webp";

/**
 * The dithered landscape behind the homepage hero and closing CTA, filling its
 * positioned parent.
 *
 * `next/image` serves AVIF or WebP at the width each screen needs, from the
 * 3104px master, and inlines a tiny blurred preview so the scene shows before
 * the image arrives. Quality 85: at 75 the dither dots start to smudge.
 */
export function HomeScene({ priority = false }: { priority?: boolean }) {
	return (
		<Image
			src={heroScene}
			alt=""
			fill
			priority={priority}
			sizes="100vw"
			quality={85}
			placeholder="blur"
			draggable={false}
			className="object-cover object-center select-none"
		/>
	);
}
