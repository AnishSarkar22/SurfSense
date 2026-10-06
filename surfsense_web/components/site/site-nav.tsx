"use client";

import { IconChevronDown } from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { TopAnnouncementBar } from "@/components/homepage/top-announcement-bar";
import { DOWNLOADS_URL, NAV_LINKS, NAV_RESOURCES } from "@/components/site/site-content";
import { SiteStars } from "@/components/site/site-stars";
import { ArrowRightIcon } from "@/components/ui/icons";

/**
 * Site navigation.
 *
 * Rendered once by `app/(home)/layout.tsx`, above any route branch, so it is a
 * single element in a single slot for every page. React therefore keeps it
 * mounted across navigations: the drawer, the dropdown, the scroll listener and
 * the star query all survive, and only the content below it changes. Rendering
 * a different nav per route — which is what this replaced — made React unmount
 * one component and mount another, resetting all of that on every link click.
 *
 * A floating bar, inset from the viewport edges and pinned to the top. It looks
 * the same at every scroll position: no blur or shadow that appears on scroll.
 *
 * It carries no palette of its own. Inside `.ss-home` it picks up the pinned
 * dark palette; everywhere else it picks up the same token names from
 * `globals.css` and follows the visitor's theme.
 *
 * The star count arrives as a prop rather than being fetched here: it is read
 * and cached on the server, so it is already in the HTML on first paint.
 */

const MENU_ID = "site-nav-menu";

function Wordmark() {
	return (
		<Link
			href="/"
			className="select-none flex shrink-0 items-center gap-1.5 rounded-lg px-1 py-1 transition-colors duration-100 hover:text-[color:var(--muted-foreground)] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[color:var(--ring)]"
		>
			<Image
				src="/icon-128.svg"
				alt=""
				width={20}
				height={20}
				priority
				className="size-6 dark:invert"
			/>
			<span className="ss-home-wordmark text-lg text-[color:var(--foreground)]">SurfSense</span>
		</Link>
	);
}

function DownloadLink({ onClick }: { onClick?: () => void }) {
	return (
		<Link href={DOWNLOADS_URL} onClick={onClick} className="ss-home-nav-cta">
			Download
			<span aria-hidden="true" className="ss-home-nav-cta-icon">
				<ArrowRightIcon className="size-4" />
			</span>
		</Link>
	);
}

export function SiteNav({ starCount, starsHref }: { starCount: number | null; starsHref: string }) {
	const [menuOpen, setMenuOpen] = useState(false);
	const [resourcesOpen, setResourcesOpen] = useState(false);
	const headerRef = useRef<HTMLElement>(null);

	// Escape closes whatever is open; a click outside the header closes the
	// dropdown. Both match what a visitor expects from a menu regardless of how
	// it was opened.
	useEffect(() => {
		if (!menuOpen && !resourcesOpen) {
			return;
		}

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setMenuOpen(false);
				setResourcesOpen(false);
			}
		};
		const onPointerDown = (event: PointerEvent) => {
			if (!headerRef.current?.contains(event.target as Node)) {
				setResourcesOpen(false);
			}
		};

		document.addEventListener("keydown", onKeyDown);
		document.addEventListener("pointerdown", onPointerDown);
		return () => {
			document.removeEventListener("keydown", onKeyDown);
			document.removeEventListener("pointerdown", onPointerDown);
		};
	}, [menuOpen, resourcesOpen]);

	const closeAll = () => {
		setMenuOpen(false);
		setResourcesOpen(false);
	};

	return (
		<>
			{/* Outside the sticky header, so it scrolls away and only the floating
			    bar stays pinned. */}
			<TopAnnouncementBar />

			<header ref={headerRef} className="ss-home-nav">
				<div className="ss-home-nav-bar">
					<Wordmark />

					<nav className="ss-home-nav-links" aria-label="Main">
						{NAV_LINKS.map((link) => (
							<Link key={link.href} href={link.href} className="ss-home-nav-link">
								{link.name}
							</Link>
						))}

						<div className="relative">
							<button
								type="button"
								className="ss-home-nav-link"
								aria-expanded={resourcesOpen}
								onClick={() => setResourcesOpen((open) => !open)}
							>
								Resources
								<IconChevronDown
									aria-hidden="true"
									className={`size-3.5 shrink-0 transition-transform duration-150 ${
										resourcesOpen ? "rotate-180" : ""
									}`}
								/>
							</button>

							{resourcesOpen ? (
								<div className="ss-home-nav-panel">
									{NAV_RESOURCES.map((item) => (
										<Link
											key={item.href}
											href={item.href}
											onClick={closeAll}
											className="ss-home-nav-item"
										>
											<span className="text-[0.8125rem] font-medium text-[color:var(--foreground)]">
												{item.name}
											</span>
											<span className="text-xs text-[color:var(--muted-foreground)]">
												{item.description}
											</span>
										</Link>
									))}
								</div>
							) : null}
						</div>
					</nav>

					<div className="ss-home-nav-actions">
						<SiteStars count={starCount} href={starsHref} />
						<DownloadLink />

						<button
							type="button"
							onClick={() => {
								setMenuOpen((open) => !open);
								setResourcesOpen(false);
							}}
							aria-label={menuOpen ? "Close menu" : "Open menu"}
							aria-expanded={menuOpen}
							aria-controls={MENU_ID}
							data-state={menuOpen ? "open" : "closed"}
							className="ss-home-nav-toggle"
						>
							{/* One icon whose bars morph between menu and close, rather than
							    two icons swapped in a single frame. */}
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								strokeWidth={2}
								strokeLinecap="round"
								aria-hidden="true"
								className="ss-home-nav-burger"
							>
								<line x1="4" y1="6" x2="20" y2="6" />
								<line x1="4" y1="12" x2="20" y2="12" />
								<line x1="4" y1="18" x2="20" y2="18" />
							</svg>
						</button>
					</div>
				</div>

				{/* The scrim and drawer stay mounted so opening and closing can
				    animate; `inert` keeps the closed drawer out of the tab order and
				    the accessibility tree.

				    The scrim is a tap-to-dismiss ground. It is decorative: Escape and
				    the toggle both already close the menu, so a keyboard user loses
				    nothing by it being unreachable. */}
				<button
					type="button"
					aria-hidden="true"
					tabIndex={-1}
					data-state={menuOpen ? "open" : "closed"}
					className="ss-home-nav-scrim"
					onClick={closeAll}
				/>

				<div
					id={MENU_ID}
					data-state={menuOpen ? "open" : "closed"}
					inert={!menuOpen}
					data-lenis-prevent
					className="ss-home-nav-drawer"
				>
					<div className="flex flex-col gap-0.5">
						{NAV_LINKS.map((link) => (
							<Link
								key={link.href}
								href={link.href}
								onClick={closeAll}
								className="ss-home-nav-link"
							>
								{link.name}
							</Link>
						))}

						<div className="my-2 border-t border-[color:var(--border)]" />
						<p className="ss-home-eyebrow px-3 pt-1 pb-1">Resources</p>

						{NAV_RESOURCES.map((item) => (
							<Link
								key={item.href}
								href={item.href}
								onClick={closeAll}
								className="ss-home-nav-link"
							>
								{item.name}
							</Link>
						))}
					</div>

					{/* Phones only: below `sm` the bar has room for the toggle alone, so
					    the stars and the download move in here. */}
					<div className="ss-home-nav-drawer-actions">
						<SiteStars count={starCount} href={starsHref} />
						<DownloadLink onClick={closeAll} />
					</div>
				</div>
			</header>
		</>
	);
}
