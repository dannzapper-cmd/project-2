// Mock data for SnapInsight screens

export const mockProduct = {
  name: "Organic Greek Yogurt",
  confidence: "HIGH CONFIDENCE",
  image: "/yogurt-placeholder.jpg",
  quickTake:
    "A high-protein, low-sugar option suitable for most clean-eating routines. Fermentation process looks authentic with active cultures present. Excellent choice for a post-workout recovery snack.",
  ingredients: [
    { name: "Cultured Pasteurized Milk", status: "safe" },
    { name: "Cream", status: "safe" },
    { name: "Pectin", status: "safe", tag: "Stabilizer" },
    { name: "Live Active Cultures", status: "safe" },
  ],
  allergens: {
    primary: "Contains Dairy",
    note: "Produced in a facility that also processes tree nuts. Cross-contamination risk is low but present.",
  },
  nutritionNotes: [
    {
      title: "Protein Dense",
      description: "15g per serving. High bioavailability ratio.",
      icon: "protein",
    },
    {
      title: "Low Sugar",
      description: "Only 4g naturally occurring sugars. No added sweeteners.",
      icon: "sugar",
    },
  ],
  betterQuestions: [
    "Show probiotic strains",
    "Compare with regular yogurt",
    "Sustainability score",
  ],
};

export const statusChips = [
  { label: "Private by default", icon: "lock" },
  { label: "Evidence-backed", icon: "check" },
  { label: "Confidence-aware", icon: "layers" },
];

export const detectionTags = [
  { label: "Brand detected", position: { top: "30%", left: "50%" } },
  { label: "Ingredients", position: { top: "55%", left: "25%" } },
  { label: "Nutrition Facts", position: { top: "70%", left: "55%" } },
];
