import type { ConnectionRead } from "@/contracts/types/model-connections.types";
import type { SearchSpace } from "@/contracts/types/search-space.types";

const COMPLETED_STATUS = "completed";

export function hasEnabledChatModel(connections: ConnectionRead[]): boolean {
	return connections.some(
		(connection) =>
			connection.enabled &&
			connection.models.some((model) => model.enabled && Boolean(model.supports_chat))
	);
}

export function isLlmSetupOnboardingComplete(
	onboardingState: SearchSpace["onboarding_state"] | null | undefined
): boolean {
	return onboardingState?.steps?.llm_setup?.status === COMPLETED_STATUS;
}

export function isLlmOnboardingComplete(
	chatModelId: number | null | undefined,
	globalConnections: ConnectionRead[],
	searchSpaceConnections: ConnectionRead[]
): boolean {
	const connections = [...globalConnections, ...searchSpaceConnections];
	const resolvedChatModelId = chatModelId ?? 0;

	if (resolvedChatModelId === 0) {
		return hasEnabledChatModel(connections);
	}

	return connections.some((connection) =>
		connection.models.some(
			(model) => model.id === resolvedChatModelId && model.enabled && Boolean(model.supports_chat)
		)
	);
}
