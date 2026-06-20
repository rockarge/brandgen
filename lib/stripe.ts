import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2024-06-20",
});

// Tüm planlar inline price_data — Stripe'ta önceden ürün oluşturmak gerekmez.
// Agency abonelik (subscription mode) da inline tanımlı.
export const PRICES = {
  // Tek seferlik — job bazlı (üretim sonrası ödeme)
  solo: {
    amount: 999, // $9.99
    currency: "usd",
    name: "BrandGen Solo — 1 Üretim",
    description: "Watermarksız tam brand kit. PNG + SVG + PDF.",
  },
  // Tek seferlik paketler — üretim hakkı (credits sistemi gelecek sprint)
  starter_pack: {
    amount: 3900, // $39
    currency: "usd",
    name: "BrandGen Starter Pack — 5 Üretim",
    description: "5 üretim hakkı. Watermarksız ZIP (PNG + SVG + PDF).",
  },
  studio_pack: {
    amount: 9900, // $99
    currency: "usd",
    name: "BrandGen Studio Pack — 15 Üretim",
    description: "15 üretim hakkı. Gelişmiş AI çıktısı. E-posta desteği.",
  },
  pro_pack: {
    amount: 17900, // $179
    currency: "usd",
    name: "BrandGen Pro Pack — 30 Üretim",
    description: "30 üretim hakkı. Gelişmiş AI çıktısı. E-posta desteği.",
  },
  // Agency — abonelik (subscription mode, inline price_data)
  agency: {
    monthly: { amount: 8900, interval: "month" as const },  // $89/ay
    yearly:  { amount: 69900, interval: "year" as const },   // $699/yıl
    currency: "usd",
    name: "BrandGen Agency",
    description: "60 üretim/ay. Gelişmiş AI çıktısı. Öncelikli e-posta desteği.",
  },
} as const;

export type BillingInterval = "monthly" | "yearly";
export type PlanTier = "solo" | "starter_pack" | "studio_pack" | "pro_pack" | "agency";
