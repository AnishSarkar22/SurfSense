import { HOME_FAQ } from "@/components/homepage/home/home-content";
import { FAQJsonLd } from "@/components/seo/json-ld";
import { SiteFaqItem } from "@/components/site/site-faq-item";
import { siteText } from "@/components/site/site-text";
import { cn } from "@/lib/utils";

/**
 * FAQ block, one `SiteFaqItem` per question.
 *
 * Each question is a cell in the reference's ruled grid, so an open answer
 * pushes the rule below it down rather than overlapping anything.
 *
 * Emits `FAQPage` schema from the same array, so the structured data and the
 * visible answers can never drift apart.
 */
export function HomeQuestions() {
	return (
		<section className="border-t border-border">
			<div className="border-b border-border px-6 pt-10 pb-8 md:px-10 md:pt-40">
				<p className={siteText.eyebrow}>FAQ</p>
				<h2 className={cn(siteText.h2, "mt-2")}>Questions people ask</h2>
			</div>

			<div className="ss-home-grid">
				{HOME_FAQ.map((item) => (
					<SiteFaqItem key={item.question} question={item.question}>
						<p className={siteText.body}>{item.answer}</p>
					</SiteFaqItem>
				))}
			</div>

			<FAQJsonLd questions={HOME_FAQ} />
		</section>
	);
}
