import Link from "next/link";
import { HomeAnnouncement } from "@/components/homepage/home/home-announcement";
import { HomeArtifactIllustration } from "@/components/homepage/home/home-artifact-illustration";
import {
	type Cell,
	COMPARE_ROWS,
	CONFIDENTIAL,
	FORMATS,
	type IllustratedCell,
	ON_YOUR_MACHINE,
	PILLARS,
} from "@/components/homepage/home/home-content";
import { HomeDownloadButton } from "@/components/homepage/home/home-download-button";
import { HomeFeaturesTabs } from "@/components/homepage/home/home-features-tabs";
import { HomeFormatCell } from "@/components/homepage/home/home-format-cell";
import { HomeScene } from "@/components/homepage/home/home-scene";
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
 * controls keep the palette's `--radius`. Styled with Tailwind plus the shared
 * `siteText` styles.
 *
 * Mostly server components. Two exceptions live in their own "use client"
 * modules rather than pulling this file across the boundary:
 * `HomeFeaturesTabs` (the claims switcher) and `CardSpotlight`
 * (components/ui), which `HomeFormatCell` wraps each format cell in for its
 * hover spotlight.
 *
 * The heading order is not editorial. It is the SEO skeleton from
 * `plans/community-local/seo/02-page-briefs.md`: H1, then eight H2s in a fixed
 * order. Sections may be restyled freely; the sequence of headings may not be
 * reordered without re-reading that brief.
 */

export function HomeHero() {
	return (
		// Full bleed, and pulled up under the sticky nav (`-mt-18` is the nav's
		// height) so the scene starts at the top edge of the page. Copy sits in
		// the sky, where the wash keeps white text readable.
		<section className="-mt-18">
			<div className="relative flex min-h-svh flex-col items-center justify-center overflow-hidden px-6 pt-32 pb-24 text-center">
				<HomeScene priority />
				<div
					aria-hidden="true"
					className="absolute inset-0 bg-linear-to-b from-black/45 via-black/20 to-transparent"
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
 * A bento cell. `illustration` renders a designed SVG in place of the usual
 * figure — some cells in this grid have something to show rather than only
 * say.
 */
function BentoCell({ title, body, illustration }: Cell & { illustration?: IllustratedCell }) {
	return (
		<div className="relative overflow-hidden px-6 py-8 md:px-10">
			{illustration ? <HomeArtifactIllustration illustration={illustration} /> : null}
			<div className="relative">
				<p className={siteText.h3}>{title}</p>
				<p className={cn(siteText.body, "mt-1.5 max-w-sm text-sm")}>{body}</p>
			</div>
		</div>
	);
}

/**
 * H2 #1 — the offline / local / air-gapped claim.
 *
 * A plain heading band, not a fourth cell: the eyebrow-plus-headline pair
 * introduces the row of three bento cells below it rather than sitting beside
 * them as an equal-weight panel, the way `HomePillars` introduces its own row.
 *
 * The headline is the brief's exact H2 #1 text; `Features` moved up to become
 * the small kicker above it instead of replacing it.
 */
export function HomeOnYourMachine() {
	return (
		<section>
			<div className="px-6 pt-10 pb-8 md:px-10 md:pt-40">
				<p className={siteText.eyebrow}>Features</p>
				<h2 className={cn(siteText.h2, "mt-2")}>Runs entirely on your machine</h2>
			</div>

			<div className="ss-home-grid ss-home-grid-dashed md:grid-cols-3">
				{ON_YOUR_MACHINE.map((cell) => (
					<BentoCell key={cell.title} {...cell} />
				))}
			</div>
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
		<section className="border-t border-border">
			<div className="px-6 pt-10 pb-8 md:px-10 md:pt-40">
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
		<section className="border-t border-border">
			<div className="border-b border-border px-6 pt-10 pb-8 md:px-10 md:pt-40">
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
		<section className="border-t border-border">
			<div className="border-b border-border px-6 pt-10 pb-8 md:px-10 md:pt-40">
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
		<section className="border-t border-border">
			<div className="px-6 py-16 md:px-10 md:py-24">
				<div className="max-w-3xl">
					<p className={siteText.eyebrow}>{CONFIDENTIAL.eyebrow}</p>
					<h2 className={cn(siteText.h2, "mt-2")}>{CONFIDENTIAL.heading}</h2>
					<p className={cn(siteText.body, "mt-5")}>{CONFIDENTIAL.body}</p>
					<p className="mt-6">
						<Link className={siteText.forward} href={CONFIDENTIAL.action.href}>
							{CONFIDENTIAL.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
						</Link>
					</p>
				</div>
			</div>
		</section>
	);
}

/**
 * Not one of the brief's eight H2s (see `FORMATS`'s own doc comment in
 * `home-content.ts`) — a bento row of the twelve Studio formats, below the
 * claims tabs. `HomeFormatCell` is the one client component in the row (a
 * cursor-tracked hover spotlight); this section itself stays server-rendered.
 */
export function HomeFormats() {
	return (
		<section className="border-t border-border">
			<div className="px-6 pt-10 pb-8 md:px-10 md:pt-40">
				<p className={siteText.eyebrow}>Artifacts</p>
				<p className={cn(siteText.h2, "mt-2")}>Twelve things one set of sources can become</p>
			</div>

			{/* The same grid as the logo cloud: the head is plain, so the grid draws its
			    own top edge, and each cell draws its own right and bottom hairlines. */}
			<div className="relative grid grid-cols-2 border-t border-border md:grid-cols-4">
				{FORMATS.map((format, index) => (
					<HomeFormatCell key={format.key} format={format} index={index} />
				))}
			</div>
		</section>
	);
}
