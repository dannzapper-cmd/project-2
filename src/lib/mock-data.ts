// Mock data for SnapInsight UI shell (preview only — not live analysis)

export const mockProduct = {
  name: "Organic Greek Yogurt",
  confidence: "Sample · High confidence preview",
  image: "/images/yogurt-placeholder.jpg",
  quickTake:
    "Sample mock analysis for UI preview. Informational context about a high-protein, low-sugar yogurt-style product—not medical advice. Always verify ingredients and allergens on the product label.",
  ingredients: [
    { name: "Cultured Pasteurized Milk", status: "safe" as const },
    { name: "Cream", status: "safe" as const },
    { name: "Pectin", status: "safe" as const, tag: "Stabilizer" },
    { name: "Live Active Cultures", status: "safe" as const },
  ],
  allergens: {
    contains: ["Dairy"],
    warning:
      "Sample allergen note for preview. Facility and cross-contamination details would come from cited sources when available.",
  },
  nutritionNotes: [
    {
      title: "Protein Dense",
      description: "Sample note: 15g per serving (mock values for layout).",
      icon: "protein" as const,
    },
    {
      title: "Low Sugar",
      description: "Sample note: naturally occurring sugars only (mock).",
      icon: "sugar" as const,
    },
  ],
  suggestedQuestions: [
    "Show probiotic strains",
    "Compare with regular yogurt",
    "Sustainability score",
  ],
}

export const mockDetectionTags = [
  { label: "Sample: Brand label", position: { top: "25%", left: "50%" } },
  { label: "Sample: Ingredients", position: { top: "50%", left: "20%" } },
  { label: "Sample: Nutrition facts", position: { top: "70%", left: "60%" } },
]

export const statusChips = [
  { label: "Privacy-first (planned)", icon: "lock" as const },
  { label: "Evidence-ready", icon: "check" as const },
  { label: "Confidence-aware", icon: "layers" as const },
]

export const navItems = [
  { label: "Scan", icon: "scan" as const, href: "/scan" },
  { label: "Insights", icon: "insights" as const, href: "/insights" },
  { label: "Compare", icon: "compare" as const, href: "/compare" },
  { label: "Activity", icon: "activity" as const, href: "/activity" },
]
