import { CircleCheck } from "lucide-react";
import Link from "next/link";
import { HomeButton } from "@/components/homepage/home/home-button";
import { PlatformsTooltip } from "@/components/pricing/platforms-tooltip";
import {
	PLANS,
	PLUGIN_NOTE,
	type Plan,
	PRICING_FAQ,
	SELF_BUILD_URL,
	SMALL_GROUP_NOTE,
} from "@/components/pricing/pricing-content";
import { FAQJsonLd } from "@/components/seo/json-ld";
import { SiteFaqItem } from "@/components/site/site-faq-item";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * Splits a feature string around "9 platforms" so that segment alone can be
 * wrapped in `PlatformsTooltip` — the rest of the line renders as plain text.
 */
function renderFeature(feature: string) {
	const marker = "9 platforms";
	const index = feature.indexOf(marker);
	if (index === -1) return feature;

	return (
		<>
			{feature.slice(0, index)}
			<PlatformsTooltip>{marker}</PlatformsTooltip>
			{feature.slice(index + marker.length)}
		</>
	);
}

/**
 * Pricing sections.
 *
 * Tailwind plus the shared `siteText` styles, the same ruled bands and hairline
 * grids as the landing page, so the two read as one document.
 *
 * All server components. The previous pricing page was a client component
 * carrying `motion`, `canvas-confetti`, `NumberFlow` and a monthly/yearly switch
 * whose two prices were identical in every tier.
 */

/**
 * The brief's first rule for this page is to lead with free: the answer to "is
 * it free?" has to be on the first screen, in plain words, before any tier
 * table. Burying it reads as a bait-and-switch to an audience that arrived via
 * the words "open source".
 */
export function PricingHero() {
	return (
		<section className="py-20 md:py-28">
			<div className="mx-auto max-w-3xl text-center">
				<h1 className={siteText.display}>Pricing</h1>
				<p className={cn(siteText.lede, "mx-auto mt-8 max-w-2xl")}>
					The app and every update are <span className="text-primary">free, forever</span>, with no
					account, no trial clock and no usage cap. A licence adds the scraper plugins and priority
					support, and a 30-day one comes with the app.
				</p>
				<p className={cn(siteText.body, "mx-auto mt-5 max-w-2xl text-sm")}>
					Prefer to build it yourself?{" "}
					<a
						className={siteText.link}
						href={SELF_BUILD_URL}
						target="_blank"
						rel="noreferrer noopener"
					>
						The source is public
					</a>
					, and self-building is free too.
				</p>
			</div>
		</section>
	);
}

function PlanCell({ plan }: { plan: Plan }) {
	return (
		<div
			className="ss-home-plan data-featured:bg-secondary"
			data-featured={plan.featured ? "" : undefined}
		>
			<div className="relative flex flex-col px-6 py-8 after:absolute after:inset-x-6 after:bottom-0 after:h-px after:bg-border md:px-10 md:after:inset-x-10">
				<p className="flex items-center gap-2">
					<span className={siteText.eyebrow}>{plan.name}</span>
					{plan.featured ? (
						<span className="rounded-xs bg-primary px-1.5 py-0.5 text-[10px] font-semibold tracking-wider whitespace-nowrap text-background uppercase">
							Most popular
						</span>
					) : null}
				</p>

				<p className="mt-3 flex items-baseline gap-1">
					<span className="text-4xl leading-none font-semibold tracking-tight tabular-nums text-foreground md:text-5xl">
						{plan.price}
					</span>
					{plan.period ? (
						<span className={cn(siteText.body, "text-sm font-medium")}>{plan.period}</span>
					) : null}
				</p>

				{plan.note ? <p className="mt-2 text-sm font-medium text-primary">{plan.note}</p> : null}

				<p className={cn(siteText.body, "mt-2 text-sm")}>{plan.summary}</p>

				{/* Pushed to the foot of the head, which subgrid holds to a common
				    height across the three tiers, so the buttons sit on one line
				    however each summary wraps. */}
				<div className="mt-auto space-x-4 pt-6">
					{plan.action.map((action) => (
						<HomeButton
							key={action.label}
							asChild
							size="lg"
							variant={action.primary ? "default" : "secondary"}
						>
							{action.external ? (
								<a href={action.href} target="_blank" rel="noreferrer noopener">
									{action.label}
								</a>
							) : (
								<Link href={action.href}>{action.label}</Link>
							)}
						</HomeButton>
					))}
				</div>
			</div>

			{/* Rows are separated by their own top border rather than by a 1px grid
			    gap. A gap-drawn grid stretches its rows to fill the column, so a
			    short tier's rows would grow to match a long one's. */}
			<ul className="m-0 list-none py-4">
				{plan.features.map((feature) => (
					<li
						key={feature}
						className="flex items-start gap-3 px-6 py-2 text-sm leading-relaxed text-muted-foreground md:px-10"
					>
						<CircleCheck aria-hidden="true" className="mt-1 size-3.5 flex-none text-primary" />
						<span>{renderFeature(feature)}</span>
					</li>
				))}
			</ul>
		</div>
	);
}

export function PricingPlans() {
	return (
		<section className="border-t border-border">
			<div className="ss-home-grid ss-home-plans md:grid-cols-3">
				{PLANS.map((plan) => (
					<PlanCell key={plan.name} plan={plan} />
				))}
			</div>

			<div className="flex flex-col gap-8 border-t border-border py-8">
				<p className={cn(siteText.body, "max-w-4xl text-sm")}>{PLUGIN_NOTE}</p>
				<p className={cn(siteText.body, "max-w-4xl text-sm")}>
					{SMALL_GROUP_NOTE}{" "}
					<Link className={siteText.link} href="/contact">
						Talk to us
					</Link>
					.
				</p>
			</div>
		</section>
	);
}

/**
 * One flat list, labelled once. The previous version grouped the questions under
 * five sub-headings, which put a heading between almost every pair of rows and
 * broke the ruled column into fragments.
 */
export function PricingQuestions() {
	return (
		<section className="border-t border-border" aria-labelledby="ss-pricing-faq-label">
			<div className="border-b border-border pt-10 pb-8 md:pt-40">
				<p className={siteText.eyebrow}>FAQ</p>
				<h2 id="ss-pricing-faq-label" className={cn(siteText.h2, "mt-2")}>
					Questions about licences
				</h2>
			</div>

			<div className="ss-home-grid">
				{PRICING_FAQ.map((item) => (
					<SiteFaqItem key={item.question} question={item.question}>
						<p className={siteText.body}>{item.answer}</p>
					</SiteFaqItem>
				))}
			</div>

			<FAQJsonLd questions={PRICING_FAQ} />
		</section>
	);
}
