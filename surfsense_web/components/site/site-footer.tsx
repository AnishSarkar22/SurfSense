import Image from "next/image";
import Link from "next/link";
import { HomeDownloadButton } from "@/components/homepage/home/home-download-button";
import { sectionSpacing } from "@/components/homepage/home/home-section-spacing";
import { FOOTER_COLUMNS } from "@/components/site/site-content";
import footerScene from "@/components/site/site-footer-scene.webp";
import { SiteSocials } from "@/components/site/site-socials";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * Site footer: the closing call to action and the site's links, set on a
 * scene of a castle in the clouds.
 *
 * The page's ground fades into the photo's sky from the top, so the download pitch
 * sits on open ground with no card of its own; the links ride a light card
 * over the hill. Rendered by `app/(home)/layout.tsx` for
 * every route under `(home)` except the auth pages.
 */

const LINK_CLASS =
	"text-sm text-muted-foreground transition-colors duration-100 hover:text-foreground focus-visible:rounded-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

const WORDMARK_CLASS =
	"font-[family-name:var(--font-brand)] font-semibold [font-variation-settings:'SOFT'_75,'WONK'_0]";

export function SiteFooter() {
	return (
		<footer className="relative isolate overflow-hidden">
			{/* The 2:1 scene covers the footer at twice its height: about 56rem tall on
			    desktop, about 80rem on a phone where the card's columns stack. */}
			<div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
				<Image
					src={footerScene}
					alt=""
					fill
					sizes="(max-width: 767px) 160rem, max(100vw, 112rem)"
					quality={85}
					placeholder="blur"
					className="object-cover object-center select-none"
				/>
				<div className="absolute inset-x-0 top-0 h-[62%] bg-linear-to-b from-background via-background/85 to-transparent" />
			</div>

			<div className={cn("px-6 pb-16 text-center md:px-10 md:pb-20", sectionSpacing.head)}>
				<p className={cn(siteText.h2, "md:text-5xl")}>Your notebook, on your own machine</p>
				<p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-pretty text-muted-foreground md:text-lg">
					Download SurfSense and keep every document, model key and answer on your own disk. Free,
					open source, no account.
				</p>
				<div className="mt-8 flex justify-center">
					<HomeDownloadButton tone="dark" />
				</div>
			</div>

			<div className="px-4 pb-16 md:px-10 md:pb-24">
				<div className="mx-auto max-w-6xl rounded-3xl bg-card px-6 py-10 shadow-xl md:px-14 md:py-14">
					<div className="grid gap-10 lg:grid-cols-[minmax(0,1.5fr)_repeat(3,minmax(0,1fr))] lg:gap-8">
						<div>
							<Link href="/" className="inline-flex items-center gap-1.5 select-none">
								<Image src="/icon-128.svg" alt="" width={28} height={28} className="size-7" />
								<span className={cn(WORDMARK_CLASS, "text-xl text-foreground")}>SurfSense</span>
							</Link>
							<p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
								One private workspace for everything you read, save and ask.
							</p>
							<Link
								href="/contact"
								className="mt-8 inline-flex h-11 items-center rounded-full bg-foreground px-6 text-sm font-medium text-background transition-colors duration-150 hover:bg-foreground/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
							>
								Contact us
							</Link>
						</div>

						<div className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:contents">
							{FOOTER_COLUMNS.map((column) => (
								<div key={column.heading}>
									<p className="text-base font-medium text-foreground">{column.heading}</p>
									<ul className="mt-4 flex list-none flex-col gap-3 p-0">
										{column.links.map((link) => (
											<li key={link.title}>
												{link.external ? (
													<a
														href={link.href}
														target="_blank"
														rel="noreferrer noopener"
														className={LINK_CLASS}
													>
														{link.title}
													</a>
												) : (
													<Link href={link.href} className={LINK_CLASS}>
														{link.title}
													</Link>
												)}
											</li>
										))}
									</ul>
								</div>
							))}
						</div>
					</div>

					<div className="mt-12 flex flex-col-reverse gap-6 border-t border-border pt-8 sm:flex-row sm:items-center sm:justify-between">
						<p className="text-sm text-muted-foreground">
							&copy; SurfSense {new Date().getFullYear()}. Free and open source.
						</p>
						<SiteSocials />
					</div>
				</div>
			</div>
		</footer>
	);
}
