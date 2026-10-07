import { AIR_GAP_DIORAMA_SVG } from "@/components/homepage/home/home-air-gap/diorama/air-gap-diorama-svg";

/**
 * The machine as an isometric diorama: laptop at the centre, the index and an
 * an unplugged router (step 1), the model rack and key card (step 2), the outputs
 * (step 3). Inlined so `data-active` on the section can light each step's
 * `data-group`; edit the generator, not the generated SVG.
 */
export function AirGapDiorama() {
	return (
		<div
			aria-hidden="true"
			className="mx-auto w-full max-w-[34rem] select-none"
			// biome-ignore lint/security/noDangerouslySetInnerHtml: a build-time constant from our own generator, never user input.
			dangerouslySetInnerHTML={{ __html: AIR_GAP_DIORAMA_SVG }}
		/>
	);
}
