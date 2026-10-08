import type { Metadata } from "next";
import { TrialForm } from "@/app/(home)/license/license-forms";
import { siteText } from "@/components/site/site-text";
import { getReleaseAssets } from "@/lib/release-assets";
import { cn } from "@/lib/utils";
import { AllReleasesLink, OSDownloadGrid } from "./download-panels";

/**
 * Rendered in the site design: the palette, ruled column, navigation and
 * footer all come from `app/(home)/layout.tsx`; the page is Tailwind plus the
 * shared `siteText` styles. Listed in `SITE_DESIGN_ROUTES` in
 * `components/site/site-shell.tsx`.
 */

export const metadata: Metadata = {
	title: "Download SurfSense | Windows, macOS, Linux",
	description:
		"Download the SurfSense desktop app for Windows, macOS and Linux. Self-hosted, runs entirely on your machine.",
	alternates: { canonical: "https://www.surfsense.com/downloads" },
};

export default async function DownloadsPage() {
	const assets = await getReleaseAssets();

	return (
		<>
			<section className="py-20 md:py-28">
				<div className="mx-auto max-w-2xl text-center">
					<h1 className={siteText.display}>Download SurfSense</h1>
					<p className={cn(siteText.lede, "mx-auto mt-6 max-w-xl")}>
						One installer, no account, no cloud.
					</p>
					<TrialForm label="Download" note="" />
				</div>
			</section>

			{assets.length > 0 ? (
				<section>
					<div className="pt-10 pb-8 md:pt-16">
						<p className={siteText.eyebrow}>Choose your platform</p>
						<h2 className={cn(siteText.h2, "mt-2")}>Windows, macOS and Linux</h2>
					</div>

					<OSDownloadGrid assets={assets} />
				</section>
			) : null}

			<section className="border-t border-border">
				<div className="py-10 text-center">
					<AllReleasesLink />
				</div>
			</section>
		</>
	);
}
