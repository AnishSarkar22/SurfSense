import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { listRemoteEmbedders } from "@/features/embedding/remote/api"
import { MODELS_QUERY_KEY } from "@/features/models/models-query"
import type { Connection } from "@/features/models/remote/connections/api"
import type { ConnectionModel } from "@/features/models/remote/models/api"
import { ServerModelsView } from "@/features/models/remote/models/server-models-view"

import type { ServerChoice } from "../kinds/step-models"

/** One server's embedding models, in the list every step shows. Use checks
 *  the model before the step holds it. */
export function EmbeddingServerModels({
  connection,
  choice,
  disabled,
  defaultOpen,
  onEdit,
}: {
  connection: Connection
  choice: ServerChoice
  disabled: boolean
  defaultOpen: boolean
  onEdit: () => void
}) {
  const [open, setOpen] = useState(defaultOpen)
  const models = useQuery({
    queryKey: [...MODELS_QUERY_KEY, "remote", "embedders", connection.id],
    queryFn: async ({ signal }): Promise<ConnectionModel[]> =>
      (await listRemoteEmbedders(connection.id, signal)).map((found) => ({
        connection_id: connection.id,
        connection_label: connection.label,
        name: found.name,
        types: [],
        capability_source: "declared",
        selectable_for: [],
        reads_images: false,
      })),
    enabled: open,
  })
  const current = choice.current(connection.id)

  return (
    <ServerModelsView
      connection={connection}
      kind="embedding"
      disabled={disabled}
      open={open}
      onOpenChange={setOpen}
      onEdit={onEdit}
      models={models}
      candidates={models.data ?? []}
      current={current}
      isInUse={(name) => current === name}
      onUse={(model) => choice.use(model)}
      using={choice.using}
      useError={choice.error}
    />
  )
}
