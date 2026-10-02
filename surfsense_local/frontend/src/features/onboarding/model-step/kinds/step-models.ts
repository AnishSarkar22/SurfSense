import type { ModelType } from "@/features/models/model-type"
import type { ConnectionModel } from "@/features/models/remote/models/api"

import type { SlotModels } from "./use-slot-models"

/**
 * A step's models and how it chooses one: the seam between a slot, whose Use
 * saves a selection, and the embedding step, whose Use only marks a choice
 * that Finish sends.
 */
export type StepModels = SlotModels & {
  /** Choose an installed model by the name it runs under. */
  use: (name: string) => void
  choosing: boolean
  chooseError: Error | null
  /** How a download from this step installs. */
  install: { select: boolean; modelType?: ModelType }
  /** What finishing onboarding from this step sends; null for a slot. */
  value: string | null
  /** A server's models, for a step that is not a slot; a slot uses its own. */
  serverChoice?: ServerChoice
}

/**
 * How a step that is not a slot chooses a server's model: held, never saved
 * as a selection. Use checks the model first, so it can be refused.
 */
export type ServerChoice = {
  /** The model chosen from this server, or null. */
  current: (connectionId: number) => string | null
  use: (model: ConnectionModel) => void
  /** The model being checked. */
  using: string | null
  /** Why the last model was refused. */
  error: string | null
}
