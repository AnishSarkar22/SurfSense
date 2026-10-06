"use client";

import Link from "next/link";
import { useRef } from "react";
import { PROOF_POINTS, STORIES } from "@/components/homepage/home/home-content";
import { siteText } from "@/components/site/site-text";
import { ArrowRightIcon, CheckIcon, ChevronDownIcon } from "@/components/ui/icons";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

// Matches the `max-md:` variant that switches the layout to an accordion.
const ACCORDION_QUERY = "(max-width: 767px)";

/**
 * H2 #5, #6, #7 as a tabbed switcher rather than three stacked rows.
 *
 * All three panels stay mounted (`forceMount`) so all three real H2s are in
 * the markup regardless of which tab is open — the heading sequence this
 * section owes the SEO brief does not depend on the active tab. They are
 * stacked in one grid cell so the section's height is always the tallest
 * panel's height: switching tabs never changes it, so nothing below the
 * section moves.
 *
 * Inactive panels hide with `invisible`, not `hidden`, so they still count
 * toward that height.
 *
 * Below 768px the same tabs lay out as an accordion: `max-md:contents` flattens
 * the list and the panel stack, and the `order` pairs each panel with its
 * trigger. One component rather than a second accordion, so the three H2s
 * appear once; the trigger shows the heading, so the H2 is visually hidden.
 */
export function HomeFeaturesTabs() {
	const triggers = useRef(new Map<string, HTMLButtonElement>());

	// Closing the panel above the tapped row pulls that row up, possibly off screen.
	const keepOpenedRowInView = (value: string) => {
		if (!window.matchMedia(ACCORDION_QUERY).matches) return;
		requestAnimationFrame(() => triggers.current.get(value)?.scrollIntoView({ block: "nearest" }));
	};

	return (
		<Tabs
			defaultValue={STORIES[0].key}
			onValueChange={keepOpenedRowInView}
			className="max-md:flex max-md:flex-col max-md:gap-px max-md:bg-border"
		>
			<TabsList className="ss-home-grid grid h-auto items-stretch justify-normal rounded-none border-b border-border bg-border p-0 max-md:contents md:grid-cols-3">
				{STORIES.map((story, index) => (
					<TabsTrigger
						key={story.key}
						value={story.key}
						ref={(node) => {
							if (node) triggers.current.set(story.key, node);
							else triggers.current.delete(story.key);
						}}
						style={{ order: index * 2 }}
						className="group/tab flex flex-col items-start justify-start gap-2 rounded-none border-t-2 border-transparent px-6 py-5 text-left whitespace-normal shadow-none transition-colors duration-100 hover:bg-secondary focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-solid focus-visible:outline-ring data-[state=active]:border-primary data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-none max-md:w-full max-md:flex-row max-md:items-center max-md:gap-3.5 max-md:border-t-0 max-md:border-l-2 max-md:py-4 md:px-10"
					>
						<span className="font-mono text-xs text-muted-foreground group-data-[state=active]/tab:text-primary">
							{String(index + 1).padStart(2, "0")}
						</span>
						<span className="text-sm leading-snug font-semibold tracking-tight text-foreground max-md:flex-1">
							{story.heading}
						</span>
						<ChevronDownIcon
							aria-hidden="true"
							className="hidden size-4 shrink-0 text-muted-foreground transition-transform duration-150 group-data-[state=active]/tab:rotate-180 motion-reduce:transition-none max-md:block"
						/>
					</TabsTrigger>
				))}
			</TabsList>

			<div className="grid grid-cols-1 *:min-w-0 *:[grid-area:1/1] max-md:contents">
				{STORIES.map((story, index) => (
					<TabsContent
						key={story.key}
						value={story.key}
						forceMount
						style={{ order: index * 2 + 1 }}
						className="ss-home-grid mt-0 data-[state=inactive]:pointer-events-none data-[state=inactive]:invisible max-md:data-[state=inactive]:hidden lg:grid-cols-2"
					>
						<div className="flex flex-col justify-center px-6 py-12 max-md:pt-0 max-md:pb-6 md:px-10 lg:py-16">
							<h2 className={cn(siteText.h2, "max-md:sr-only")}>{story.heading}</h2>
							<div className={cn(siteText.body, "mt-5 flex flex-col gap-4")}>
								{story.body.map((paragraph) => (
									<p key={paragraph}>{paragraph}</p>
								))}
							</div>
							<p className="mt-6">
								{story.action.external ? (
									<a
										className={siteText.forward}
										href={story.action.href}
										target="_blank"
										rel="noreferrer noopener"
									>
										{story.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
									</a>
								) : (
									<Link className={siteText.forward} href={story.action.href}>
										{story.action.label} <ArrowRightIcon aria-hidden="true" className="size-4" />
									</Link>
								)}
							</p>
						</div>

						<ul className="ss-home-grid m-0 list-none p-0">
							{PROOF_POINTS[story.key].map((point) => (
								<li key={point} className="flex items-center gap-3 px-6 py-3.5 md:px-10">
									<CheckIcon aria-hidden="true" className="size-3.5 shrink-0 text-primary" />
									<span className={cn(siteText.body, "text-sm")}>{point}</span>
								</li>
							))}
						</ul>
					</TabsContent>
				))}
			</div>
		</Tabs>
	);
}
