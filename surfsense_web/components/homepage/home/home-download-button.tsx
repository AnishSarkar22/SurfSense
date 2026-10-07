import Link from "next/link";
import { DOWNLOADS_URL } from "@/components/site/site-content";
import { ArrowRightIcon } from "@/components/ui/icons";

/** The download pill for sections set on the meadow scene, where the
 *  outlined `FlowButton` would disappear into the photo. */
export function HomeDownloadButton() {
	return (
		<Link
			href={DOWNLOADS_URL}
			className="group inline-flex h-11 items-center gap-2.5 rounded-full bg-card pr-1.5 pl-5 text-sm font-semibold text-foreground shadow-lg transition-colors duration-150 hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
		>
			Download for desktop
			<span className="grid size-8 place-items-center rounded-full bg-foreground text-background">
				<ArrowRightIcon
					aria-hidden="true"
					className="size-4 transition-transform duration-150 group-hover:translate-x-0.5"
				/>
			</span>
		</Link>
	);
}
