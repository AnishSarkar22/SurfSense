"use client";

import { useAtomValue, useSetAtom } from "jotai";
import { useParams, usePathname, useRouter } from "next/navigation";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { pendingUserImageDataUrlsAtom } from "@/atoms/chat/pending-user-images.atom";
import { myAccessAtom } from "@/atoms/members/members-query.atoms";
import {
	activeSearchSpaceIdAtom,
	searchSpacesAtom,
} from "@/atoms/search-spaces/search-space-query.atoms";
import { DocumentUploadDialogProvider } from "@/components/assistant-ui/document-upload-popup";
import { LayoutDataProvider } from "@/components/layout";
import { OnboardingTour } from "@/components/onboarding-tour";
import { useFolderSync } from "@/hooks/use-folder-sync";
import { useGlobalLoadingEffect } from "@/hooks/use-global-loading";
import { useElectronAPI } from "@/hooks/use-platform";
import { isSelfHosted } from "@/lib/env-config";
import { isLlmSetupOnboardingComplete } from "@/lib/onboarding";

export function DashboardClientLayout({
	children,
	searchSpaceId,
}: {
	children: React.ReactNode;
	searchSpaceId: string;
}) {
	const router = useRouter();
	const pathname = usePathname();
	const { search_space_id } = useParams();
	const activeSearchSpaceId = useAtomValue(activeSearchSpaceIdAtom);
	const setActiveSearchSpaceIdState = useSetAtom(activeSearchSpaceIdAtom);
	const setPendingUserImageUrls = useSetAtom(pendingUserImageDataUrlsAtom);

	const { isLoading: accessLoading } = useAtomValue(myAccessAtom);
	const {
		data: searchSpaces = [],
		isLoading: searchSpacesLoading,
		isSuccess: searchSpacesLoaded,
	} = useAtomValue(searchSpacesAtom);
	const [hasCheckedLayoutReadiness, setHasCheckedLayoutReadiness] = useState(false);

	const isOnboardingPage = pathname?.includes("/onboard");
	const isSearchSpaceReady = activeSearchSpaceId === searchSpaceId;
	const selfHosted = isSelfHosted();
	const numericSearchSpaceId = Number(searchSpaceId);
	const activeSearchSpace = useMemo(
		() => searchSpaces.find((space) => space.id === numericSearchSpaceId) ?? null,
		[searchSpaces, numericSearchSpaceId]
	);
	const llmSetupComplete = isLlmSetupOnboardingComplete(activeSearchSpace?.onboarding_state);
	const shouldRouteToOnboarding =
		selfHosted &&
		searchSpacesLoaded &&
		activeSearchSpace?.is_owner === true &&
		!llmSetupComplete &&
		!isOnboardingPage;
	const shouldRouteAwayFromOnboarding =
		selfHosted &&
		searchSpacesLoaded &&
		isOnboardingPage &&
		activeSearchSpace !== null &&
		(activeSearchSpace.is_owner !== true || llmSetupComplete);

	useEffect(() => {
		if (isSearchSpaceReady) return;
		setHasCheckedLayoutReadiness(false);
	}, [isSearchSpaceReady]);

	useEffect(() => {
		if (isOnboardingPage) {
			setHasCheckedLayoutReadiness(true);
			return;
		}

		if (isSearchSpaceReady && !accessLoading && !hasCheckedLayoutReadiness) {
			setHasCheckedLayoutReadiness(true);
		}
	}, [isSearchSpaceReady, accessLoading, isOnboardingPage, hasCheckedLayoutReadiness]);

	useEffect(() => {
		if (!shouldRouteToOnboarding) return;
		router.replace(`/dashboard/${searchSpaceId}/onboard`);
	}, [router, searchSpaceId, shouldRouteToOnboarding]);

	useEffect(() => {
		if (!shouldRouteAwayFromOnboarding) return;
		router.replace(`/dashboard/${searchSpaceId}/new-chat`);
	}, [router, searchSpaceId, shouldRouteAwayFromOnboarding]);

	const electronAPI = useElectronAPI();

	useEffect(() => {
		const htmlBackground = document.documentElement.style.backgroundColor;
		const bodyBackground = document.body.style.backgroundColor;

		document.documentElement.style.backgroundColor = "var(--panel)";
		document.body.style.backgroundColor = "var(--panel)";

		return () => {
			document.documentElement.style.backgroundColor = htmlBackground;
			document.body.style.backgroundColor = bodyBackground;
		};
	}, []);

	useEffect(() => {
		if (!electronAPI?.onChatScreenCapture) return;
		return electronAPI.onChatScreenCapture((dataUrl: string) => {
			if (typeof dataUrl !== "string" || !dataUrl.startsWith("data:image/")) return;
			setPendingUserImageUrls((prev) => [...prev, dataUrl]);
		});
	}, [electronAPI, setPendingUserImageUrls]);

	useEffect(() => {
		const activeSeacrhSpaceId =
			typeof search_space_id === "string"
				? search_space_id
				: Array.isArray(search_space_id) && search_space_id.length > 0
					? search_space_id[0]
					: "";
		if (!activeSeacrhSpaceId) return;
		setActiveSearchSpaceIdState(activeSeacrhSpaceId);

		// Sync to Electron store if stored value is null (first navigation)
		if (electronAPI?.getActiveSearchSpace && electronAPI.setActiveSearchSpace) {
			const setActiveSearchSpace = electronAPI.setActiveSearchSpace;
			electronAPI
				.getActiveSearchSpace()
				.then((stored: string | null) => {
					if (!stored) {
						setActiveSearchSpace(activeSeacrhSpaceId);
					}
				})
				.catch(() => {});
		}
	}, [search_space_id, setActiveSearchSpaceIdState, electronAPI]);

	// Determine if we should show loading
	const shouldShowLoading =
		(!hasCheckedLayoutReadiness && (!isSearchSpaceReady || accessLoading) && !isOnboardingPage) ||
		(selfHosted && searchSpacesLoading) ||
		shouldRouteToOnboarding ||
		shouldRouteAwayFromOnboarding;

	// Use global loading screen - spinner animation won't reset
	useGlobalLoadingEffect(shouldShowLoading);

	// Wire desktop app file watcher -> single-file re-index API
	useFolderSync();

	if (shouldShowLoading) {
		return null;
	}

	if (isOnboardingPage) {
		return <>{children}</>;
	}

	return (
		<DocumentUploadDialogProvider>
			<OnboardingTour />
			<LayoutDataProvider searchSpaceId={searchSpaceId}>{children}</LayoutDataProvider>
		</DocumentUploadDialogProvider>
	);
}
