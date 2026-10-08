/** A desktop installer, finished, with the three systems it ships for below. */
export function InstallerPreview() {
	return (
		<div className="flex w-full max-w-56 flex-col gap-3">
			<div className="overflow-hidden rounded-xl bg-card shadow-sm ring-1 ring-black/5">
				<div className="flex gap-1 border-b border-border px-3 py-2">
					{["a", "b", "c"].map((dot) => (
						<span key={dot} className="size-1.5 rounded-full bg-muted-foreground/40" />
					))}
				</div>
				<div className="flex flex-col gap-2.5 p-4">
					<span className="text-xs font-medium text-foreground">Installing SurfSense</span>
					<span className="h-1.5 overflow-hidden rounded-full bg-muted">
						<span className="block h-full w-full rounded-full bg-(--notice)" />
					</span>
					<span className="self-end text-[10px] text-muted-foreground">Ready</span>
				</div>
			</div>
			<div className="flex justify-center gap-1.5">
				{["Windows", "macOS", "Linux"].map((os) => (
					<span
						key={os}
						className="rounded-full bg-card px-2.5 py-1 text-[10px] font-medium text-foreground ring-1 ring-black/5"
					>
						{os}
					</span>
				))}
			</div>
		</div>
	);
}
