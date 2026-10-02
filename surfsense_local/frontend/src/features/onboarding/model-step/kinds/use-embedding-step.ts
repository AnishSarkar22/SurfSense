import { useState } from "react"

import { checkRemoteEmbedder } from "@/features/embedding/remote/api"
import { useLocalChatCatalog } from "@/features/models/local/chat/use-local-chat-catalog"
import { useConnections } from "@/features/models/remote/connections/use-connections"
import { intl } from "@/i18n/intl"

import { leadBuild } from "../local/local-choices"
import type { StepModels } from "./step-models"

/** A server's model that passed its checks. */
type RemotePick = {
  choice: string
  connectionId: number
  name: string
}

/**
 * The embedding step: the choice is held here and sent by Finish, never saved
 * as a selection. The model SurfSense ships is in use until another is used,
 * and again if that one is deleted or its server removed.
 */
export function useEmbeddingStep(): StepModels {
  const [chosen, setChosen] = useState<string | null>(null)
  const [remote, setRemote] = useState<RemotePick | null>(null)
  const [using, setUsing] = useState<string | null>(null)
  const [refusal, setRefusal] = useState<string | null>(null)
  const catalog = useLocalChatCatalog()
  const connections = useConnections()

  const server = remote
    ? (connections.data ?? []).find((each) => each.id === remote.connectionId)
    : undefined
  const remoteInUse = remote && server ? remote : null
  const embedders = (catalog.data?.rows ?? []).filter(
    (row) => row.engine === "onnxruntime"
  )
  const picked = embedders.find(
    (row) => row.id === chosen && leadBuild(row)?.installed_as != null
  )
  const current = remoteInUse
    ? undefined
    : (picked ?? embedders.find((row) => leadBuild(row)?.bundled === true))
  const build = current ? leadBuild(current) : null

  return {
    // Marked as a slot's model is, so the chosen row reads "In use"; a
    // Hugging Face pick says nobody measured it.
    rows: embedders.map((row) => ({
      ...row,
      description:
        row.description ??
        (row.origin === "downloaded"
          ? intl.formatMessage({
              id: "onboarding_embedding_step_untested_label",
              defaultMessage: "Not tested by SurfSense",
            })
          : null),
      builds: row.builds.map((each) => ({
        ...each,
        selected: row.id === current?.id,
      })),
    })),
    // Embedders are small; nothing to say about the machine.
    hardware: null,
    inUse: remoteInUse
      ? { name: remoteInUse.name, source: server?.label ?? "", where: "server" }
      : current && build?.installed_as
        ? { name: current.name, source: build.quantization, where: "local" }
        : null,
    isPending: catalog.isPending,
    error: catalog.error,
    use: (name) => {
      setRemote(null)
      setChosen(name)
    },
    choosing: using !== null,
    chooseError: null,
    // An embedder is never a selection, so a download selects nothing.
    install: { select: false },
    value: remoteInUse?.choice ?? picked?.id ?? null,
    serverChoice: {
      current: (connectionId) =>
        remoteInUse?.connectionId === connectionId ? remoteInUse.name : null,
      using,
      error: refusal,
      use: (model) => {
        setUsing(model.name)
        setRefusal(null)
        checkRemoteEmbedder(model.connection_id, model.name)
          .then((checked) =>
            setRemote({
              choice: checked.choice,
              connectionId: model.connection_id,
              name: checked.name,
            })
          )
          .catch((cause: unknown) =>
            setRefusal(
              cause instanceof Error
                ? cause.message
                : intl.formatMessage({
                    id: "onboarding_embedding_step_check_error",
                    defaultMessage: "Could not check this model",
                  })
            )
          )
          .finally(() => setUsing(null))
      },
    },
  }
}
