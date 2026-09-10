import { useState, type ComponentType } from "react"
import {
  ArrowLeftIcon,
  BrowserIcon,
  Cards01Icon,
  ChartHistogramIcon,
  CheckIcon,
  DownloadIcon,
  File02Icon,
  FileIcon,
  FileTextIcon,
  HierarchyIcon,
  Image01Icon,
  Pdf01Icon,
  PodcastIcon,
  Presentation01Icon,
  Quiz01Icon,
  SparklesIcon,
  Trash2Icon,
  Xls01Icon,
} from "@/components/ui/icons"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { WorkspaceDocument } from "@/features/sources/api"
import { cn } from "@/lib/utils"

import { fileUrl, type Artifact, type ArtifactDetail } from "./api"
import { useArtifacts } from "./use-artifacts"

const FORMAT_ICONS: Record<
  string,
  ComponentType<{ className?: string }>
> = {
  summary: FileTextIcon,
  docx: File02Icon,
  pptx: Presentation01Icon,
  xlsx: Xls01Icon,
  html: BrowserIcon,
  pdf: Pdf01Icon,
  mindmap: HierarchyIcon,
  flashcards: Cards01Icon,
  quiz: Quiz01Icon,
  podcast: PodcastIcon,
  image: Image01Icon,
  infographic: ChartHistogramIcon,
}

const statusVariant = {
  pending: "outline",
  processing: "secondary",
  ready: "secondary",
  failed: "destructive",
} as const

function Catalog({
  formats,
  onSelect,
}: {
  formats: ReturnType<typeof useArtifacts>["formats"]
  onSelect: (key: string) => void
}) {
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {formats.map((entry) => {
        const Icon = FORMAT_ICONS[entry.key] ?? FileIcon
        const tooltip = entry.available
          ? entry.description
          : (entry.unavailable_reason ??
            `Needs a ${entry.requires_role?.replace("_", " ")} model`)
        const card = (
          <button
            type="button"
            aria-label={entry.label}
            aria-disabled={entry.available ? undefined : "true"}
            onClick={() => {
              if (!entry.available) return
              onSelect(entry.key)
            }}
            className={cn(
              "flex min-w-0 cursor-pointer flex-col items-center gap-1 rounded-lg border bg-muted/40 px-1 py-2 text-center [&_svg]:size-4",
              entry.available
                ? "hover:bg-accent"
                : "cursor-not-allowed opacity-50"
            )}
          >
            <Icon />
            <span className="w-full truncate text-[11px] leading-4">
              {entry.label}
            </span>
          </button>
        )
        return (
          <Tooltip key={entry.key}>
            <TooltipTrigger asChild>{card}</TooltipTrigger>
            <TooltipContent side="top">{tooltip}</TooltipContent>
          </Tooltip>
        )
      })}
    </div>
  )
}

