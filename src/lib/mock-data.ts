// Mock data for SnapInsight UI shell

export const mockProduct = {
  name: "Organic Greek Yogurt",
  confidence: "HIGH CONFIDENCE",
  image: "/images/yogurt-placeholder.jpg",
  quickTake: "A high-protein, low-sugar option suitable for most clean-eating routines. Fermentation process looks authentic with active cultures present. Excellent choice for a post-workout recovery snack.",
  ingredients: [
    { name: "Cultured Pasteurized Milk", status: "safe" as const },
    { name: "Cream", status: "safe" as const },
    { name: "Pectin", status: "safe" as const, tag: "Stabilizer" },
    { name: "Live Active Cultures", status: "safe" as const },
  ],
  allergens: {
    contains: ["Dairy"],
    warning: "Produced in a facility that also processes tree nuts. Cross-contamination risk is low but present.",
  },
  nutritionNotes: [
    {
      title: "Protein Dense",
      description: "15g per serving. High bioavailability ratio.",
      icon: "protein" as const,
    },
    {
      title: "Low Sugar",
      description: "Only 4g naturally occurring sugars. No added sweeteners.",
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
  { label: "Brand detected", position: { top: "25%", left: "50%" } },
  { label: "Ingredients", position: { top: "50%", left: "20%" } },
  { label: "Nutrition Facts", position: { top: "70%", left: "60%" } },
]

export const statusChips = [
  { label: "Private by default", icon: "lock" as const },
  { label: "Evidence-backed", icon: "check" as const },
  { label: "Confidence-aware", icon: "layers" as const },
]

export const navItems = [
  { label: "Scan", icon: "scan" as const, href: "/scan" },
  { label: "Insights", icon: "insights" as const, href: "/insights" },
  { label: "Compare", icon: "compare" as const, href: "/compare" },
  { label: "Activity", icon: "activity" as const, href: "/activity" },
]
