import { HomeDownloadButton } from "@/components/homepage/home/home-download-button";
import { HomeScene } from "@/components/homepage/home/home-scene";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * The closing call to action, set on the same meadow scene as the hero.
 *
 * Lazy, unlike the hero's: by the time a visitor scrolls here the scene is
 * usually already cached from the hero. The headline is a paragraph, not
 * an H2: the SEO brief fixes the page's heading sequence and this sits after
 * its last entry.
 */
export function HomeCta() {
	return (
		<section className="px-6 py-16 md:px-10 md:py-24">
			<div className="relative mx-auto flex min-h-[28rem] max-w-6xl flex-col items-center overflow-hidden rounded-3xl px-6 pt-16 text-center md:min-h-[34rem] md:pt-20">
				<HomeScene />
				{/* The sky is light behind the copy; a wash from the top keeps white
				    text above 4.5:1 without darkening the meadow below. */}
				<div
					aria-hidden="true"
					className="absolute inset-0 bg-linear-to-b from-black/45 via-black/15 to-transparent"
				/>

				<div className="relative max-w-2xl">
					<p className={cn(siteText.h2, "text-white md:text-5xl")}>
						Your notebook, on your own machine
					</p>
					<p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-pretty text-white/85 md:text-lg">
						Download SurfSense and keep every document, model key and answer on your own disk. Free,
						open source, no account.
					</p>
					<div className="mt-8">
						<HomeDownloadButton />
					</div>
				</div>
			</div>
		</section>
	);
}
