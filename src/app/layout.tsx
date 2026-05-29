import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/layout/app-shell";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SnapInsight",
  description:
    "Visual companion for products — grounded insights with evidence and confidence (in development).",
  applicationName: "SnapInsight",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "SnapInsight",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#0f172a" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased bg-background`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col touch-manipulation pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)]">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
