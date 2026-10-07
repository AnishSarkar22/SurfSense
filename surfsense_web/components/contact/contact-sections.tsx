import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import {
	CALL_URL,
	CHANNELS,
	type Channel,
	DISCUSSIONS_URL,
	EMAIL,
} from "@/components/contact/contact-content";
import { HomeButton } from "@/components/homepage/home/home-button";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * Contact sections.
 *
 * Tailwind plus the shared `siteText` styles, the same ruled column and hairline
 * grids as the landing and pricing pages, so the three read as one document.
 *
 * All server components. The page it replaced was a client component carrying
 * `motion`, an animated map pin and a world map SVG, none of which said
 * anything about how to reach us.
 */

export function ContactHero() {
	return (
		<section className="px-6 py-20 md:px-10 md:py-28">
			<div className="mx-auto max-w-3xl text-center">
				<h1 className={siteText.display}>
					Talk to the people who <span className="text-primary">build it</span>
				</h1>
				<p className={cn(siteText.lede, "mx-auto mt-8 max-w-2xl")}>
					SurfSense is a small team, so there is no ticket queue and no contact form that goes
					nowhere. Pick whichever of the four below matches what you need.
				</p>
				<div className="mt-10 flex justify-center">
					<HomeButton asChild size="xl">
						<a href={CALL_URL} target="_blank" rel="noreferrer noopener">
							Book a call
							<ArrowUpRight aria-hidden="true" />
						</a>
					</HomeButton>
				</div>
			</div>
		</section>
	);
}

function ChannelCell({ channel }: { channel: Channel }) {
	const { label, href, external } = channel.action;

	return (
		<div className="flex flex-col px-6 py-8 md:px-10">
			<p className={siteText.eyebrow}>{channel.eyebrow}</p>
			<h2 className={cn(siteText.h3, "mt-3")}>{channel.title}</h2>
			<p className={cn(siteText.body, "mt-2 max-w-md text-sm")}>{channel.body}</p>

			{/* Pinned to the foot of the cell so the four links sit on one line
			    however each body wraps. */}
			<p className="mt-auto pt-6">
				{external ? (
					<a className={siteText.forward} href={href} target="_blank" rel="noreferrer noopener">
						{label}
						<ArrowUpRight aria-hidden="true" className="size-4" />
					</a>
				) : (
					<a className={siteText.forward} href={href}>
						{label}
						<ArrowUpRight aria-hidden="true" className="size-4" />
					</a>
				)}
			</p>
		</div>
	);
}

export function ContactChannels() {
	return (
		<section className="border-t border-border">
			<div className="border-b border-border px-6 pt-10 pb-8 md:px-10 md:pt-40">
				<p className={siteText.eyebrow}>Where to write</p>
				<p className={cn(siteText.body, "mt-2 text-sm")}>
					Four addresses, each for a different kind of message. A bug report sent to a sales call
					helps nobody.
				</p>
			</div>

			<div className="ss-home-grid sm:grid-cols-2">
				{CHANNELS.map((channel) => (
					<ChannelCell key={channel.title} channel={channel} />
				))}
			</div>
		</section>
	);
}

export function ContactBugReports() {
	return (
		<section className="border-t border-border px-6 md:px-10">
			<div className="flex flex-col justify-center py-12 lg:py-16">
				<h2 className={siteText.h2}>Reporting something broken</h2>
				<p className={cn(siteText.body, "mt-6")}>
					SurfSense runs on your machine, which means we cannot look at your logs, your index or
					your model settings. Everything we know about a bug is what the report tells us.
				</p>
				<p className={cn(siteText.body, "mt-3")}>
					Four details turn a report into a fix rather than a round trip. Nothing here asks for your
					documents. Describe the failure, not the file it happened on.
				</p>
				<p className="mt-6">
					<a
						className={siteText.forward}
						href={DISCUSSIONS_URL}
						target="_blank"
						rel="noreferrer noopener"
					>
						Not sure it is a bug? Ask in Discussions
						<ArrowUpRight aria-hidden="true" className="size-4" />
					</a>
				</p>
			</div>
		</section>
	);
}

/**
 * The page's last band: the one thing a licence buyer needs that none of the
 * four channels above states outright: that terms are negotiable, and that
 * there is a human to negotiate them with.
 */
export function ContactEnterprise() {
	return (
		<section className="flex flex-col gap-6 border-t border-border px-6 py-12 md:px-10">
			<h2 className={cn(siteText.h2, "max-w-3xl")}>Enterprise, volume and procurement</h2>
			<p className={cn(siteText.body, "max-w-3xl")}>
				Above 25 seats, or where security review, invoicing and purchase orders are part of the
				process, the published{" "}
				<Link className={siteText.link} href="/pricing">
					pricing
				</Link>{" "}
				stops being the whole answer. Write to{" "}
				<a className={siteText.link} href={`mailto:${EMAIL}`}>
					{EMAIL}
				</a>{" "}
				with your seat count and what your procurement team needs, and you will get a reply from a
				person rather than a form.
			</p>
		</section>
	);
}
