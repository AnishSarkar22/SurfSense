import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { TooltipProvider } from "@/components/ui/tooltip"

import { ArtifactsSection } from "./artifacts-section"

const readyDocument = {
  id: 4,
  title: "Saturn facts",
  document_type: "NOTE" as const,
  status: "ready" as const,
  error_message: null,
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
}

const pendingArtifact = {
  id: 9,
  document_id: 20,
  format: "summary",
  generation: 1,
  title: "Summary",
  status: "pending" as const,
  error_message: null,
  created_at: "2026-09-06T00:00:00Z",
  updated_at: "2026-09-06T00:00:00Z",
}

beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  )
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("artifacts section", () => {
  it("submits a job after a format is chosen", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input)
        if (path === "/workspaces/1/artifacts/formats") {
          return Response.json([
            {
              key: "summary",
              label: "Summary",
              description: "Generate a summary based on your sources",
              requires_role: "generation",
              available: true,
              unavailable_reason: null,
            },
          ])
        }
        if (path === "/workspaces/1/artifacts/jobs" && init?.method === "POST") {
          return Response.json(pendingArtifact, { status: 201 })
        }
        if (path === "/workspaces/1/artifacts") {
          return Response.json([])
        }
        return Response.json({ detail: "not found" }, { status: 404 })
      }
    )
    vi.stubGlobal("fetch", fetchMock)
    const user = userEvent.setup()

    render(
      <TooltipProvider>
        <ArtifactsSection workspaceId={1} documents={[readyDocument]} />
      </TooltipProvider>
    )

    expect(screen.queryByText("Sources (0 selected)")).toBeNull()
    await user.click(await screen.findByRole("button", { name: "Summary" }))
    expect(screen.getByText("Sources (0 selected)")).toBeTruthy()
    await user.click(screen.getByText("Saturn facts"))
    await user.click(screen.getByRole("button", { name: /Generate/ }))

    const jobCall = await vi.waitFor(() =>
      fetchMock.mock.calls.find(
        ([path, init]) =>
          path === "/workspaces/1/artifacts/jobs" && init?.method === "POST"
      )
    )
    expect(JSON.parse(String(jobCall?.[1]?.body))).toEqual({
      format: "summary",
      document_ids: [4],
    })
    expect(await screen.findByText("pending")).toBeTruthy()
    expect(screen.queryByText("Sources (1 selected)")).toBeNull()
  })

  it("shows the stored reason on a failed artifact", async () => {
    const failedArtifact = {
      ...pendingArtifact,
      id: 11,
      title: "Flashcards",
      format: "flashcards",
      status: "failed" as const,
      error_message: "ConnectError: All connection attempts failed",
    }
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input)
        if (path === "/workspaces/1/artifacts/formats") {
          return Response.json([
            {
              key: "flashcards",
              label: "Flashcards",
              description: "Generate flashcards based on your sources",
              requires_role: "generation",
              available: true,
              unavailable_reason: null,
            },
          ])
        }
        if (path === "/workspaces/1/artifacts") {
          return Response.json([failedArtifact])
        }
        return Response.json({ detail: "not found" }, { status: 404 })
      })
    )

    render(
      <TooltipProvider>
        <ArtifactsSection workspaceId={1} documents={[readyDocument]} />
      </TooltipProvider>
    )

    expect(await screen.findByText("failed")).toBeTruthy()
    expect(
      screen.getByText("ConnectError: All connection attempts failed")
    ).toBeTruthy()
  })

  it("explains why an unavailable image format is disabled", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input)
        if (path === "/workspaces/1/artifacts/formats") {
          return Response.json([
            {
              key: "image",
              label: "Image",
              description: "Generate an image based on your sources",
              requires_role: "image_generation",
              available: false,
              unavailable_reason: "Image model required",
            },
          ])
        }
        if (path === "/workspaces/1/artifacts") return Response.json([])
        return Response.json({ detail: "not found" }, { status: 404 })
      })
    )
    const user = userEvent.setup()

    render(
      <TooltipProvider>
        <ArtifactsSection workspaceId={1} documents={[readyDocument]} />
      </TooltipProvider>
    )

    const image = await screen.findByRole("button", { name: "Image" })
    expect(image.getAttribute("aria-disabled")).toBe("true")
    await user.hover(image)
    expect(
      await screen.findByRole("tooltip", {
        name: "Image model required",
      })
    ).toBeTruthy()
    expect(screen.queryByText("Sources (0 selected)")).toBeNull()
  })
})
