import type { ReactNode } from "react";

/** A frosted pill for text set on a painted scene. */
export function GlassChip({ icon, label }: { icon: ReactNode; label: string }) {
	return (
		<span className="flex h-10 shrink-0 items-center gap-2 rounded-full bg-black/15 px-4 text-sm font-medium whitespace-nowrap text-white backdrop-blur-sm [&_svg]:size-4">
			{icon}
			{label}
		</span>
	);
}
