"use client";

import { useState } from "react";
import { Check, Zap, Loader2 } from "lucide-react";

type Billing = "monthly" | "yearly";

// Tek seferlik paket planları
const ONE_TIME_PLANS = [
  {
    id: "solo",
    name: "Solo",
    badge: null,
    price: 9.99,
    priceLabel: "tek seferlik",
    description: "Bir marka, hemen hazır.",
    features: [
      "1 marka üretimi",
      "Watermarksız ZIP",
      "PNG + SVG + PDF brand kit",
    ],
    cta: "Hemen Al",
    highlight: false,
    aiNote: null,
  },
  {
    id: "starter_pack",
    name: "Starter Pack",
    badge: null,
    price: 39,
    priceLabel: "5 üretim · tek seferlik",
    description: "Küçük portföy, büyük başlangıç.",
    features: [
      "5 üretim hakkı",
      "Watermarksız ZIP",
      "PNG + SVG + PDF brand kit",
    ],
    cta: "Paketi Al",
    highlight: false,
    aiNote: null,
  },
  {
    id: "studio_pack",
    name: "Studio Pack",
    badge: "En Çok Tercih",
    price: 99,
    priceLabel: "15 üretim · tek seferlik",
    description: "Freelancer'ın vazgeçilmezi.",
    features: [
      "15 üretim hakkı",
      "Watermarksız ZIP",
      "PNG + SVG + PDF brand kit",
      "Gelişmiş AI çıktısı",
      "E-posta desteği",
    ],
    cta: "Studio Paketi Al",
    highlight: true,
    aiNote: null,
  },
  {
    id: "pro_pack",
    name: "Pro Pack",
    badge: null,
    price: 179,
    priceLabel: "30 üretim · tek seferlik",
    description: "Yoğun üretim, düşük birim maliyet.",
    features: [
      "30 üretim hakkı",
      "Watermarksız ZIP",
      "PNG + SVG + PDF brand kit",
      "Gelişmiş AI çıktısı",
      "E-posta desteği",
    ],
    cta: "Pro Paketi Al",
    highlight: false,
    aiNote: null,
  },
];

// Agency abonelik planı
const AGENCY_PLAN = {
  id: "agency",
  name: "Agency",
  badge: null,
  monthly: 89,
  yearly: 699,
  description: "Sürekli üretim yapan ajans ve freelancerlar için.",
  features: [
    "60 üretim / ay",
    "Watermarksız ZIP",
    "PNG + SVG + PDF brand kit",
    "Gelişmiş AI çıktısı",
    "Öncelikli e-posta desteği",
  ],
  cta: "Agency'ye Geç",
};

