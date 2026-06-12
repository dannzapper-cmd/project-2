import { describe, expect, it } from "vitest"

import {
  ANALYSIS_SERVICE_UNREACHABLE_MESSAGE,
  LIVE_CONFIG_UNREACHABLE_MESSAGE,
  getAnalysisServiceErrorMessage,
  isDeploymentFetchError,
} from "@/lib/deployment-errors"

describe("deployment-aware error messages", () => {
  it("maps browser fetch failures to actionable analysis copy", () => {
    expect(getAnalysisServiceErrorMessage(new TypeError("Failed to fetch"))).toBe(
      ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
    )
    expect(ANALYSIS_SERVICE_UNREACHABLE_MESSAGE).toContain("API URL")
    expect(ANALYSIS_SERVICE_UNREACHABLE_MESSAGE).toContain("CORS")
    expect(ANALYSIS_SERVICE_UNREACHABLE_MESSAGE).toContain("waking up")
  })

  it("maps missing frontend API URL to deployment copy", () => {
    const error = new Error(
      "NEXT_PUBLIC_SNAPINSIGHT_API_URL is not configured. Set it in your environment before building."
    )

    expect(isDeploymentFetchError(error)).toBe(true)
    expect(getAnalysisServiceErrorMessage(error)).toBe(
      ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
    )
  })

  it("preserves backend-provided analysis errors", () => {
    expect(getAnalysisServiceErrorMessage(new Error("Gemini API key is not configured."))).toBe(
      "Gemini API key is not configured."
    )
  })

  it("prefixes usage limit backend messages for public demo context", () => {
    expect(
      getAnalysisServiceErrorMessage(
        new Error("You have reached the analysis limit for this session.")
      )
    ).toContain("public demo")
    expect(
      getAnalysisServiceErrorMessage(
        new Error("This public demo has reached the analysis limit for this session.")
      )
    ).toBe("This public demo has reached the analysis limit for this session.")
  })

  it("distinguishes Live config fetch failure from Gemini Live disabled", () => {
    expect(LIVE_CONFIG_UNREACHABLE_MESSAGE).toContain("backend")
    expect(LIVE_CONFIG_UNREACHABLE_MESSAGE).toContain("API URL")
    expect(LIVE_CONFIG_UNREACHABLE_MESSAGE).toContain("CORS")
    expect(LIVE_CONFIG_UNREACHABLE_MESSAGE).toContain("not a Gemini Live failure")
  })
})