function Composer({
  format,
  formatLabel,
  documents,
  isCreating,
  onBack,
  onGenerate,
}: {
  format: string
  formatLabel: string
  documents: WorkspaceDocument[]
  isCreating: boolean
  onBack: () => void
  onGenerate: (job: {
    format: string
    document_ids: number[]
    prompt?: string
  }) => void
}) {
  const ready = documents.filter((document) => document.status === "ready")
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [prompt, setPrompt] = useState("")

  const toggle = (id: number) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })

  const canGenerate = selected.size > 0 && !isCreating

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Back to formats"
          onClick={onBack}
        >
          <ArrowLeftIcon />
        </Button>
        <h4 className="min-w-0 flex-1 truncate text-sm font-medium">
          {formatLabel}
        </h4>
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium text-muted-foreground">
          Sources ({selected.size} selected)
        </p>
        {ready.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Add and index a source first — only ready documents can be used.
          </p>
        ) : (
          <ScrollArea className="max-h-40">
            <div className="flex flex-col gap-1 pr-2">
              {ready.map((document) => {
                const on = selected.has(document.id)
                return (
                  <button
                    key={document.id}
                    type="button"
                    onClick={() => toggle(document.id)}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-2 rounded-md border px-2.5 py-2 text-left text-sm",
                      on ? "border-primary bg-primary/5" : "hover:bg-accent"
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-4 items-center justify-center rounded border",
                        on
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-muted-foreground/40"
                      )}
                    >
                      {on ? <CheckIcon className="size-3" /> : null}
                    </span>
                    <span className="min-w-0 flex-1 truncate">
                      {document.title}
                    </span>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium text-muted-foreground">
          Prompt (optional)
        </p>
        <Input
          value={prompt}
          placeholder="Steer the focus, e.g. emphasise the risks"
          onChange={(event) => setPrompt(event.target.value)}
        />
      </div>
      <Button
        className="w-full"
        disabled={!canGenerate}
        onClick={() =>
          onGenerate({
            format,
            document_ids: [...selected],
            prompt: prompt.trim() || undefined,
          })
        }
      >
        {isCreating ? <Spinner /> : <SparklesIcon data-icon="inline-start" />}
        Generate
      </Button>
    </div>
  )
}

function Library({
  artifacts,
  labelOf,
  onOpen,
  onDelete,
}: {
  artifacts: Artifact[]
  labelOf: (format: string) => string
  onOpen: (id: number) => void
  onDelete: (id: number) => void
}) {
  if (artifacts.length === 0) {
    return null
  }
  return (
    <div className="flex flex-col gap-1.5">
      {artifacts.map((artifact) => (
        <div
          key={artifact.id}
          className="flex items-start gap-2 rounded-md border p-2"
        >
          <div className="min-w-0 flex-1">
            <button
              type="button"
              disabled={artifact.status !== "ready"}
              onClick={() => onOpen(artifact.id)}
              className="w-full cursor-pointer text-left disabled:cursor-default"
            >
              <span className="block truncate text-sm font-medium">
                {artifact.title}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {labelOf(artifact.format)}
              </span>
            </button>
            {artifact.status === "failed" && artifact.error_message ? (
              <p className="mt-1 text-[11px] text-pretty text-destructive">
                {artifact.error_message}
              </p>
            ) : null}
          </div>
          <Badge
            variant={statusVariant[artifact.status]}
            className="mt-0.5 h-4 shrink-0 px-1.5 text-[10px]"
          >
            {artifact.status}
          </Badge>
          <Button
            variant="ghost"
            size="icon-sm"
            className="shrink-0"
            aria-label={`Delete ${artifact.title}`}
            onClick={() => onDelete(artifact.id)}
          >
            <Trash2Icon />
          </Button>
        </div>
      ))}
    </div>
  )
}

function Viewer({
  artifact,
  onBack,
}: {
  artifact: ArtifactDetail
  onBack: () => void
}) {
  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Back"
          onClick={onBack}
        >
          <ArrowLeftIcon />
        </Button>
        <h3 className="min-w-0 flex-1 truncate text-sm font-medium">
          {artifact.title}
        </h3>
        {artifact.files.map((file) => (
          <Button key={file.role} size="xs" variant="outline" asChild>
            <a href={fileUrl(artifact.id, file.role)} download>
              <DownloadIcon data-icon="inline-start" />
              {file.role}
            </a>
          </Button>
        ))}
      </div>
      <div className="overflow-y-auto rounded-md border">
        <Preview artifact={artifact} />
        <div className="prose prose-sm max-w-none p-3 text-sm leading-6 whitespace-pre-wrap">
          {artifact.content || "This artifact has no text body."}
        </div>
      </div>
    </div>
  )
}

function Preview({ artifact }: { artifact: ArtifactDetail }) {
  const primary = artifact.files.find((file) => file.role === "primary")
  if (!primary) return null

  const src = fileUrl(artifact.id, primary.role)
  if (primary.mime_type.startsWith("audio/")) {
    // biome-ignore lint/a11y/useMediaCaption: The generated transcript is rendered directly below the player.
    return <audio className="w-full p-3" controls src={src} />
  }
  if (primary.mime_type.startsWith("image/")) {
    return (
      <img className="mx-auto max-w-full p-3" alt={artifact.title} src={src} />
    )
  }
  return null
}

export function ArtifactsSection({
  workspaceId,
  documents,
}: {
  workspaceId: number
  documents: WorkspaceDocument[]
}) {
  const artifacts = useArtifacts(workspaceId)
  const [composing, setComposing] = useState<string | null>(null)
  const labelOf = (format: string) =>
    artifacts.formats.find((entry) => entry.key === format)?.label ?? format
  const composingLabel = composing ? labelOf(composing) : ""

  return (
    <section className="w-full min-w-0" aria-labelledby="artifacts-heading">
      <h3
        id="artifacts-heading"
        className="mb-2 px-1 text-xs font-medium text-muted-foreground"
      >
        Artifacts
      </h3>
      {artifacts.error ? (
        <Alert variant="destructive" className="mb-2">
          <AlertTitle>Artifact action failed</AlertTitle>
          <AlertDescription>{artifacts.error}</AlertDescription>
        </Alert>
      ) : null}
      {artifacts.selected ? (
        <Viewer
          artifact={artifacts.selected}
          onBack={artifacts.closeArtifact}
        />
      ) : artifacts.isLoading ? (
        <div className="flex flex-col gap-1.5">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <Library
            artifacts={artifacts.artifacts}
            labelOf={labelOf}
            onOpen={(id) => void artifacts.openArtifact(id)}
            onDelete={(id) => void artifacts.remove(id)}
          />
          {composing ? (
            <Composer
              format={composing}
              formatLabel={composingLabel}
              documents={documents}
              isCreating={artifacts.isCreating}
              onBack={() => setComposing(null)}
              onGenerate={(job) => {
                void artifacts.create(job).then((ok) => {
                  if (ok) setComposing(null)
                })
              }}
            />
          ) : (
            <Catalog
              formats={artifacts.formats}
              onSelect={setComposing}
            />
          )}
        </div>
      )}
    </section>
  )
}
