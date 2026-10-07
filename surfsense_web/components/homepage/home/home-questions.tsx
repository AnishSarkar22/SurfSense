import { HomeBadge } from "@/components/homepage/home/home-badge";
import { HOME_FAQ } from "@/components/homepage/home/home-content";
import { sectionSpacing } from "@/components/homepage/home/home-section-spacing";
import { FAQJsonLd } from "@/components/seo/json-ld";
import { SiteFaqItem } from "@/components/site/site-faq-item";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * FAQ block, one `SiteFaqItem` per question.
 *
 * Headed like the features section (a centred badge and headline), with the
 * questions inside the page gutters. An open answer pushes the rule below it
 * down rather than overlapping anything.
 *
 * Emits `FAQPage` schema from the same array, so the structured data and the
 * visible answers can never drift apart.
 */
export function HomeQuestions() {
	return (
		<section className={cn("border-t border-border", sectionSpacing.foot)}>
			<div className={cn("px-6 md:px-10", sectionSpacing.head)}>
				<div className="text-center">
					<HomeBadge>FAQ</HomeBadge>
					<h2 className={cn(siteText.h2, "mt-4")}>Questions people ask</h2>
				</div>

				{/* Gutter to gutter like every section, rows flush to the gutters. */}
				<div className="ss-home-grid mt-10 border-t border-border lg:mt-14">
					{HOME_FAQ.map((item) => (
						<SiteFaqItem key={item.question} question={item.question} flush>
							<p className={siteText.body}>{item.answer}</p>
						</SiteFaqItem>
					))}
				</div>
			</div>

			<FAQJsonLd questions={HOME_FAQ} />
		</section>
	);
}
