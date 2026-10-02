import { useState } from "react"

import type { ModelType } from "../../model-type"
import type { ModelSelection } from "../../selection/api"
import { useSelection } from "../../selection/use-selection"
import type { Connection } from "../connections/api"
import { ServerVoices } from "../voices/server-voices"
import type { ConnectionModel } from "./api"
import { ServerModelsView } from "./server-models-view"
import { TryModelDialog } from "./try-model-dialog"
import { useConnectionModels } from "./use-connection-models"

/** One server, and the models on it that can fill this section's slot. Use
 *  tries the model in a dialog, which then makes it the slot's model. */
export function ServerModels({
  connection,
  modelType,
  disabled,
  defaultOpen = false,
  onEdit,
  onSelected,
  onChatCleared,
}: {
  connection: Connection
  modelType: ModelType
  disabled: boolean
  /** Opens on its models when it first appears: a server just added. */
  defaultOpen?: boolean
  onEdit: () => void
  onSelected?: (selection: ModelSelection) => void
  onChatCleared?: () => void
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [trying, setTrying] = useState<{
    model: ConnectionModel
    unlisted: boolean
  } | null>(null)
  const [tryOpen, setTryOpen] = useState(false)
  const models = useConnectionModels(connection.id, open)
  const selection = useSelection(modelType)

  const current =
    selection.data?.connection_id === connection.id ? selection.data.name : null

  return (
    <ServerModelsView
      connection={connection}
      kind={modelType}
      disabled={disabled}
      open={open}
      onOpenChange={setOpen}
      onEdit={onEdit}
      onChatCleared={onChatCleared}
      models={models}
      candidates={(models.data ?? []).filter((model) =>
        model.selectable_for.includes(modelType)
      )}
      current={current}
      // Its voices belong to this server's model, so they are set up here.
      currentDetail={modelType === "audio_gen" ? <ServerVoices /> : undefined}
      isInUse={(name) => current === name}
      onUse={(model, unlisted) => {
        setTrying({ model, unlisted })
        setTryOpen(true)
      }}
    >
      {trying ? (
        <TryModelDialog
          key={trying.model.name}
          open={tryOpen}
          modelType={modelType}
          model={trying.model}
          unlisted={trying.unlisted}
          onOpenChange={setTryOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setTrying(null)
          }}
          onSelected={onSelected}
        />
      ) : null}
    </ServerModelsView>
  )
}
