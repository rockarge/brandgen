"use client";

import { useState } from "react";
import { Check, Zap, Loader2 } from "lucide-react";

type Billing = "monthly" | "yearly";

const PLANS = [
  {
    id: "single",
    name: "Tek Seferlik",
    badge: null,
    monthly: 4.99,
    yearly: null,
    yearlyTotal: null,
    description: "Dene, beğen, al.",
    features: [
      "Tüm dosyalar watermarksız",
      "1 revizyon hakkı",
      "30 gün bulut saklama",
      "PNG + SVG + PDF brand kit",
    ],
    cta: "Hemen İndir",
    highlight: false,
  },
  {
    id: "starter",
    name: "Starter",
    badge: null,
    monthly: 9,
    yearly: 7,
    yearlyTotal: 79,
    description: "Düzenli üretim yapanlar için.",
    features: [
      "3 marka projesi / ay",
      "5 revizyon / proje",
      "Brand kit PDF (9 sayfa)",
      "1 yıl bulut saklama",
      "E-posta desteği",
    ],
    cta: "Starter'a Geç",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    badge: "En Popüler",
    monthly: 24,
    yearly: 19,
    yearlyTotal: 199,
    description: "Ajans kalitesi, AI hızı.",
    features: [
      "Sınırsız proje",
      "Sınırsız revizyon",
      "White-label PDF",
      "Öncelikli üretim kuyruğu",
      "TR + EN brand hikayesi",
      "Figma / Canva export",
    ],
    cta: "Pro'ya Geç",
    highlight: true,
  },
  {
    id: "agency",
    name: "Agency",
    badge: null,
    monthly: 79,
    yearly: 59,
    yearlyTotal: 599,
    description: "Ekip + müşteri üretimi.",
    features: [
      "Her şey + 5 ekip üyesi",
      "Müşteri adına üretim",
      "API erişimi",
      "Custom domain sunum",
      "Öncelikli destek",
    ],
    cta: "Agency'ye Geç",
    highlight: false,
  },
];

export default function Pricing({ jobId }: { jobId?: string }) {
  const [billing, setBilling] = useState<Billing>("monthly");
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  async function handleCheckout(planId: string) {
    if (planId === "single" && !jobId) {
      // Tek seferlik ödeme için önce marka üretimi gerekli
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
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-14">
          <h2 className="font-display font-black text-5xl uppercase tracking-wide text-brand-offwhite mb-4">
            Fiyatlandırma
          </h2>
          <p className="text-white/40 font-mono text-sm">
            Ücretsiz dene. Beğenince öde.
          </p>

          {/* Billing toggle */}
          <div className="inline-flex items-center gap-1 mt-8 p-1 rounded-full border border-white/10 bg-white/5">
            <button
              onClick={() => setBilling("monthly")}
              className={`px-5 py-2 rounded-full text-sm font-mono transition-all ${
                billing === "monthly"
                  ? "bg-white/10 text-brand-offwhite"
                  : "text-white/30 hover:text-white/50"
              }`}
            >
              Aylık
            </button>
            <button
              onClick={() => setBilling("yearly")}
              className={`px-5 py-2 rounded-full text-sm font-mono transition-all flex items-center gap-2 ${
                billing === "yearly"
                  ? "bg-white/10 text-brand-offwhite"
                  : "text-white/30 hover:text-white/50"
              }`}
            >
              Yıllık
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-gold/20 text-brand-gold font-mono">
                2 ay bedava
              </span>
            </button>
          </div>
        </div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {PLANS.map((plan) => {
            const price =
              billing === "yearly" && plan.yearly != null
                ? plan.yearly
                : plan.monthly;

            const isYearly = billing === "yearly" && plan.yearlyTotal != null;

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col rounded-2xl border p-6 transition-all ${
                  plan.highlight
                    ? "border-brand-gold/40 bg-brand-gold/5"
                    : "border-white/10 bg-white/3 hover:bg-white/5"
                }`}
              >
                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="flex items-center gap-1 px-3 py-1 rounded-full bg-brand-gold text-brand-black text-xs font-mono font-bold">
                      <Zap size={10} />
                      {plan.badge}
                    </span>
                  </div>
                )}

                {/* Plan name */}
                <div className="mb-6">
                  <div className="text-xs font-mono text-white/30 uppercase tracking-widest mb-2">
                    {plan.name}
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="font-display font-black text-4xl text-brand-offwhite">
                      {plan.yearly === null
                        ? `$${price}`
                        : `$${price}`}
                    </span>
                    <span className="text-white/30 font-mono text-xs">
                      {plan.yearly === null ? "" : isYearly ? "/ay" : "/ay"}
                    </span>
                  </div>
                  {isYearly && (
                    <div className="text-xs font-mono text-brand-gold/70 mt-1">
                      ${plan.yearlyTotal}/yıl · ${plan.monthly - plan.yearly!} tasarruf
                    </div>
                  )}
                  {plan.yearlyTotal === null && billing === "yearly" && (
                    <div className="text-xs font-mono text-white/20 mt-1">
                      tek seferlik
                    </div>
                  )}
                  <p className="text-xs text-white/30 font-mono mt-3">
                    {plan.description}
                  </p>
                </div>

                {/* Features */}
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

                {/* CTA */}
                <button
                  onClick={() => handleCheckout(plan.id)}
                  disabled={loadingPlan === plan.id}
                  className={`flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-display font-bold uppercase tracking-widest transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
                    plan.highlight
                      ? "bg-brand-offwhite text-brand-black hover:bg-white"
                      : "border border-white/15 text-white/60 hover:border-white/30 hover:text-white/80"
                  }`}
                >
                  {loadingPlan === plan.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : null}
                  {plan.cta}
                </button>
              </div>
            );
          })}
        </div>

        {/* Footer note */}
        <p className="mt-10 text-center text-xs font-mono text-white/20">
          Tüm planlar Stripe ile güvenli ödeme. İstediğin zaman iptal.
        </p>
      </div>
    </section>
  );
}