// v3 — yeni fiyatlama politikası
export default function Pricing({ jobId }: { jobId?: string }) {
  const [billing, setBilling] = useState<Billing>("monthly");
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  async function handleCheckout(planId: string) {
    if (planId === "solo" && !jobId) {
      document.getElementById("try")?.scrollIntoView({ behavior: "smooth" });
      return;
    }

    setLoadingPlan(planId);
    try {
      const res = await fetch("/api/create-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier: planId, billing, jobId: jobId ?? null }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert(data.error ?? "Bir hata oluştu.");
      }
    } catch {
      alert("Bağlantı hatası. Tekrar dene.");
    } finally {
      setLoadingPlan(null);
    }
  }

  return (
    <section className="py-24 px-4" id="pricing">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-14">
          <h2 className="font-display font-black text-5xl uppercase tracking-wide text-brand-offwhite mb-4">
            Fiyatlandırma
          </h2>
          <p className="text-white/40 font-mono text-sm">
            Ücretsiz dene. Beğenince öde. Abonelik yok.
          </p>
        </div>

        {/* Tek seferlik paket kartları */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {ONE_TIME_PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-2xl border p-6 transition-all ${
                plan.highlight
                  ? "border-brand-gold/40 bg-brand-gold/5"
                  : "border-white/10 bg-white/3 hover:bg-white/5"
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="flex items-center gap-1 px-3 py-1 rounded-full bg-brand-gold text-brand-black text-xs font-mono font-bold">
                    <Zap size={10} />
                    {plan.badge}
                  </span>
                </div>
              )}

              <div className="mb-6">
                <div className="text-xs font-mono text-white/30 uppercase tracking-widest mb-2">
                  {plan.name}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="font-display font-black text-4xl text-brand-offwhite">
                    ${plan.price}
                  </span>
                </div>
                <div className="text-xs font-mono text-white/25 mt-1">
                  {plan.priceLabel}
                </div>
                <p className="text-xs text-white/30 font-mono mt-3">
                  {plan.description}
                </p>
              </div>

              <ul className="flex-1 space-y-2.5 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <Check
                      size={13}
                      className={`mt-0.5 flex-shrink-0 ${
                        plan.highlight ? "text-brand-gold" : "text-white/40"
                      }`}
                    />
                    <span className="text-xs font-mono text-white/50">{f}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleCheckout(plan.id)}
                disabled={loadingPlan === plan.id}
                className={`flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-display font-bold uppercase tracking-widest transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
                  plan.highlight
                    ? "bg-brand-offwhite text-brand-black hover:bg-white"
                    : "border border-white/15 text-white/60 hover:border-white/30 hover:text-white/80"
                }`}
              >
                {loadingPlan === plan.id && (
                  <Loader2 size={14} className="animate-spin" />
                )}
                {plan.cta}
              </button>
            </div>
          ))}
        </div>

        {/* Agency abonelik kartı — tam genişlik, farklı görünüm */}
        <div className="rounded-2xl border border-white/10 bg-white/3 hover:bg-white/5 transition-all p-6">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            {/* Sol: başlık + açıklama */}
            <div className="flex-1">
              <div className="text-xs font-mono text-white/30 uppercase tracking-widest mb-1">
                {AGENCY_PLAN.name}
              </div>
              <p className="text-sm text-white/40 font-mono">
                {AGENCY_PLAN.description}
              </p>
            </div>

            {/* Orta: özellikler */}
            <ul className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
              {AGENCY_PLAN.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check size={13} className="mt-0.5 flex-shrink-0 text-white/40" />
                  <span className="text-xs font-mono text-white/50">{f}</span>
                </li>
              ))}
            </ul>

            {/* Sağ: fiyat + toggle + buton */}
            <div className="flex flex-col items-center md:items-end gap-3 min-w-[180px]">
              {/* Billing toggle — sadece Agency'de */}
              <div className="inline-flex items-center gap-1 p-1 rounded-full border border-white/10 bg-white/5">
                <button
                  onClick={() => setBilling("monthly")}
                  className={`px-4 py-1.5 rounded-full text-xs font-mono transition-all ${
                    billing === "monthly"
                      ? "bg-white/10 text-brand-offwhite"
                      : "text-white/30 hover:text-white/50"
                  }`}
                >
                  Aylık
                </button>
                <button
                  onClick={() => setBilling("yearly")}
                  className={`px-4 py-1.5 rounded-full text-xs font-mono transition-all flex items-center gap-1.5 ${
                    billing === "yearly"
                      ? "bg-white/10 text-brand-offwhite"
                      : "text-white/30 hover:text-white/50"
                  }`}
                >
                  Yıllık
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-brand-gold/20 text-brand-gold font-mono">
                    -35%
                  </span>
                </button>
              </div>

              <div className="text-right">
                <span className="font-display font-black text-3xl text-brand-offwhite">
                  {billing === "yearly"
                    ? `$${AGENCY_PLAN.yearly}/yıl`
                    : `$${AGENCY_PLAN.monthly}/ay`}
                </span>
                {billing === "yearly" && (
                  <div className="text-xs font-mono text-brand-gold/70 mt-0.5">
                    ≈ $58/ay · 2 ay bedava
                  </div>
                )}
              </div>

              <button
                onClick={() => handleCheckout(AGENCY_PLAN.id)}
                disabled={loadingPlan === AGENCY_PLAN.id}
                className="flex items-center justify-center gap-2 w-full py-3 px-6 rounded-xl text-sm font-display font-bold uppercase tracking-widest border border-white/15 text-white/60 hover:border-white/30 hover:text-white/80 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loadingPlan === AGENCY_PLAN.id && (
                  <Loader2 size={14} className="animate-spin" />
                )}
                {AGENCY_PLAN.cta}
              </button>
            </div>
          </div>
        </div>

        {/* Footer note */}
        <p className="mt-8 text-center text-xs font-mono text-white/20">
          Tüm ödemeler Stripe ile güvenli. Paketler süresi dolmaz.
        </p>
      </div>
    </section>
  );
}
