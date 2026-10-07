import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Shared marketing-page section container: the site's gutters (px-6 md:px-10)
 * and no width cap, so every section edge aligns across the marketing site.
 */
export function MarketingSection({
	children,
	className,
}: {
	children: ReactNode;
	className?: string;
}) {
	return (
		<section className={cn("py-12 sm:py-16", className)}>
			<div className="w-full px-6 md:px-10">{children}</div>
		</section>
	);
}
