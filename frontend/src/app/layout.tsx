import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navigation";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ImpactLab | Limit Order Book Simulator & Market Impact Analyzer",
  description:
    "Simulate price-time priority order books for Indian equities (NSE-style), study slippage curves, price impact, and statutory trading charges.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-neutral-950 text-neutral-100 min-h-screen flex flex-col`}
      >
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
        <footer className="border-t border-neutral-900 bg-neutral-950/50 py-6 text-center text-xs text-neutral-400">
          <p>
            ImpactLab &bull; Price-Time Priority Limit Order Book Simulator &bull; NSE-Style Microstructure
          </p>
          <p className="mt-1 text-neutral-400">
            Simulated results using synthetic data. Not financial advice. Real execution costs will differ.
          </p>
        </footer>
      </body>
    </html>
  );
}
