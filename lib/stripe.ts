import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2024-06-20",
});

export const PRICES = {
  single: {
    amount: 499, // $4.99 in cents
    currency: "usd",
    name: "BrandGen — Tek Seferlik Brand Kit",
    description: "Watermarksız tam brand kit. Haiku AI ile üretildi.",
  },
  starter: {
    monthly: process.env.STRIPE_STARTER_MONTHLY_PRICE_ID!,
    yearly:  process.env.STRIPE_STARTER_YEARLY_PRICE_ID!,
    name: "BrandGen Starter",
    aiModel: "Sonnet",
  },
  pro: {
    monthly: process.env.STRIPE_PRO_MONTHLY_PRICE_ID!,
    yearly:  process.env.STRIPE_PRO_YEARLY_PRICE_ID!,
    name: "BrandGen Pro",
    aiModel: "Opus",         // VIP farklılaştırıcı
  },
  agency: {
    monthly: process.env.STRIPE_AGENCY_MONTHLY_PRICE_ID!,
    yearly:  process.env.STRIPE_AGENCY_YEARLY_PRICE_ID!,
    name: "BrandGen Agency",
    aiModel: "Opus",
  },
} as const;

export type BillingInterval = "monthly" | "yearly";
export type PlanTier = "single" | "starter" | "pro" | "agency";
