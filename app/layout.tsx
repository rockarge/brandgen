import type { Metadata } from "next";
import "./globals.css";
import { PageTracker } from "@/components/PageTracker";

export const metadata: Metadata = {
  title: "BrandGen — AI Marka Kimliği",
  description:
    "3 dakikada tam marka kimliği. Logo, renk, tipografi, sosyal medya. Ücretsiz dene.",
  openGraph: {
    title: "BrandGen",
    description: "AI ile 3 dakikada avant-garde marka kimliği.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body className="grain">
        <PageTracker />
        {children}
      </body>
    </html>
  );
}
