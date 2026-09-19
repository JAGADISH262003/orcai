import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORCAI Ecosystem — Dual-Sided Marketplace & Recruiting OS",
  description: "Connecting Employer Contracts with Verified Employment Seekers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col selection:bg-brand selection:text-white antialiased">
        {children}
      </body>
    </html>
  );
}