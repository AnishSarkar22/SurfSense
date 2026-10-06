import { COMPANIES } from "@/components/homepage/home/home-content";

/**
 * "Trusted by experts at": a pill label on a faded rule, over a row of logos
 * that scrolls on a loop.
 *
 * The loop is CSS (`.ss-home-marquee` in `home.css`): the list renders twice
 * and the track slides by half its width, so the seam never shows. Every logo
 * and its `alt` stays in the server-rendered HTML; the second copy is hidden
 * from assistive technology so the names are read once.
 *
 * Marks are desaturated for cohesion and inverted so dark artwork shows on the
 * dark ground. Logos that are already light opt out (see `home-content`).
 */

const FADED_RULE = "h-px bg-linear-to-r from-transparent via-border to-transparent";

function LogoList({ hidden = false }: { hidden?: boolean }) {
	return (
		<ul
			aria-hidden={hidden || undefined}
			className="flex shrink-0 items-center gap-16 pr-16 md:gap-40 md:pr-40"
		>
			{COMPANIES.map((company) => (
				<li key={company.title} className="shrink-0">
					{/* biome-ignore lint/performance/noImgElement: fixed-size local logo marks; next/image adds a loader and layout machinery for no benefit here */}
					<img
						src={`/logos/${company.file}`}
						alt={hidden ? "" : company.title}
						title={company.title}
						width={130}
						height={40}
						loading="lazy"
						decoding="async"
						draggable={false}
						data-light={company.light === true ? "" : undefined}
						className="h-8 w-auto max-w-36 object-contain opacity-70 brightness-105 grayscale invert select-none data-light:invert-0"
					/>
				</li>
			))}
		</ul>
	);
}

export function HomeLogos() {
	// Labelled with a paragraph rather than a heading on purpose: the brief fixes
	// the H1 and the seven H2s that follow it, and an eighth heading here would
	// sit in the middle of that sequence.
	return (
		<section className="border-t border-border py-16" aria-labelledby="home-logos-label">
			<div className="relative flex justify-center px-6 md:px-10">
				<div aria-hidden="true" className={`absolute inset-x-0 top-1/2 ${FADED_RULE}`} />
				<p
					id="home-logos-label"
					className="relative rounded-full border border-border bg-secondary px-5 py-2 text-sm font-medium text-foreground md:text-base"
				>
					Trusted by experts at
				</p>
			</div>

			<div className="mt-10 overflow-hidden mask-[linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
				<div className="ss-home-marquee flex w-max">
					<LogoList />
					<LogoList hidden />
				</div>
			</div>

			<div aria-hidden="true" className={`mt-10 ${FADED_RULE}`} />
		</section>
	);
}
