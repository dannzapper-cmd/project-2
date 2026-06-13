#!/usr/bin/env node
/**
 * SnapInsight evidence capture — production screenshots via Playwright.
 *
 * Safety: no secrets, access codes, tokens, or real user images.
 * Stops with a clear error if Gemini analysis fails (no fabricated UI).
 */

import { mkdir, copyFile, writeFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { chromium, type Browser, type Page } from "playwright"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..")

const DEFAULT_BASE_URL = "https://project-2-wine-seven.vercel.app"
const DEFAULT_BACKEND_HEALTH_URL =
  "https://snapinsight-backend-87dm.onrender.com/health"

const BASE_URL = (
  process.env.SNAPINSIGHT_EVIDENCE_BASE_URL ?? DEFAULT_BASE_URL
).replace(/\/$/, "")
const BACKEND_HEALTH_URL =
  process.env.SNAPINSIGHT_EVIDENCE_BACKEND_HEALTH_URL ??
  DEFAULT_BACKEND_HEALTH_URL

const MOBILE_DIR = path.join(ROOT, "docs/evidence/screenshots/mobile")
const DESKTOP_DIR = path.join(ROOT, "docs/evidence/screenshots/desktop")
const DEMO_ASSETS_DIR = path.join(ROOT, "docs/evidence/demo-assets")
const PREVIEW_DIR = path.join(ROOT, "docs/evidence/preview")

const MOBILE_VIEWPORT = { width: 390, height: 844 }
const DESKTOP_VIEWPORT = { width: 1440, height: 1000 }

const WARM_MAX_ATTEMPTS = 6
const WARM_DELAY_MS = 5_000
const ANALYSIS_TIMEOUT_MS = 180_000


interface DemoLabelSpec {
  filename: string
  productName: string
  brand: string
  flavor: string
  barcode: string
}

const DEMO_LABELS: DemoLabelSpec[] = [
  {
    filename: "demo-product-label.png",
    productName: "Harvest Grove Oat Crisps",
    brand: "Harvest Grove Co.",
    flavor: "Honey Almond",
    barcode: "012345678905",
  },
  {
    filename: "demo-product-label-b.png",
    productName: "Summit Valley Granola",
    brand: "Summit Valley Foods",
    flavor: "Maple Pecan",
    barcode: "098765432109",
  },
]

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function ensureDirs(): Promise<void> {
  await Promise.all([
    mkdir(MOBILE_DIR, { recursive: true }),
    mkdir(DESKTOP_DIR, { recursive: true }),
    mkdir(DEMO_ASSETS_DIR, { recursive: true }),
    mkdir(PREVIEW_DIR, { recursive: true }),
  ])
}

async function warmBackend(): Promise<void> {
  console.log(`Warming backend: ${BACKEND_HEALTH_URL}`)

  for (let attempt = 1; attempt <= WARM_MAX_ATTEMPTS; attempt += 1) {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30_000)
      const response = await fetch(BACKEND_HEALTH_URL, {
        signal: controller.signal,
      })
      clearTimeout(timeout)

      if (!response.ok) {
        throw new Error(`Health returned HTTP ${response.status}`)
      }

      const body = (await response.json()) as { analysis_mode?: string }
      console.log(
        `Backend warm (attempt ${attempt}/${WARM_MAX_ATTEMPTS}) · mode=${body.analysis_mode ?? "unknown"}`
      )
      return
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      console.warn(`Warm attempt ${attempt} failed: ${message}`)
      if (attempt === WARM_MAX_ATTEMPTS) {
        throw new Error(
          `Backend did not become healthy after ${WARM_MAX_ATTEMPTS} attempts. Last error: ${message}`
        )
      }
      await sleep(WARM_DELAY_MS)
    }
  }
}

