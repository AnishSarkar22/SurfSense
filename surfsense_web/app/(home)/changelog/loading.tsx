import { Skeleton } from "@/components/ui/skeleton";

/** Mirrors `ChangelogTimeline`: a centred hero, then gutter-to-gutter entry rows. */
export default function ChangelogLoading() {
	return (
		<div className="min-h-screen relative pt-20">
			<div className="px-6 py-20 md:px-10 md:py-28">
				<div className="mx-auto flex max-w-2xl flex-col items-center gap-4">
					<Skeleton className="h-12 w-64" />
					<Skeleton className="h-5 w-full max-w-xl" />
				</div>
			</div>

			<div className="pt-12">
				{Array.from({ length: 3 }).map((_, i) => (
					<div
						key={i}
						className={`grid gap-6 px-6 py-10 md:grid-cols-[12rem_1fr] md:gap-10 md:px-10 md:py-12${i > 0 ? " border-t border-border" : ""}`}
					>
						<div className="flex flex-col gap-3">
							<Skeleton className="h-4 w-24" />
							<Skeleton className="h-6 w-16 rounded-full" />
						</div>
						<div className="flex max-w-2xl flex-col gap-4">
							<Skeleton className="h-7 w-2/3" />
							<div className="space-y-2">
								<Skeleton className="h-4 w-full" />
								<Skeleton className="h-4 w-full" />
								<Skeleton className="h-4 w-3/4" />
							</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
