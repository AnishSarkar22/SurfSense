import Link from "next/link";
import { AirGapDiagram } from "@/components/homepage/home/home-air-gap/air-gap-diagram";
import { AirGapScrollSteps } from "@/components/homepage/home/home-air-gap/air-gap-scroll-steps";
import { HomeAnnouncement } from "@/components/homepage/home/home-announcement";
import { HomeBadge } from "@/components/homepage/home/home-badge";
import { COMPARE_ROWS, CONFIDENTIAL, PILLARS } from "@/components/homepage/home/home-content";
import { HomeDownloadButton } from "@/components/homepage/home/home-download-button";
import { HomeFeaturesTabs } from "@/components/homepage/home/home-features-tabs";
import { HomeScene } from "@/components/homepage/home/home-scene";
import { sectionSpacing } from "@/components/homepage/home/home-section-spacing";
import { siteText } from "@/components/site/site-text";
import { ArrowRightIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

/**
 * Homepage sections.
 *
 * The layout vocabulary is ported from `homepage-reference/`: every section is
 * a ruled band inside one bordered column, splits are two halves separated by a
 * hairline, and cell grids are drawn with a 1px gap over the border colour so
 * no interior rule ever doubles up. Nothing here has a radius or a shadow; only
 * controls keep the palette's `--radius`. `HomeFormats` (its own folder) is the
 * exception: rounded cards with miniatures, in the painted scenes' language.
 * Styled with Tailwind plus the shared `siteText` styles.
 *
 * Mostly server components. `HomeFeaturesTabs` (the claims switcher) lives in
 * its own "use client" module rather than pulling this file across the boundary.
 *
 * The heading order is not editorial. It is the SEO skeleton from
 * `plans/community-local/seo/02-page-briefs.md`: H1, then eight H2s in a fixed
 * order. Sections may be restyled freely; the sequence of headings may not be
 * reordered without re-reading that brief.
 */

export function HomeHero() {
	return (
		// Full bleed, and pulled up under the sticky nav (`-mt-20` is the nav's
		// height) so the scene starts at the top edge of the page. Copy sits in
		// the sky, where the wash keeps white text readable.
		<section className="-mt-20" data-bleed>
			<div className="relative flex min-h-[calc(100svh+4rem)] flex-col items-center justify-center overflow-hidden px-6 pt-32 pb-40 text-center md:px-10 lg:pb-96">
				{/* 1.73 times the hero's height, the cover width on portrait screens. */}
				<HomeScene priority sizes="max(100vw, calc(173vh + 7rem))" />
				<div
					aria-hidden="true"
					className="absolute inset-0 bg-linear-to-b from-black/45 via-black/20 to-transparent"
				/>
				{/* Dissolves the scene into the page. It sits in the 4rem the hero runs
				    past the fold (pb-40 offsets it so the copy stays centred), so the
				    first screen shows no fade. On desktop lg:pb-96 lifts the copy clear
				    of the dome. */}
				<div
					aria-hidden="true"
					className="absolute inset-x-0 bottom-0 h-16 bg-linear-to-b from-transparent to-background"
				/>

				<div className="relative mx-auto max-w-4xl">
					<HomeAnnouncement />
					<h1 className={cn(siteText.display, "text-white")}>
						Air-gapped, open source NotebookLM alternative
					</h1>
					<p className="mx-auto mt-8 max-w-2xl text-base leading-relaxed text-pretty text-white/85 md:text-lg lg:text-xl">
						A private research notebook that runs entirely on your own machine. Your documents, your
						model keys, no cloud, no account.
					</p>
					<div className="mt-10 flex justify-center">
						<HomeDownloadButton />
					</div>
				</div>
			</div>
		</section>
	);
}

/**
 * H2 #1 — the offline / local / air-gapped claim.
 *
 * Drawn as one system diagram, not a row of cells: `HomePillars` directly
 * below is already a three-column row, and the diagram shows the air gap
 * rather than asserting it.
 *
 * The headline is the brief's exact H2 #1 text; `Features` is the pill above
 * it instead of replacing it.
 */
export function HomeOnYourMachine() {
	return (
		<section>
			{/* On lg the whole frame pins for one screen (pt-20 clears the nav) and
			    only the diagram changes as you scroll; below lg it flows normally. */}
			<AirGapScrollSteps className="pt-10 pb-16 md:pt-24 lg:sticky lg:top-0 lg:flex lg:h-svh lg:flex-col lg:justify-center lg:pt-20 lg:pb-0">
				<div className="text-center">
					<HomeBadge>Features</HomeBadge>
					<h2 className={cn(siteText.h2, "mt-4")}>Runs entirely on your machine</h2>
				</div>
				<AirGapDiagram className="mt-10 lg:mt-14" />
			</AirGapScrollSteps>
		</section>
	);
}

/**
 * H2 #2, #3, #4 — one ruled row, three arguments.
 *
 * The reference's `Services` cards: a headline, a short body, and a forward
 * link pinned to the bottom of the cell so the three links line up regardless
 * of how long each body runs.
 *
 * The band's own headline is a `<p>` styled like an H2, not a real one — the
 * three real H2s the brief wants are the pillar titles below it, and adding a
 * fourth here would leave the section carrying two.
 */
export function HomePillars() {
	return (
		<section className={cn("border-t border-border", sectionSpacing.foot)}>
			<div className={cn("pb-8", sectionSpacing.head)}>
				<p className={siteText.eyebrow}>Why it is different</p>
				<p className={cn(siteText.h2, "mt-2")}>Three things NotebookLM cannot do</p>
			</div>

			<div className="ss-home-grid ss-home-grid-dashed md:grid-cols-3">
				{PILLARS.map((pillar) => (
					<div key={pillar.title} className="flex flex-col px-6 py-8 md:px-10">
						<h2 className={siteText.h3}>{pillar.title}</h2>
						<p className={cn(siteText.body, "mt-2 text-sm")}>{pillar.body}</p>
						<p className="mt-auto pt-6">
							{pillar.action.external ? (
								<a
									className={siteText.forward}
									href={pillar.action.href}
									target="_blank"
									rel="noreferrer noopener"
								>
									{pillar.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
								</a>
							) : (
								<Link className={siteText.forward} href={pillar.action.href}>
									{pillar.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
								</Link>
							)}
						</p>
					</div>
				))}
			</div>
		</section>
	);
}

/**
 * The comparison table carries no heading of its own, so the brief's H2 order
 * stays intact — the headline below is a `<p>` styled like an H2, not a real
 * one. The caption names the table for assistive technology instead.
 *
 * The scroller is focusable and labelled: on a narrow screen the table is wider
 * than the column, and a keyboard visitor needs to be able to scroll it without
 * a pointer.
 */
export function HomeCompare() {
	return (
		<section className={cn("border-t border-border", sectionSpacing.foot)}>
			<div className={cn("border-b border-border pb-8", sectionSpacing.head)}>
				<p className={siteText.eyebrow}>How it compares</p>
				<p className={cn(siteText.h2, "mt-2")}>Getting started, compared</p>
			</div>

			<section
				className="overflow-x-auto focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
				aria-label="Scrollable comparison table"
				/* biome-ignore lint/a11y/noNoninteractiveTabindex: a region that scrolls horizontally has to be focusable, or a keyboard-only visitor cannot reach the columns past the fold. The labelled landmark is what makes the focus stop meaningful. */
				tabIndex={0}
			>
				<table className="ss-home-table">
					<caption className="sr-only">
						SurfSense compared with NotebookLM, AnythingLLM and Open Notebook
					</caption>
					<thead>
						<tr>
							<th scope="col">
								<span className="sr-only">Capability</span>
							</th>
							<th scope="col" data-col="ours">
								SurfSense
							</th>
							<th scope="col">NotebookLM</th>
							<th scope="col">AnythingLLM</th>
							<th scope="col">Open Notebook</th>
						</tr>
					</thead>
					<tbody>
						{COMPARE_ROWS.map((row) => (
							<tr key={row.label}>
								<th scope="row">{row.label}</th>
								<td data-col="ours">{row.ours}</td>
								<td>{row.notebooklm}</td>
								<td>{row.anythingllm}</td>
								<td>{row.openNotebook}</td>
							</tr>
						))}
					</tbody>
				</table>
			</section>
		</section>
	);
}

/**
 * H2 #5, #6, #7 — the reference's `Pricing` block: a header, then cells that
 * pair a claim with the concrete things that back it, each ruled off from the
 * next.
 *
 * The band's own headline is a `<p>` styled like an H2, not a real one — the
 * three real H2s the brief wants are each story's own heading, rendered by
 * `HomeFeaturesTabs` below.
 */
export function HomeFeatures() {
	return (
		<section className={cn("border-t border-border", sectionSpacing.foot)}>
			<div className={cn("border-b border-border pb-8", sectionSpacing.head)}>
				<p className={siteText.eyebrow}>What you get</p>
				<p className={cn(siteText.h2, "mt-2")}>Three things worth knowing before you install</p>
			</div>

			<HomeFeaturesTabs />
		</section>
	);
}

/**
 * H2 #8 — *For confidential work*, added to the brief on 17 Sep 2026.
 *
 * Sits directly after H2 #7 (*Private by construction*, the last of the claims
 * tabs) because it answers the question that one raises: privacy for whom. The
 * brief asks for one paragraph rather than a section, so this is a single
 * statement band with no grid and no proof list — the argument is made in full
 * on the page it links to.
 */
export function HomeConfidential() {
	return (
		<section className={cn("border-t border-border", sectionSpacing.foot)}>
			<div className={cn("max-w-3xl", sectionSpacing.head)}>
				<p className={siteText.eyebrow}>{CONFIDENTIAL.eyebrow}</p>
				<h2 className={cn(siteText.h2, "mt-2")}>{CONFIDENTIAL.heading}</h2>
				<p className={cn(siteText.body, "mt-5")}>{CONFIDENTIAL.body}</p>
				<p className="mt-6">
					<Link className={siteText.forward} href={CONFIDENTIAL.action.href}>
						{CONFIDENTIAL.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
					</Link>
				</p>
			</div>
		</section>
	);
}
