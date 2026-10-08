import { CheckIcon, ChevronDownIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

// Local ones first: the built-in catalog's text models, then two hosted providers.
const MODELS = [
	{ name: "Qwen3", where: "local", selected: true },
	{ name: "Gemma 4", where: "local", selected: false },
	{ name: "OpenAI", where: "hosted", selected: false },
	{ name: "Anthropic", where: "hosted", selected: false },
];

/** The model as a setting: a picker open on local and hosted choices. */
export function ModelPreview() {
	return (
		<div className="flex w-full max-w-56 flex-col gap-1.5">
			<div className="flex items-center justify-between rounded-lg bg-card px-3 py-2 text-xs font-medium text-foreground shadow-sm ring-1 ring-black/5">
				Qwen3
				<ChevronDownIcon className="size-3.5 text-muted-foreground" />
			</div>
			<div className="flex flex-col rounded-lg bg-card p-1 shadow-sm ring-1 ring-black/5">
				{MODELS.map((model) => (
					<div
						key={model.name}
						className={cn(
							"flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
							model.selected && "bg-(--notice)/10"
						)}
					>
						<span className="flex-1 text-foreground">{model.name}</span>
						<span className="text-[10px] text-muted-foreground">{model.where}</span>
						<CheckIcon className={cn("size-3 text-(--notice)", !model.selected && "invisible")} />
					</div>
				))}
			</div>
		</div>
	);
}
