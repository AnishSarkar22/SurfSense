import type { ReactElement } from "react"
import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, waitFor } from "@testing-library/react"

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "./alert-dialog"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./dialog"

const modals: [string, () => ReactElement][] = [
  [
    "dialog",
    () => (
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <DialogDescription>Dialog content</DialogDescription>
        </DialogContent>
      </Dialog>
    ),
  ],
  [
    "alert dialog",
    () => (
      <AlertDialog defaultOpen>
        <AlertDialogContent>
          <AlertDialogTitle>Alert dialog</AlertDialogTitle>
          <AlertDialogDescription>Alert dialog content</AlertDialogDescription>
        </AlertDialogContent>
      </AlertDialog>
    ),
  ],
]

afterEach(() => {
  cleanup()
  document.documentElement.classList.remove("electron-macos", "electron")
  document.body.replaceChildren()
})

describe.each(modals)("%s app-shell layout", (_name, renderModal) => {
  it("keeps Electron title-bar spacing off the scroll-locked body", async () => {
    document.documentElement.classList.add("electron-macos")
    const root = document.createElement("div")
    root.id = "root"
    root.style.paddingTop = "28px"
    document.body.append(root)

    render(renderModal(), { container: root })

    // Base UI locks the body by setting `overflow` inline; Radix used to mark
    // it with `data-scroll-locked`. Assert the lock itself, not the marker.
    await waitFor(() =>
      expect(getComputedStyle(document.body).overflowY).toBe("hidden")
    )
    // jsdom reports an unset padding as "0" and an explicit one as "0px", and
    // Base UI (unlike Radix) never writes padding onto the body at all.
    expect(parseFloat(getComputedStyle(document.body).paddingTop) || 0).toBe(0)
    expect(getComputedStyle(root).paddingTop).toBe("28px")
  })
})
