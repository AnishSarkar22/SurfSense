import { atomWithMutation } from "jotai-tanstack-query";
import { toast } from "sonner";
import type {
	CompleteLlmSetupOnboardingRequest,
	CompleteLlmSetupOnboardingResponse,
	CreateSearchSpaceRequest,
	CreateSearchSpaceResponse,
	DeleteSearchSpaceRequest,
	SearchSpace,
	UpdateSearchSpaceRequest,
} from "@/contracts/types/search-space.types";
import { searchSpacesApiService } from "@/lib/apis/search-spaces-api.service";
import { cacheKeys } from "@/lib/query-client/cache-keys";
import { queryClient } from "@/lib/query-client/client";
import { activeSearchSpaceIdAtom } from "./search-space-query.atoms";

function upsertSearchSpaceInList(searchSpace: SearchSpace) {
	queryClient.setQueriesData<SearchSpace[]>({ queryKey: cacheKeys.searchSpaces.all }, (current) => {
		if (!current) return [searchSpace];
		if (current.some((space) => space.id === searchSpace.id)) {
			return current.map((space) => (space.id === searchSpace.id ? searchSpace : space));
		}
		return [...current, searchSpace];
	});
}

function updateSearchSpaceCache(updatedSpace: CompleteLlmSetupOnboardingResponse) {
	queryClient.setQueriesData<SearchSpace[]>({ queryKey: cacheKeys.searchSpaces.all }, (current) =>
		current?.map((space) =>
			space.id === updatedSpace.id
				? { ...space, onboarding_state: updatedSpace.onboarding_state }
				: space
		)
	);
	queryClient.setQueryData(cacheKeys.searchSpaces.detail(String(updatedSpace.id)), updatedSpace);
}

export const createSearchSpaceMutationAtom = atomWithMutation(() => {
	return {
		mutationKey: ["create-search-space"],
		mutationFn: async (request: CreateSearchSpaceRequest) => {
			return searchSpacesApiService.createSearchSpace(request);
		},

		onSuccess: (createdSpace: CreateSearchSpaceResponse) => {
			toast.success("Search space created successfully");
			upsertSearchSpaceInList({
				...createdSpace,
				member_count: 1,
				is_owner: true,
			});
			queryClient.setQueryData(
				cacheKeys.searchSpaces.detail(String(createdSpace.id)),
				createdSpace
			);
			queryClient.invalidateQueries({
				queryKey: cacheKeys.searchSpaces.all,
			});
		},
	};
});

export const completeLlmSetupOnboardingMutationAtom = atomWithMutation(() => {
	return {
		mutationKey: ["complete-llm-setup-onboarding"],
		mutationFn: async (request: CompleteLlmSetupOnboardingRequest) => {
			return searchSpacesApiService.completeLlmSetupOnboarding(request);
		},

		onSuccess: (updatedSpace: CompleteLlmSetupOnboardingResponse) => {
			updateSearchSpaceCache(updatedSpace);
		},
		onError: (error: Error) => toast.error(error.message || "Failed to save onboarding progress"),
	};
});

export const updateSearchSpaceMutationAtom = atomWithMutation((get) => {
	const activeSearchSpaceId = get(activeSearchSpaceIdAtom);

	return {
		mutationKey: ["update-search-space", activeSearchSpaceId],
		enabled: !!activeSearchSpaceId,
		mutationFn: async (request: UpdateSearchSpaceRequest) => {
			return searchSpacesApiService.updateSearchSpace(request);
		},

		onSuccess: (_, request: UpdateSearchSpaceRequest) => {
			toast.success("Search space updated successfully");
			queryClient.invalidateQueries({
				queryKey: cacheKeys.searchSpaces.all,
			});
			if (request.id) {
				queryClient.invalidateQueries({
					queryKey: cacheKeys.searchSpaces.detail(String(request.id)),
				});
			}
		},
	};
});

export const deleteSearchSpaceMutationAtom = atomWithMutation((get) => {
	const activeSearchSpaceId = get(activeSearchSpaceIdAtom);

	return {
		mutationKey: ["delete-search-space", activeSearchSpaceId],
		enabled: !!activeSearchSpaceId,
		mutationFn: async (request: DeleteSearchSpaceRequest) => {
			return searchSpacesApiService.deleteSearchSpace(request);
		},

		onSuccess: (_, request: DeleteSearchSpaceRequest) => {
			toast.success("Search space deleted successfully");
			queryClient.invalidateQueries({
				queryKey: cacheKeys.searchSpaces.all,
			});
			if (request.id) {
				queryClient.removeQueries({
					queryKey: cacheKeys.searchSpaces.detail(String(request.id)),
				});
			}
		},
	};
});
