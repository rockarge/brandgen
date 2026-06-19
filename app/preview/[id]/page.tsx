"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Download, Clock, Sparkles, Lock } from "lucide-react";

type JobStatus = "pending" | "processing" | "done" | "error";

interface JobData {
  id: string;
  status: JobStatus;
  prompt: string;
  preview_url?: string;
  brand_story_preview?: string;
  error?: string;
  expires_at?: string;
}

const PROCESSING_MESSAGES = [
  "Marka karakteri analiz ediliyor…",
  "Tipografi sistemi oluşturuluyor…",
  "Logo kompozisyonları hazırlanıyor…",
  "Kartvizit tasarımı üretiliyor…",
  "Sosyal medya asset'leri hazırlanıyor…",
  "Brand hikayesi yazılıyor…",
  "Son rötuşlar yapılıyor…",
];

export default function PreviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobData | null>(null);
  const [msgIndex, setMsgIndex] = useState(0);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const poll = useCallback(async () => {
    try {
      const res = await fetch(`/api/job-status?id=${id}`);
      if (!res.ok) return;
      const data: JobData = await res.json();
      setJob(data);
      return data.status;
    } catch {
      return null;
    }
  }, [id]);

  useEffect(() => {
    poll();
    const interval = setInterval(async () => {
      const status = await poll();
      if (status === "done" || status === "error") {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [poll]);

  // Rotate processing messages
  useEffect(() => {
    if (job?.status !== "done" && job?.status !== "error") {
      const t = setInterval(() => {
        setMsgIndex((i) => (i + 1) % PROCESSING_MESSAGES.length);
      }, 2800);
      return () => clearInterval(t);
    }
  }, [job?.status]);

  const handleBuy = async () => {
    setCheckoutLoading(true);
    try {
      const res = await fetch("/api/create-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId: id, tier: "single" }),
      });
      const { url } = await res.json();
      if (url) window.location.href = url;
    } catch {
      setCheckoutLoading(false);
    }
  };

  // Loading state
  if (!job || job.status === "pending" || job.status === "processing") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-lg text-center">
          {/* Animated logo placeholder */}
          <div className="w-32 h-32 mx-auto mb-8 relative">
            <div className="absolute inset-0 rounded-2xl bg-white/5 shimmer" />
            <div className="absolute inset-4 rounded-xl bg-white/3" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Sparkles size={32} className="text-brand-gold/60 animate-pulse" />
            </div>
          </div>

          <h2 className="font-display font-black text-3xl uppercase tracking-wide text-brand-offwhite mb-3">
            Üretiliyor
          </h2>

          {/* Processing message */}
          <p className="text-white/40 font-mono text-sm min-h-[1.5rem] transition-all">
            {PROCESSING_MESSAGES[msgIndex]}
          </p>

          {/* Progress bar */}
          <div className="mt-8 w-full h-px bg-white/10 overflow-hidden rounded-full">
            <div className="h-full bg-brand-gold/60 rounded-full animate-[shimmer_2s_linear_infinite] w-1/2" />
          </div>

          {/* Prompt */}
          {job?.prompt && (
            <p className="mt-6 text-xs font-mono text-white/20 max-w-sm mx-auto">
              &ldquo;{job.prompt}&rdquo;
            </p>
          )}
        </div>
      </main>
    );
  }

  // Error state
  if (job.status === "error") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="text-center">
          <h2 className="font-display font-black text-3xl uppercase text-red-400 mb-4">
            Bir hata oluştu
          </h2>
          <p className="text-white/40 font-mono text-sm mb-8">
            {job.error || "Üretim sırasında beklenmedik bir hata oluştu."}
          </p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-3 bg-brand-offwhite text-brand-black font-display font-bold uppercase tracking-widest text-sm rounded-xl hover:bg-white transition-colors"
          >
            Tekrar Dene
          </button>
        </div>
      </main>
    );
  }

  // Done state — show preview with paywall
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-5 border-b border-white/5">
        <span className="font-display text-xl font-black tracking-widest text-brand-offwhite uppercase">
          Brand<span className="text-brand-gold">Gen</span>
        </span>
        {job.expires_at && (
          <div className="flex items-center gap-2 text-xs font-mono text-white/30">
            <Clock size={12} />
            <span>Önizleme 48 saat erişilebilir</span>
          </div>
        )}
      </nav>

      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Prompt recap */}
        <p className="text-xs font-mono text-white/30 mb-8">
          &ldquo;{job.prompt}&rdquo;
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Preview image — 3/5 */}
          <div className="lg:col-span-3">
            <div className="watermark-container rounded-2xl overflow-hidden border border-white/10">
              {job.preview_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={job.preview_url}
                  alt="Brand preview"
                  className="w-full object-cover"
                />
              ) : (
                <div className="aspect-[4/5] bg-white/5 shimmer" />
              )}
            </div>

            <p className="mt-3 text-center text-xs font-mono text-white/20 flex items-center justify-center gap-2">
              <Lock size={10} />
              Watermarksız tam kalite için indir
            </p>
          </div>

          {/* Paywall panel — 2/5 */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* Brand story preview */}
            {job.brand_story_preview && (
              <div className="p-5 rounded-2xl border border-white/10 bg-white/3">
                <div className="text-xs font-mono text-brand-gold/60 uppercase tracking-widest mb-3">
                  Brand Hikayesi
                </div>
                <p className="text-sm text-white/60 leading-relaxed font-body">
                  {job.brand_story_preview}
                </p>
                <div className="mt-4 h-8 rounded bg-white/5 shimmer" />
                <div className="mt-2 h-8 rounded bg-white/5 shimmer opacity-60" />
                <p className="mt-3 text-xs font-mono text-white/20 flex items-center gap-1">
                  <Lock size={10} /> Devamı için indir
                </p>
              </div>
            )}

            {/* What's included */}
            <div className="p-5 rounded-2xl border border-white/10 bg-white/3">
              <div className="text-xs font-mono text-white/40 uppercase tracking-widest mb-4">
                Pakete dahil
              </div>
              {[
                "3 logo versiyonu (PNG + SVG)",
                "Kartvizit mockup",
                "2 sosyal medya post",
                "Brand hikayesi (tam metin)",
                "Brand kit PDF (9 sayfa)",
                "Renk & tipografi kılavuzu",
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-gold/60 flex-shrink-0" />
                  <span className="text-sm font-body text-white/60">{item}</span>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="p-5 rounded-2xl border border-brand-gold/30 bg-brand-gold/5">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-display font-black text-4xl text-brand-offwhite">
                  $4.99
                </span>
                <span className="text-white/30 font-mono text-xs">
                  tek seferlik
                </span>
              </div>
              <p className="text-xs text-white/40 font-mono mb-5">
                Kahve fiyatına tam marka kiti.
              </p>

              <button
                onClick={handleBuy}
                disabled={checkoutLoading}
                className="w-full flex items-center justify-center gap-2 py-4 bg-brand-offwhite text-brand-black font-display font-black text-sm uppercase tracking-widest rounded-xl hover:bg-white transition-colors disabled:opacity-50"
              >
                {checkoutLoading ? (
                  <span className="w-4 h-4 border-2 border-brand-black/20 border-t-brand-black rounded-full animate-spin" />
                ) : (
                  <>
                    <Download size={16} />
                    İndir — $4.99
                  </>
                )}
              </button>

              <p className="mt-3 text-center text-xs font-mono text-white/20">
                Stripe ile güvenli ödeme. Anında indirme.
              </p>
            </div>

            {/* Upsell teaser */}
            <div className="p-4 rounded-xl border border-white/5 bg-white/2">
              <div className="text-xs font-mono text-white/20 mb-2">
                Daha fazla marka yapacaksan?
              </div>
              <div className="text-sm font-body text-white/40">
                <strong className="text-white/60">Starter $9/ay</strong> — 3
                proje/ay, sınırsız revizyon, 1 yıl bulut saklama.
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
