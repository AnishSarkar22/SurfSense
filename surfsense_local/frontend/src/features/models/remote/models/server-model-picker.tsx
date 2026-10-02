import { Fragment, type ReactNode } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { CircleAlertIcon } from "@/components/ui/icons"
import { intl } from "@/i18n/intl"

import type { ModelType } from "../../model-type"
import type { ModelSelection } from "../../selection/api"
import type { Connection } from "../connections/api"
import { useConnections } from "../connections/use-connections"
import { ServerModels } from "./server-models"

function messageFrom(error: unknown) {
  return error instanceof Error
    ? error.message
    : intl.formatMessage({
        id: "models_server_picker_load_error",
        defaultMessage: "Could not load servers",
      })
}

/** A server's models for a section that is not a slot, in its own wrapper. */
export type ServerModelsRenderer = (
  connection: Connection,
  group: { defaultOpen: boolean; onEdit: () => void }
) => ReactNode

/**
 * One group per OpenAI-compatible server, each offering its models for one
 * slot. Servers are shared across slots; only the models listed are filtered.
 */
export function ServerModelPicker({
  modelType,
  renderModels,
  disabled = false,
  openServerId = null,
  onEdit,
  onSelected,
  onChatCleared,
}: {
  /** The slot each group offers models for; absent where `renderModels` is. */
  modelType?: ModelType
  /** Replaces the slot's own group, for a section that is not a slot. */
  renderModels?: ServerModelsRenderer
  disabled?: boolean
  /** A server just added, whose group opens on its models. */
  openServerId?: number | null
  onEdit: (connection: Connection) => void
  onSelected?: (selection: ModelSelection) => void
  onChatCleared?: () => void
}) {
  const connections = useConnections()

  if (connections.isError) {
    return (
      <Alert variant="destructive">
        <CircleAlertIcon />
        <AlertTitle>
          {intl.formatMessage({
            id: "models_server_picker_load_error_title",
            defaultMessage: "Could not load servers",
          })}
        </AlertTitle>
        <AlertDescription>{messageFrom(connections.error)}</AlertDescription>
      </Alert>
    )
  }

  return (connections.data ?? []).map((connection) => {
    if (renderModels) {
      return (
        <Fragment key={connection.id}>
          {renderModels(connection, {
            defaultOpen: connection.id === openServerId,
            onEdit: () => onEdit(connection),
          })}
        </Fragment>
      )
    }
    if (!modelType) return null
    return (
      <ServerModels
        key={connection.id}
        connection={connection}
        modelType={modelType}
        disabled={disabled}
        defaultOpen={connection.id === openServerId}
        onEdit={() => onEdit(connection)}
        onSelected={onSelected}
        onChatCleared={onChatCleared}
      />
    )
  })
}