function labelSvg(spec: DemoLabelSpec): string {
  const ingredients = [
    "Whole grain oats",
    "Almond pieces",
    "Honey",
    "Sunflower oil",
    "Sea salt",
    "Natural flavor",
  ].join(", ")

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #f4efe6; font-family: Georgia, serif; }
  .label {
    width: 720px; height: 960px; margin: 0 auto; background: #fffdf8;
    border: 3px solid #2f4f3f; padding: 28px; color: #1f2937;
  }
  .brand { font-size: 22px; letter-spacing: 0.08em; color: #355e4b; text-transform: uppercase; }
  .name { font-size: 42px; font-weight: 700; margin: 12px 0 6px; line-height: 1.1; }
  .flavor { font-size: 24px; color: #4b5563; margin-bottom: 18px; }
  .panel { border: 2px solid #d1d5db; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
  .panel h2 { margin: 0 0 8px; font-size: 18px; text-transform: uppercase; letter-spacing: 0.06em; }
  .nutrition { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 18px; font-size: 15px; }
  .ingredients { font-size: 14px; line-height: 1.45; }
  .barcode { margin-top: 18px; padding-top: 12px; border-top: 2px dashed #9ca3af; }
  .bars { display: flex; gap: 2px; align-items: flex-end; height: 72px; margin-top: 8px; }
  .bar { background: #111827; width: 3px; }
  .code { font-family: monospace; font-size: 16px; margin-top: 8px; letter-spacing: 0.12em; }
  .note { font-size: 12px; color: #6b7280; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="label">
    <div class="brand">${spec.brand}</div>
    <div class="name">${spec.productName}</div>
    <div class="flavor">${spec.flavor}</div>
    <div class="panel">
      <h2>Nutrition Facts</h2>
      <div class="nutrition">
        <div>Serving size 40g</div><div>Calories 180</div>
        <div>Total Fat 6g</div><div>Saturated Fat 1g</div>
        <div>Total Sugars 7g</div><div>Protein 5g</div>
        <div>Sodium 140mg</div><div>Fiber 4g</div>
      </div>
    </div>
    <div class="panel">
      <h2>Ingredients</h2>
      <p class="ingredients">${ingredients}</p>
    </div>
    <div class="barcode">
      <div class="bars">
        ${Array.from({ length: 48 }, (_, index) => {
          const height = 24 + ((index * 7) % 40)
          return `<div class="bar" style="height:${height}px;width:${index % 5 === 0 ? 5 : 3}px"></div>`
        }).join("")}
      </div>
      <div class="code">${spec.barcode}</div>
      <p class="note">Synthetic demo label for SnapInsight evidence capture only.</p>
    </div>
  </div>
</body>
</html>`
}

async function generateDemoLabels(browser: Browser): Promise<Record<string, string>> {
  const paths: Record<string, string> = {}
  const page = await browser.newPage({ viewport: { width: 760, height: 1000 } })

  for (const spec of DEMO_LABELS) {
    const outputPath = path.join(DEMO_ASSETS_DIR, spec.filename)
    await page.setContent(labelSvg(spec), { waitUntil: "load" })
    await page.locator(".label").screenshot({ path: outputPath })
    paths[spec.filename] = outputPath
    console.log(`Generated demo label: ${outputPath}`)
  }

  await page.close()
  return paths
}

async function screenshot(page: Page, filePath: string): Promise<void> {
  await page.screenshot({ path: filePath, fullPage: true })
  console.log(`Captured ${filePath}`)
}

async function waitForGeminiResult(page: Page): Promise<void> {
  const resultLocator = page
    .locator("section.glass-card")
    .filter({ hasText: "AI Analysis" })
    .first()
  const analysisErrorLocator = page
    .locator('[role="alert"]')
    .filter({ has: page.locator("span", { hasText: "Unavailable" }) })

  await page
    .getByRole("button", { name: "Analyzing..." })
    .waitFor({ state: "visible", timeout: 15_000 })
    .catch(() => undefined)

  const outcome = await Promise.race([
    resultLocator
      .waitFor({ state: "visible", timeout: ANALYSIS_TIMEOUT_MS })
      .then(() => "success" as const),
    analysisErrorLocator
      .first()
      .waitFor({ state: "visible", timeout: ANALYSIS_TIMEOUT_MS })
      .then(() => "error" as const),
  ]).catch(() => "timeout" as const)

  if (outcome === "error") {
    const message =
      (await analysisErrorLocator.first().textContent())?.trim() ??
      "Unknown analysis error"
    throw new Error(`Gemini analysis failed on production: ${message}`)
  }

  if (outcome === "timeout") {
    throw new Error(
      `Gemini analysis timed out after ${ANALYSIS_TIMEOUT_MS / 1000}s. Backend may still be cold or rate-limited.`
    )
  }

  const mockBadge = page.getByText("Mock (dev)", { exact: true })
  if (await mockBadge.isVisible().catch(() => false)) {
    throw new Error("Production returned mock analysis — expected Gemini real mode.")
  }
}

async function uploadProductImage(page: Page, imagePath: string): Promise<void> {
  await page
    .locator('input[type="file"][accept="image/*"]')
    .first()
    .setInputFiles(imagePath)
  await page
    .getByRole("button", { name: "Analyze image" })
    .waitFor({ state: "visible", timeout: 15_000 })
}

async function uploadAndAnalyze(
  page: Page,
  imagePath: string
): Promise<Record<string, unknown>> {
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/v1/analyze/image") && response.status() === 200,
    { timeout: ANALYSIS_TIMEOUT_MS }
  )

  await uploadProductImage(page, imagePath)
  await page.getByRole("button", { name: "Analyze image" }).click()
  const response = await responsePromise
  const analysis = (await response.json()) as Record<string, unknown>
  await waitForGeminiResult(page)
  return analysis
}

async function waitForProductionBannerReady(page: Page): Promise<void> {
  const readyBanner = page.getByText(
    /Gemini real analysis · Cost controlled · Live gated|Gemini mode · Grounded product intelligence/i
  )

  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const isReady = await readyBanner.isVisible().catch(() => false)
    if (isReady) return

    if (attempt < 4) {
      await warmBackend()
      await page.reload({ waitUntil: "domcontentloaded" })
      await sleep(2000)
    }
  }

  throw new Error("Production banner did not reach Gemini ready state")
}

async function verifyDedicatedRoutes(page: Page): Promise<void> {
  const routes = ["/insights", "/compare", "/activity"] as const
  const pageErrors: string[] = []

  page.on("pageerror", (error) => {
    pageErrors.push(error.message)
  })

  for (const route of routes) {
    pageErrors.length = 0
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded" })
    await sleep(1500)

    const bodyText = await page.locator("body").innerText()
    const crashed =
      bodyText.includes("Application error") ||
      bodyText.includes("client-side exception")

    if (crashed || pageErrors.length > 0) {
      const details = pageErrors.length > 0 ? pageErrors.join(" | ") : bodyText.slice(0, 200)
      throw new Error(`Dedicated route ${route} crashed: ${details}`)
    }
  }
}

async function waitForDedicatedRouteContent(page: Page, route: string): Promise<void> {
  if (route === "/insights") {
    await page
      .getByRole("heading", { name: /Latest product insights/i })
      .waitFor({ state: "visible", timeout: 15_000 })
    return
  }

  if (route === "/compare") {
    await page
      .getByRole("heading", { name: /Compare products/i })
      .waitFor({ state: "visible", timeout: 15_000 })
    await page
      .getByText(/Product A|Add products/i)
      .first()
      .waitFor({ state: "visible", timeout: 15_000 })
    return
  }

  if (route === "/activity") {
    await page
      .getByRole("heading", { name: "Activity" })
      .waitFor({ state: "visible", timeout: 15_000 })

    const refreshButton = page.getByRole("button", { name: /Refresh/i })
    const usageLimits = page.getByText("Usage limits", { exact: true })
    const backendStatus = page.getByText("Backend status", { exact: true })
    const unavailable = page.getByText(/Backend metrics are unavailable/i)

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const ready = await Promise.race([
        usageLimits.waitFor({ state: "visible", timeout: 20_000 }).then(() => "metrics"),
        unavailable.waitFor({ state: "visible", timeout: 20_000 }).then(() => "unavailable"),
        backendStatus.waitFor({ state: "visible", timeout: 20_000 }).then(() => "status"),
      ]).catch(() => null)

      if (ready) return

      if (attempt < 3 && (await refreshButton.isVisible().catch(() => false))) {
        await refreshButton.click()
        await sleep(2500)
      }
    }

    throw new Error("Activity route did not load metrics or fallback content in time")
  }
}

async function captureDedicatedRoute(
  page: Page,
  route: "/insights" | "/compare" | "/activity",
  filePath: string
): Promise<void> {
  if (route === "/activity") {
    await warmBackend()
  }

  await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded" })
  await waitForDedicatedRouteContent(page, route)
  await waitForProductionBannerReady(page)
  await sleep(800)
  await screenshot(page, filePath)
}

async function scrollToText(page: Page, text: string): Promise<void> {
  const locator = page.getByText(text, { exact: false }).first()
  await locator.scrollIntoViewIfNeeded()
  await sleep(400)
}

async function captureMobileFlow(
  browser: Browser,
  labelPaths: Record<string, string>
): Promise<void> {
  const context = await browser.newContext({
    viewport: MOBILE_VIEWPORT,
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  })
  const page = await context.newPage()

  await page.goto(`${BASE_URL}/scan`, { waitUntil: "domcontentloaded" })
  await sleep(1500)
  await waitForProductionBannerReady(page)
  await screenshot(page, path.join(MOBILE_DIR, "01-scan-empty-or-upload.png"))

  await uploadAndAnalyze(page, labelPaths["demo-product-label.png"])
  await sleep(1000)
  await waitForProductionBannerReady(page)
  await screenshot(page, path.join(MOBILE_DIR, "02-scan-gemini-result.png"))

  const graphToggle = page.getByRole("button", { name: /Evidence Graph/i })
  if (await graphToggle.isVisible().catch(() => false)) {
    await graphToggle.click()
    await Promise.race([
      page
        .locator(".evidence-graph-flow")
        .waitFor({ state: "visible", timeout: 90_000 }),
      page
        .getByText(/Evidence graph unavailable|Graph request failed/i)
        .waitFor({ state: "visible", timeout: 90_000 }),
      page
        .getByText("No graph nodes available")
        .waitFor({ state: "visible", timeout: 90_000 }),
    ])
    await scrollToText(page, "Evidence Graph")
    await sleep(1000)
    await screenshot(page, path.join(MOBILE_DIR, "06-graph-evidence-no-minimap.png"))
  } else {
    console.warn("Evidence Graph not visible on scan — skipping 06-graph-evidence-no-minimap.png")
  }

  await scrollToText(page, "Gemini Live Voice + Vision")
  await sleep(800)
  await waitForProductionBannerReady(page)
  await screenshot(page, path.join(MOBILE_DIR, "07-gemini-live-ready-access-gated.png"))

  const analysisB = await uploadAndAnalyze(page, labelPaths["demo-product-label-b.png"])
  void analysisB

  await verifyDedicatedRoutes(page)

  await captureDedicatedRoute(
    page,
    "/insights",
    path.join(MOBILE_DIR, "03-insights-latest-analysis.png")
  )
  await captureDedicatedRoute(
    page,
    "/compare",
    path.join(MOBILE_DIR, "04-compare-workflow.png")
  )
  await captureDedicatedRoute(
    page,
    "/activity",
    path.join(MOBILE_DIR, "05-activity-metrics-limits.png")
  )

  await context.close()
}

async function captureDesktopFlow(
  browser: Browser,
  labelPaths: Record<string, string>
): Promise<void> {
  const context = await browser.newContext({
    viewport: DESKTOP_VIEWPORT,
    deviceScaleFactor: 1,
  })
  const page = await context.newPage()

  await page.goto(`${BASE_URL}/scan`, { waitUntil: "domcontentloaded" })
  await sleep(1200)
  await waitForProductionBannerReady(page)
  await screenshot(page, path.join(DESKTOP_DIR, "01-home-or-scan-desktop.png"))

  const desktopAnalysisA = await uploadAndAnalyze(
    page,
    labelPaths["demo-product-label.png"]
  )
  await sleep(1000)
  await waitForProductionBannerReady(page)
  await screenshot(page, path.join(DESKTOP_DIR, "02-scan-result-desktop.png"))

  void desktopAnalysisA
  await uploadAndAnalyze(page, labelPaths["demo-product-label-b.png"])

  await verifyDedicatedRoutes(page)

  await captureDedicatedRoute(
    page,
    "/activity",
    path.join(DESKTOP_DIR, "03-activity-dashboard-desktop.png")
  )
  await captureDedicatedRoute(
    page,
    "/compare",
    path.join(DESKTOP_DIR, "04-compare-desktop.png")
  )
  await captureDedicatedRoute(
    page,
    "/insights",
    path.join(DESKTOP_DIR, "05-insights-desktop.png")
  )

  await context.close()
}

async function createPreviewThumbnail(): Promise<void> {
  const source = path.join(MOBILE_DIR, "02-scan-gemini-result.png")
  const dest = path.join(PREVIEW_DIR, "scan-result-preview.png")
  await copyFile(source, dest)
  console.log(`Created preview thumbnail: ${dest}`)
}

async function writeCaptureManifest(): Promise<void> {
  const manifestPath = path.join(ROOT, "docs/evidence/screenshots/README.md")
  const capturedAt = new Date().toISOString()

  const content = `# SnapInsight evidence screenshots

**Captured from:** \`${BASE_URL}\` (production unless overridden)  
**Capture command:** \`npm run evidence:screenshots\`  
**Last capture:** ${capturedAt}  
**Post-merge:** Captured after PR #30 storage-hook fix — dedicated \`/insights\`, \`/compare\`, and \`/activity\` routes verified before screenshots.

## Quality audit

- No secrets visible in committed screenshots
- No access code visible
- No auth tokens visible
- Synthetic demo labels only (generated by capture script)
- Real Gemini output when scan succeeds (script aborts on mock or analysis failure)
- Dedicated routes verified after PR #30 deploy
- Graph and Gemini Live captured from \`/scan\` (no separate routes)

## Privacy

- Synthetic demo product labels only — no real user images, brands, or copyrighted packaging.
- No API keys, access codes, auth tokens, or private env vars in screenshots.
- Analysis results are real Gemini output from the production backend when capture succeeds.

## Mobile (\`mobile/\`)

| File | Proves |
|------|--------|
| \`01-scan-empty-or-upload.png\` | Mobile-first scan entry, upload/camera UX, calm backend banner |
| \`02-scan-gemini-result.png\` | Real Gemini multimodal analysis on synthetic label |
| \`03-insights-latest-analysis.png\` | \`/insights\` route — latest analysis from local JSON persistence |
| \`04-compare-workflow.png\` | \`/compare\` route — compare workflow with saved analyses |
| \`05-activity-metrics-limits.png\` | \`/activity\` route — backend metrics, usage limits, local scan log |
| \`06-graph-evidence-no-minimap.png\` | Evidence graph on \`/scan\` without minimap/overview panel |
| \`07-gemini-live-ready-access-gated.png\` | Gemini Live ready state with access-code gate (no secrets shown) |

## Desktop (\`desktop/\`)

| File | Proves |
|------|--------|
| \`01-home-or-scan-desktop.png\` | Desktop scan layout |
| \`02-scan-result-desktop.png\` | Gemini analysis result at desktop width |
| \`03-activity-dashboard-desktop.png\` | \`/activity\` route — metrics and usage limits |
| \`04-compare-desktop.png\` | \`/compare\` route on desktop |
| \`05-insights-desktop.png\` | \`/insights\` route on desktop |

## Demo assets

Synthetic labels live in \`../demo-assets/\` and are generated by the capture script when run.
`

  await writeFile(manifestPath, content, "utf8")
}

async function main(): Promise<void> {
  console.log(`SnapInsight evidence capture`)
  console.log(`Frontend: ${BASE_URL}`)
  console.log(`Backend health: ${BACKEND_HEALTH_URL}`)

  await ensureDirs()
  await warmBackend()

  const browser = await chromium.launch({ headless: true })

  try {
    const labelPaths = await generateDemoLabels(browser)
    await captureMobileFlow(browser, labelPaths)
    await captureDesktopFlow(browser, labelPaths)
    await createPreviewThumbnail()
    await writeCaptureManifest()
    console.log("Evidence capture completed successfully.")
  } finally {
    await browser.close()
  }
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Evidence capture failed: ${message}`)
  process.exit(1)
})
