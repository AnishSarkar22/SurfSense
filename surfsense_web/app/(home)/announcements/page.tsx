"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect } from "react";
import { HomeBadge } from "@/components/homepage/home/home-badge";
import { siteText } from "@/components/site/site-text";
import { LinkSquare02Icon, Notification03Icon } from "@/components/ui/icons";
import type { AnnouncementCategory } from "@/contracts/types/announcement.types";
import { type AnnouncementWithState, useAnnouncements } from "@/hooks/use-announcements";
import { formatRelativeDate } from "@/lib/format-date";
import { cn } from "@/lib/utils";

/**
 * Rendered in the site design: listed in `SITE_DESIGN_ROUTES` in
 * `components/site/site-shell.tsx`, so the palette, ruled column, navigation
 * and footer all come from the site shell.
 *
 * The card here is page-local rather than a reuse of
 * `components/announcements/AnnouncementCard.tsx`: that component also backs
 * the in-app `AnnouncementsDialog` (the dashboard's "What's New" popover),
 * which stays on its own shadcn styling untouched by this page's redesign.
 */

const categoryConfig: Record<AnnouncementCategory, { label: string }> = {
	feature: { label: "Feature" },
	update: { label: "Update" },
	maintenance: { label: "Maintenance" },
	info: { label: "Info" },
};

function AnnouncementRow({ announcement }: { announcement: AnnouncementWithState }) {
	const config = categoryConfig[announcement.category] ?? categoryConfig.info;

	return (
		<article className="py-8 flex flex-col gap-4 md:flex-row md:gap-8">
			<div className="flex h-min shrink-0 flex-col items-start gap-3 md:w-48 md:sticky md:top-24">
				<time className={siteText.eyebrow}>{formatRelativeDate(announcement.date)}</time>
				<HomeBadge>{config.label}</HomeBadge>
				{announcement.isImportant && <HomeBadge>Important</HomeBadge>}
			</div>

			<div className="flex min-w-0 max-w-2xl flex-1 flex-col">
				{announcement.image && (
					<div className="relative mb-4 aspect-video w-full overflow-hidden border border-border">
						<Image
							src={announcement.image.src}
							alt={announcement.image.alt}
							fill
							sizes="(max-width: 768px) 100vw, 640px"
							className="object-cover"
						/>
					</div>
				)}
				<h2 className={cn(siteText.h3, "mb-2 text-xl md:text-2xl")}>{announcement.title}</h2>
				<p className={siteText.body}>{announcement.description}</p>
				{announcement.link && (
					<Link
						href={announcement.link.url}
						target={announcement.link.url.startsWith("http") ? "_blank" : undefined}
						className={cn(siteText.forward, "mt-4 self-start")}
					>
						{announcement.link.label}
						<LinkSquare02Icon className="size-3.5" />
					</Link>
				)}
			</div>
		</article>
	);
}

function EmptyState() {
	return (
		<div className="flex flex-col items-center py-24 text-center">
			<Notification03Icon className="mb-4 size-8 text-muted-foreground" />
			<h3 className={siteText.h3}>Nothing new yet</h3>
			<p className={cn(siteText.body, "mt-2 max-w-xs")}>
				You're all caught up! New updates will appear here.
			</p>
		</div>
	);
}

export default function AnnouncementsPage() {
	const { announcements, markAllRead } = useAnnouncements({ includeExpired: true });

	// Auto-mark all visible announcements as read when the page is opened
	useEffect(() => {
		markAllRead();
	}, [markAllRead]);

	return (
		<>
			<section className="py-20 md:py-28">
				<div className="mx-auto max-w-2xl text-center">
					<h1 className={siteText.display}>What's New</h1>
					<p className={cn(siteText.lede, "mx-auto mt-6 max-w-xl")}>
						Product updates, features and fixes as they ship.
					</p>
				</div>
			</section>

			<section>
				{announcements.length === 0 ? (
					<EmptyState />
				) : (
					announcements.map((announcement, index) => (
						<div key={announcement.id} className={index > 0 ? "border-t border-border" : undefined}>
							<AnnouncementRow announcement={announcement} />
						</div>
					))
				)}
			</section>
		</>
	);
}
