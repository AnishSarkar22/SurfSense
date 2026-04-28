"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { SearchSpace } from "../../types/layout.types";
import type { User } from "../../types/layout.types";
import { SidebarUserProfile } from "../sidebar/SidebarUserProfile";
import { SearchSpaceAvatar } from "./SearchSpaceAvatar";

interface IconRailProps {
	searchSpaces: SearchSpace[];
	activeSearchSpaceId: number | null;
	onSearchSpaceSelect: (id: number) => void;
	onSearchSpaceDelete?: (searchSpace: SearchSpace) => void;
	onSearchSpaceSettings?: (searchSpace: SearchSpace) => void;
	onAddSearchSpace: () => void;
	user: User;
	onUserSettings?: () => void;
	onLogout?: () => void;
	theme?: string;
	setTheme?: (theme: "light" | "dark" | "system") => void;
	className?: string;
}

export function IconRail({
	searchSpaces,
	activeSearchSpaceId,
	onSearchSpaceSelect,
	onSearchSpaceDelete,
	onSearchSpaceSettings,
	onAddSearchSpace,
	user,
	onUserSettings,
	onLogout,
	theme,
	setTheme,
	className,
}: IconRailProps) {
	return (
		<div className={cn("flex h-full w-14 min-h-0 flex-col items-center", className)}>
			<ScrollArea className="w-full min-h-0 flex-1">
				<div className="flex flex-col items-center gap-2 px-1.5 py-3">
					{searchSpaces.map((searchSpace) => (
						<SearchSpaceAvatar
							key={searchSpace.id}
							name={searchSpace.name}
							isActive={searchSpace.id === activeSearchSpaceId}
							isShared={searchSpace.memberCount > 1}
							isOwner={searchSpace.isOwner}
							onClick={() => onSearchSpaceSelect(searchSpace.id)}
							onDelete={onSearchSpaceDelete ? () => onSearchSpaceDelete(searchSpace) : undefined}
							onSettings={
								onSearchSpaceSettings ? () => onSearchSpaceSettings(searchSpace) : undefined
							}
							size="md"
						/>
					))}

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								onClick={onAddSearchSpace}
								className="h-10 w-10 rounded-lg border-2 border-dashed border-muted-foreground/30 hover:border-muted-foreground/50"
							>
								<Plus className="h-5 w-5 text-muted-foreground" />
								<span className="sr-only">Add search space</span>
							</Button>
						</TooltipTrigger>
						<TooltipContent side="right" sideOffset={8}>
							Add search space
						</TooltipContent>
					</Tooltip>
				</div>
			</ScrollArea>
			<SidebarUserProfile
				user={user}
				onUserSettings={onUserSettings}
				onLogout={onLogout}
				isCollapsed
				theme={theme}
				setTheme={setTheme}
			/>
		</div>
	);
}
