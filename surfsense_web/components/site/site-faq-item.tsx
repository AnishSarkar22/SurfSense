import type { ReactNode } from "react";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * One question in a marketing FAQ.
 *
 * Native details/summary: no client JS, keyboard operable, and the answer stays
 * in the markup for crawlers. The open/close motion and the plus-to-cross
 * marker are `.ss-home-faq*` in `app/(home)/home.css`.
 *
 * `flush` drops the side padding for a list that already sits inside the page
 * gutters; without it a row pads itself, for edge-to-edge lists.
 */
export function SiteFaqItem({
	question,
	flush = false,
	children,
}: {
	question: string;
	flush?: boolean;
	children: ReactNode;
}) {
	const inset = flush ? "px-0" : "px-6 md:px-10";
	return (
		<details className="ss-home-faq">
			<summary
				className={cn(
					"flex cursor-pointer list-none items-center justify-between gap-4 py-5 font-medium transition-colors duration-100 ease-out hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring [&::-webkit-details-marker]:hidden",
					inset
				)}
			>
				<span className={siteText.h3}>{question}</span>
				<span aria-hidden="true" className="ss-home-faq-marker" />
			</summary>
			<div className={cn("pb-6", inset)}>{children}</div>
		</details>
	);
}
