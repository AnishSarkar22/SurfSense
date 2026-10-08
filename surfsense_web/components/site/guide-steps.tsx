import Image from "next/image";
import Link from "next/link";
import { siteText } from "@/components/site/site-text";
import { ArrowRightIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

/**
 * A numbered walkthrough in the site design (Tailwind plus the shared
 * `siteText` styles): one ruled row per step, prose on the left and that
 * step's screenshot opposite it.
 *
 * Shared by `/sunset` and `/license/activate` so the two guides stay the same
 * page shape. Both hold the same kind of instruction and a reader may well
 * follow one after the other.
 *
 * `shot` is optional, and a step without one renders as prose across the full
 * column rather than as a split with an empty cell beside it. Steps whose
 * action is on this site rather than in the app tend not to want a picture:
 * a screenshot of a button that is already on screen, or of the page a link
 * leads to, only shows the reader what they can see.
 */

export type GuideStep = {
	title: string;
	body: React.ReactNode;
	/** Rendered under the body, for a step whose control lives on the page. */
	control?: React.ReactNode;
	action?: { href: string; label: string };
	shot?: { src: string; alt: string; width: number; height: number };
};

export function GuideSteps({ steps }: { steps: GuideStep[] }) {
	return (
		<ol className="ss-home-grid m-0 list-none p-0">
			{steps.map((step, index) => (
				<li key={step.title} className={step.shot ? "ss-home-grid lg:grid-cols-2" : undefined}>
					<div className="flex flex-col justify-center py-12 lg:py-16 lg:pr-10">
						<span className="font-mono text-xs text-muted-foreground">
							{String(index + 1).padStart(2, "0")}
						</span>
						<h3 className={cn(siteText.h3, "mt-2")}>{step.title}</h3>
						<p className={cn(siteText.body, "mt-3 max-w-xl")}>{step.body}</p>
						{step.control}
						{step.action ? (
							<p className="mt-5">
								<Link className={siteText.forward} href={step.action.href}>
									{step.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
								</Link>
							</p>
						) : null}
					</div>

					{/* Square-cornered and hairlined like every other surface on the
					    site: a screenshot is a panel here, not a card.

					    Capped at half its pixel width, because the shots are taken at
					    a device scale factor of 2: left to fill the cell, the smaller
					    ones (a dialog, a single settings row) would be drawn above
					    their own resolution and land soft on a retina screen. */}
					{step.shot ? (
						<div className="flex items-center justify-center px-6 py-8 md:px-10">
							<Image
								src={step.shot.src}
								alt={step.shot.alt}
								width={step.shot.width}
								height={step.shot.height}
								style={{ maxWidth: step.shot.width / 2 }}
								draggable={false}
								className="h-auto w-full border border-border select-none"
							/>
						</div>
					) : null}
				</li>
			))}
		</ol>
	);
}
