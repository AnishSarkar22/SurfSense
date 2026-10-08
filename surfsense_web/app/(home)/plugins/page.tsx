import type { Metadata } from "next";
import Link from "next/link";
import { HomeBadge } from "@/components/homepage/home/home-badge";
import { AmazonLogo } from "@/components/homepage/icons/amazon-logo";
import { GoogleMapsLogo } from "@/components/homepage/icons/google-maps-logo";
import { GoogleSearchLogo } from "@/components/homepage/icons/google-search-logo";
import { IndeedLogo } from "@/components/homepage/icons/indeed-logo";
import { InstagramLogo } from "@/components/homepage/icons/instagram-logo";
import { RedditLogo } from "@/components/homepage/icons/reddit-logo";
import { TiktokLogo } from "@/components/homepage/icons/tiktok-logo";
import { WalmartLogo } from "@/components/homepage/icons/walmart-logo";
import { WebCrawlLogo } from "@/components/homepage/icons/web-crawl-logo";
import { YoutubeLogo } from "@/components/homepage/icons/youtube-logo";
import { siteText } from "@/components/site/site-text";
import { ArrowUpRight01Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

/**
 * Plugins page.
 *
 * Rendered in the site design: the palette, ruled column, navigation and footer
 * all come from `app/(home)/layout.tsx`; the page is Tailwind plus the shared
 * `siteText` styles. Listed in `SITE_DESIGN_ROUTES` in
 * `components/site/site-shell.tsx`.
 *
 * The page is a placeholder while the plugins ship, so it says the one thing a
 * visitor came for (which platforms are covered) and nothing else. The list is
 * declared here rather than read from a registry: this page is the whole of
 * what the site claims about plugins.
 *
 * Each tile links to that platform's existing marketing page under
 * `lib/connectors-marketing` — the plugin itself is not live yet, but the page
 * explaining what it will do already is.
 *
 * Logos are inline components from `components/homepage/icons/`, so they
 * arrive in the HTML and paint with the page instead of loading one request
 * each afterwards. They are the marketing site's own copies of the brand
 * marks the product's connector picker reads from `public/connectors/`.
 *
 * Replaces the old `/connectors` index, which now redirects here from
 * `next.config.ts`.
 *
 * A server component with no client JavaScript.
 */

const canonicalUrl = "https://www.surfsense.com/plugins";

const metaTitle = "SurfSense Plugins: Scrapers for Every Platform";
const metaDescription =
	"Scraper plugins for Reddit, YouTube, Instagram, TikTok, Google Maps, Google Search, Indeed, Amazon, Walmart and the open web. Coming soon to SurfSense.";

export const metadata: Metadata = {
	title: metaTitle,
	description: metaDescription,
	alternates: { canonical: canonicalUrl },
	openGraph: {
		title: metaTitle,
		description: metaDescription,
		url: canonicalUrl,
		siteName: "SurfSense",
		type: "website",
		images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "SurfSense plugins" }],
	},
	twitter: {
		card: "summary_large_image",
		title: metaTitle,
		description: metaDescription,
		images: ["/og-image.png"],
	},
};

const PLUGINS = [
	{ name: "Reddit", href: "/reddit", Logo: RedditLogo },
	{ name: "YouTube", href: "/youtube", Logo: YoutubeLogo },
	{ name: "Instagram", href: "/instagram", Logo: InstagramLogo },
	{ name: "TikTok", href: "/tiktok", Logo: TiktokLogo },
	{ name: "Google Maps", href: "/google-maps", Logo: GoogleMapsLogo },
	{ name: "Google Search", href: "/google-search", Logo: GoogleSearchLogo },
	{ name: "Indeed", href: "/indeed", Logo: IndeedLogo },
	{ name: "Amazon", href: "/amazon", Logo: AmazonLogo },
	{ name: "Walmart", href: "/walmart", Logo: WalmartLogo },
	{ name: "Web Crawl", href: "/web-crawl", Logo: WebCrawlLogo },
];

export default function PluginsPage() {
	return (
		<>
			<section className="py-20 md:py-28">
				<div className="mx-auto max-w-3xl text-center">
					<HomeBadge>Coming soon</HomeBadge>
					<h1 className={cn(siteText.display, "mt-4")}>
						Plugins for the platforms your <span className="text-primary">answers live on</span>
					</h1>
					<p className={cn(siteText.lede, "mx-auto mt-8 max-w-2xl")}>
						Each plugin pulls public data from one platform straight into your notebook. These are
						the ones being built first.
					</p>
				</div>
			</section>

			<section className="border-t border-border" aria-labelledby="ss-plugins-label">
				<div className="border-b border-border pt-10 pb-8 md:pt-40">
					<p className={siteText.eyebrow}>Plugins</p>
					<h2 id="ss-plugins-label" className={cn(siteText.h2, "mt-2")}>
						Shipping first
					</h2>
				</div>

				<ul className="ss-home-grid list-none p-0 sm:grid-cols-2 md:grid-cols-3">
					{PLUGINS.map((plugin) => (
						<li key={plugin.name}>
							<Link
								href={plugin.href}
								className="group flex items-center gap-3 px-6 py-8 text-inherit transition-colors duration-100 hover:bg-secondary focus-visible:bg-secondary focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring md:px-10"
							>
								<plugin.Logo className="size-5 shrink-0" />
								<span className={siteText.h3}>{plugin.name}</span>
								<ArrowUpRight01Icon
									aria-hidden="true"
									className="ml-auto size-4 shrink-0 text-muted-foreground transition-[transform,color] duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary group-focus-visible:translate-x-0.5 group-focus-visible:-translate-y-0.5 group-focus-visible:text-primary"
								/>
							</Link>
						</li>
					))}
					{/* Fills out the last row of the three-column grid: ten platforms is
					    not a multiple of three, and this says so instead of leaving the
					    row's remaining cells empty. Not a link — there is nothing to open
					    yet for whatever comes after this list. */}
					<li className="md:col-span-2">
						<div className="flex items-center px-6 py-8 text-muted-foreground md:px-10">
							<span className="text-sm">And many more on the way</span>
						</div>
					</li>
				</ul>
			</section>

			<section className="border-t border-border py-12">
				<p className={cn(siteText.body, "mx-auto max-w-2xl text-center text-sm")}>
					Need a platform that is not on this list?{" "}
					<Link className={siteText.link} href="/contact">
						Tell us which one
					</Link>
					.
				</p>
			</section>
		</>
	);
}
