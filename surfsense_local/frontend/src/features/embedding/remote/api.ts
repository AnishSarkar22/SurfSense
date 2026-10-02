import { requestJson } from "@/lib/api"

import type { EmbeddingIndex } from "../api"

type Identified = EmbeddingIndex["spec"]["identified"]

/** A model on a connected server that embeds, and how SurfSense knows. */
export type RemoteEmbedder = {
  name: string
  identified: Identified
  context: number | null
}

/** A model that passed its checks; `choice` is what Finish sends to lock it. */
export type RemoteCheck = {
  choice: string
  name: string
  identified: Identified
  dimension: number
}

export function listRemoteEmbedders(
  connectionId: number,
  signal?: AbortSignal
): Promise<RemoteEmbedder[]> {
  return requestJson<RemoteEmbedder[]>(
    `/embedding/remote/connections/${connectionId}/models`,
    { signal }
  )
}

export function checkRemoteEmbedder(
  connectionId: number,
  model: string
): Promise<RemoteCheck> {
  return requestJson<RemoteCheck>("/embedding/remote/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_id: connectionId, model }),
  })
}
