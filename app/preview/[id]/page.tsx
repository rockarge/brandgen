"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Download, Clock, Sparkles, Lock } from "lucide-react";

type JobStatus = "pending" | "processing" | "done" | "error";

interface BriefData {
  brand_name: string;
  tagline: string;
  brand_story_preview: string;
  brand_story: string;
  primary_color: string;
  secondary_color: string;
  accent_color?: string;
  font_display: string;
  font_body: string;
  font_meta?: string;
  mood_words?: string[];
  visual_language?: string;
  social_post_1_caption?: string;
  social_post_2_caption?: string;
}

interface JobData {
  id: string;
  status: JobStatus;
  prompt: string;
  preview_url?: string;
  brand_story_preview?: string;
  brief_data?: BriefData;
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

// Rengin açık mı koyu mu olduğunu hesapla
function isLight(hex: string): boolean {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55;
}

// Rengi hafifçe karartır/açar (ghost efekti)
function ghostHex(hex: string, amount = 20): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const light = isLight(hex);
  const shift = light ? -amount : amount;
  const clamp = (v: number) => Math.max(0, Math.min(255, v + shift));
  return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
}

// ── Brand Kit Preview Component ──────────────────────────────────────────────
function BrandKitPreview({ brief }: { brief: BriefData }) {
  const {
    brand_name,
    tagline,
    primary_color,
    secondary_color,
    accent_color,
    font_display,
    font_body,
    mood_words = [],
    social_post_1_caption = "",
    social_post_2_caption = "",
    brand_story_preview = "",
  } = brief;

  const primaryLight = isLight(primary_color);
  const textOnPrimary = primaryLight ? "#0A0A0A" : secondary_color;
  const ghostOnPrimary = ghostHex(primary_color, 25);
  const initials = brand_name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();
  const initial1 = brand_name[0]?.toUpperCase() || "B";
  const colors = [primary_color, secondary_color, accent_color].filter(Boolean) as string[];

  // Google Fonts URL
  const displayFont = font_display || "Big Shoulders Display";
  const bodyFont = font_body || "DM Sans";
  const encodedFonts = encodeURIComponent(`${displayFont}:wght@700;900`);
  const encodedBody = encodeURIComponent(`${bodyFont}:wght@400;600`);

  return (
    <div style={{ fontFamily: `'${bodyFont}', sans-serif`, position: "relative" }}>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=${encodedFonts}&family=${encodedBody}&display=swap');
        .brand-display { font-family: '${displayFont}', sans-serif; }
        .brand-body { font-family: '${bodyFont}', sans-serif; }
        .watermark-wrap { position: relative; overflow: hidden; }
        .watermark-wrap::after {
          content: 'BRANDGEN PREVIEW  •  BRANDGEN PREVIEW  •  BRANDGEN PREVIEW';
          position: absolute;
          top: 50%; left: 50%;
          transform: translate(-50%, -50%) rotate(-30deg);
          font-size: 13px;
          font-family: monospace;
          letter-spacing: 0.15em;
          color: rgba(255,255,255,0.13);
          white-space: nowrap;
          pointer-events: none;
          z-index: 10;
          text-shadow: none;
          width: 200%;
          text-align: center;
          line-height: 2.8;
          word-spacing: 2em;
        }
        .watermark-dark::after { color: rgba(0,0,0,0.1); }
      `}</style>

      {/* ── BLOK 1: Hero Logo ─────────────────────────────────────────────── */}
      <div
        className="watermark-wrap"
        style={{
          background: primary_color,
          padding: "0",
          minHeight: "260px",
          display: "flex",
          alignItems: "stretch",
          position: "relative",
          overflow: "hidden",
          borderRadius: "16px 16px 0 0",
        }}
      >
        {/* Ghost büyük harf — arka plan */}
        <div
          className="brand-display"
          style={{
            position: "absolute",
            top: "-30%",
            left: "-5%",
            fontSize: "clamp(180px, 38vw, 320px)",
            fontWeight: 900,
            color: ghostOnPrimary,
            lineHeight: 1,
            userSelect: "none",
            pointerEvents: "none",
            letterSpacing: "-0.05em",
          }}
        >
          {initial1}
        </div>

        {/* Sol: Logo blok */}
        <div style={{ flex: "1 1 60%", padding: "40px 40px 32px", position: "relative", zIndex: 2 }}>
          <div
            className="brand-display"
            style={{
              fontSize: "clamp(28px, 5vw, 52px)",
              fontWeight: 900,
              color: textOnPrimary,
              letterSpacing: "0.06em",
              marginBottom: "8px",
              lineHeight: 1,
            }}
          >
            {brand_name.toUpperCase()}
          </div>
          <div
            style={{
              width: "48px",
              height: "2px",
              background: textOnPrimary,
              opacity: 0.4,
              marginBottom: "12px",
            }}
          />
          <div
            className="brand-body"
            style={{
              fontSize: "11px",
              letterSpacing: "0.22em",
              color: textOnPrimary,
              opacity: 0.5,
              textTransform: "uppercase",
            }}
          >
            Brand Identity
          </div>

          {/* Slogan */}
          <div
            className="brand-display"
            style={{
              marginTop: "auto",
              paddingTop: "48px",
              fontSize: "clamp(18px, 2.8vw, 26px)",
              fontWeight: 700,
              color: textOnPrimary,
              opacity: 0.9,
              lineHeight: 1.2,
              maxWidth: "420px",
            }}
          >
            {tagline.toUpperCase()}
          </div>
        </div>

        {/* Sağ: Monogram ikon */}
        <div
          style={{
            width: "clamp(100px, 18%, 160px)",
            background: accent_color || secondary_color,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            position: "relative",
          }}
          className="watermark-wrap"
        >
          <span
            className="brand-display"
            style={{
              fontSize: "clamp(36px, 6vw, 64px)",
              fontWeight: 900,
              color: isLight(accent_color || secondary_color) ? "#0A0A0A" : primary_color,
              letterSpacing: "-0.02em",
            }}
          >
            {initials.slice(0, 2)}
          </span>
        </div>
      </div>

      {/* ── BLOK 2: Renk Paleti + Tipografi ─────────────────────────────── */}
      <div
        style={{
          background: "#111",
          padding: "24px 32px",
          display: "flex",
          alignItems: "center",
          gap: "32px",
          flexWrap: "wrap",
        }}
      >
        {/* Renkler */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {colors.map((c) => (
            <div key={c} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "8px",
                  background: c,
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              />
              <span style={{ fontSize: "9px", fontFamily: "monospace", color: "rgba(255,255,255,0.35)", letterSpacing: "0.05em" }}>
                {c.toUpperCase()}
              </span>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div style={{ width: "1px", height: "48px", background: "rgba(255,255,255,0.08)" }} />

        {/* Tipografi */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div
            className="brand-display"
            style={{ fontSize: "22px", fontWeight: 900, color: "rgba(255,255,255,0.9)", lineHeight: 1 }}
          >
            Aa Bb Cc
          </div>
          <div style={{ fontSize: "10px", fontFamily: "monospace", color: "rgba(255,255,255,0.3)", letterSpacing: "0.1em" }}>
            {displayFont} / {bodyFont}
          </div>
        </div>

        {/* Mood words */}
        {mood_words.length > 0 && (
          <>
            <div style={{ width: "1px", height: "48px", background: "rgba(255,255,255,0.08)" }} />
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {mood_words.slice(0, 4).map((w) => (
                <span
                  key={w}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "100px",
                    border: `1px solid ${primary_color}55`,
                    color: primary_color,
                    fontSize: "10px",
                    letterSpacing: "0.1em",
                    fontFamily: "monospace",
                    textTransform: "uppercase",
                  }}
                >
                  {w}
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── BLOK 3: Sosyal Medya + Kartvizit ────────────────────────────── */}
      <div style={{ display: "flex", gap: "0", minHeight: "220px" }}>

        {/* Sosyal medya post — 1:1 */}
        <div
          className={`watermark-wrap ${primaryLight ? "watermark-dark" : ""}`}
          style={{
            flex: "0 0 220px",
            background: primary_color,
            position: "relative",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
            padding: "20px",
          }}
        >
          {/* Ghost arka plan harfi */}
          <div
            className="brand-display"
            style={{
              position: "absolute",
              top: "-20%",
              left: "-10%",
              fontSize: "200px",
              fontWeight: 900,
              color: ghostOnPrimary,
              lineHeight: 1,
              userSelect: "none",
            }}
          >
            {initial1}
          </div>
          {/* Köşe detay */}
          <div style={{ position: "absolute", top: "16px", left: "16px", width: "24px", height: "24px", borderTop: `1px solid ${textOnPrimary}55`, borderLeft: `1px solid ${textOnPrimary}55` }} />
          {/* Post metni */}
          <div style={{ position: "relative", zIndex: 2 }}>
            <div className="brand-display" style={{ fontSize: "13px", fontWeight: 700, color: textOnPrimary, lineHeight: 1.3, marginBottom: "8px" }}>
              {(social_post_1_caption || tagline).toUpperCase()}
            </div>
            <div style={{ fontSize: "9px", letterSpacing: "0.15em", color: textOnPrimary, opacity: 0.4, fontFamily: "monospace" }}>
              {brand_name.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Kartvizit ön yüz */}
        <div
          className={`watermark-wrap ${primaryLight ? "watermark-dark" : ""}`}
          style={{
            flex: "1",
            background: primary_color,
            borderLeft: `1px solid ${ghostOnPrimary}`,
            position: "relative",
            overflow: "hidden",
            display: "flex",
            alignItems: "stretch",
          }}
        >
          {/* Ghost monogram */}
          <div
            className="brand-display"
            style={{
              position: "absolute",
              top: "-30%",
              left: "-8%",
              fontSize: "260px",
              fontWeight: 900,
              color: ghostOnPrimary,
              lineHeight: 1,
              userSelect: "none",
            }}
          >
            {initial1}
          </div>
          {/* Dikey çizgi */}
          <div style={{ width: "1px", background: `${textOnPrimary}15`, position: "absolute", left: "55%", top: "12%", bottom: "12%" }} />
          {/* Sağ içerik */}
          <div style={{ marginLeft: "60%", padding: "24px 20px 24px 16px", position: "relative", zIndex: 2, display: "flex", flexDirection: "column", justifyContent: "center", gap: "6px" }}>
            <div className="brand-display" style={{ fontSize: "16px", fontWeight: 900, color: textOnPrimary, letterSpacing: "0.04em", lineHeight: 1 }}>
              AD SOYAD
            </div>
            <div style={{ fontSize: "10px", color: textOnPrimary, opacity: 0.5, fontFamily: "monospace" }}>Kurucu</div>
            <div style={{ width: "100%", height: "1px", background: `${textOnPrimary}15`, margin: "4px 0" }} />
            <div style={{ fontSize: "9px", color: textOnPrimary, opacity: 0.4, fontFamily: "monospace" }}>
              hello@{brand_name.toLowerCase().replace(/\s/g, "")}.com
            </div>
            <div style={{ fontSize: "9px", color: textOnPrimary, opacity: 0.4, fontFamily: "monospace" }}>
              {brand_name.toLowerCase().replace(/\s/g, "")}.com
            </div>
          </div>
        </div>

        {/* Kartvizit arka yüz */}
        <div
          className={`watermark-wrap ${isLight(secondary_color) ? "watermark-dark" : ""}`}
          style={{
            flex: "0 0 180px",
            background: secondary_color,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Büyük monogram */}
          <div
            className="brand-display"
            style={{
              position: "absolute",
              fontSize: "180px",
              fontWeight: 900,
              color: isLight(secondary_color) ? "rgba(0,0,0,0.06)" : "rgba(255,255,255,0.06)",
              lineHeight: 1,
              userSelect: "none",
            }}
          >
            {initials}
          </div>
          {/* Tagline */}
          <div
            className="brand-display"
            style={{
              position: "relative",
              zIndex: 2,
              fontSize: "10px",
              fontWeight: 700,
              letterSpacing: "0.12em",
              textAlign: "center",
              color: isLight(secondary_color) ? "rgba(0,0,0,0.7)" : "rgba(255,255,255,0.7)",
              padding: "0 16px",
              lineHeight: 1.4,
            }}
          >
            {tagline.toUpperCase()}
          </div>
          {/* Köşe detayları */}
          <div style={{ position: "absolute", top: "12px", left: "12px", width: "16px", height: "16px", borderTop: `1px solid ${isLight(secondary_color) ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.2)"}`, borderLeft: `1px solid ${isLight(secondary_color) ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.2)"}` }} />
          <div style={{ position: "absolute", bottom: "12px", right: "12px", width: "16px", height: "16px", borderBottom: `1px solid ${isLight(secondary_color) ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.2)"}`, borderRight: `1px solid ${isLight(secondary_color) ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.2)"}` }} />
        </div>
      </div>

      {/* ── BLOK 4: Brand Story preview ──────────────────────────────────── */}
      {brand_story_preview && (
        <div
          style={{
            background: "#0d0d0b",
            padding: "24px 32px",
            borderRadius: "0 0 16px 16px",
            display: "flex",
            alignItems: "flex-start",
            gap: "20px",
          }}
        >
          <div
            style={{
              width: "3px",
              flexShrink: 0,
              height: "100%",
              minHeight: "48px",
              background: primary_color,
              borderRadius: "2px",
              marginTop: "2px",
            }}
          />
          <p className="brand-body" style={{ fontSize: "13px", color: "rgba(255,255,255,0.45)", lineHeight: 1.7, margin: 0 }}>
            {brand_story_preview}
          </p>
        </div>
      )}

      {/* Watermark overlay — tüm bölge */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 20,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-around",
          overflow: "hidden",
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              transform: `rotate(-25deg) translateX(${i % 2 === 0 ? "-10%" : "10%"})`,
              fontSize: "11px",
              fontFamily: "monospace",
              letterSpacing: "0.3em",
              color: "rgba(255,255,255,0.07)",
              whiteSpace: "nowrap",
              textAlign: "center",
            }}
          >
            BRANDGEN PREVIEW &nbsp;&nbsp;&nbsp; BRANDGEN PREVIEW &nbsp;&nbsp;&nbsp; BRANDGEN PREVIEW
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Ana Sayfa ────────────────────────────────────────────────────────────────
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
      if (status === "done" || status === "error") clearInterval(interval);
    }, 3000);
    return () => clearInterval(interval);
  }, [poll]);

  useEffect(() => {
    if (job?.status !== "done" && job?.status !== "error") {
      const t = setInterval(() => setMsgIndex((i) => (i + 1) % PROCESSING_MESSAGES.length), 2800);
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

  // Loading
  if (!job || job.status === "pending" || job.status === "processing") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-lg text-center">
          <div className="w-32 h-32 mx-auto mb-8 relative">
            <div className="absolute inset-0 rounded-2xl bg-white/5 shimmer" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Sparkles size={32} className="text-brand-gold/60 animate-pulse" />
            </div>
          </div>
          <h2 className="font-display font-black text-3xl uppercase tracking-wide text-brand-offwhite mb-3">Üretiliyor</h2>
          <p className="text-white/40 font-mono text-sm min-h-[1.5rem]">{PROCESSING_MESSAGES[msgIndex]}</p>
          <div className="mt-8 w-full h-px bg-white/10 overflow-hidden rounded-full">
            <div className="h-full bg-brand-gold/60 rounded-full animate-[shimmer_2s_linear_infinite] w-1/2" />
          </div>
          {job?.prompt && (
            <p className="mt-6 text-xs font-mono text-white/20 max-w-sm mx-auto">&ldquo;{job.prompt}&rdquo;</p>
          )}
        </div>
      </main>
    );
  }

  // Error
  if (job.status === "error") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="text-center">
          <h2 className="font-display font-black text-3xl uppercase text-red-400 mb-4">Bir hata oluştu</h2>
          <p className="text-white/40 font-mono text-sm mb-8">{job.error || "Üretim sırasında beklenmedik bir hata oluştu."}</p>
          <button onClick={() => router.push("/")} className="px-6 py-3 bg-brand-offwhite text-brand-black font-display font-bold uppercase tracking-widest text-sm rounded-xl hover:bg-white transition-colors">
            Tekrar Dene
          </button>
        </div>
      </main>
    );
  }

  // Done
  const brief = job.brief_data;

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
        <p className="text-xs font-mono text-white/30 mb-8">&ldquo;{job.prompt}&rdquo;</p>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Preview — 3/5 */}
          <div className="lg:col-span-3">
            {brief ? (
              <div className="rounded-2xl overflow-hidden border border-white/10 relative">
                <BrandKitPreview brief={brief} />
              </div>
            ) : job.preview_url ? (
              // Fallback: eski brief_data yoksa Pillow image göster
              <div className="watermark-container rounded-2xl overflow-hidden border border-white/10">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={job.preview_url} alt="Brand preview" className="w-full object-cover" />
              </div>
            ) : (
              <div className="aspect-[4/5] bg-white/5 shimmer rounded-2xl" />
            )}
            <p className="mt-3 text-center text-xs font-mono text-white/20 flex items-center justify-center gap-2">
              <Lock size={10} />
              Watermarksız tam kalite için indir
            </p>
          </div>

          {/* Paywall panel — 2/5 */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* Brand story */}
            {(brief?.brand_story_preview || job.brand_story_preview) && (
              <div className="p-5 rounded-2xl border border-white/10 bg-white/3">
                <div className="text-xs font-mono text-brand-gold/60 uppercase tracking-widest mb-3">Brand Hikayesi</div>
                <p className="text-sm text-white/60 leading-relaxed font-body">
                  {brief?.brand_story_preview || job.brand_story_preview}
                </p>
                <div className="mt-4 h-8 rounded bg-white/5 shimmer" />
                <div className="mt-2 h-8 rounded bg-white/5 shimmer opacity-60" />
                <p className="mt-3 text-xs font-mono text-white/20 flex items-center gap-1">
                  <Lock size={10} /> Devamı için indir
                </p>
              </div>
            )}

            {/* Kit içeriği */}
            <div className="p-5 rounded-2xl border border-white/10 bg-white/3">
              <div className="text-xs font-mono text-white/40 uppercase tracking-widest mb-4">Pakete dahil</div>
              {[
                "3 logo versiyonu (PNG + SVG)",
                "Kartvizit mockup",
                "2 sosyal medya post",
                "Brand hikayesi (tam metin)",
                "Brand kit PDF (9 sayfa)",
                "Renk & tipografi kılavuzu",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-gold/60 flex-shrink-0" />
                  <span className="text-sm font-body text-white/60">{item}</span>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="p-5 rounded-2xl border border-brand-gold/30 bg-brand-gold/5">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-display font-black text-4xl text-brand-offwhite">$4.99</span>
                <span className="text-white/30 font-mono text-xs">tek seferlik</span>
              </div>
              <p className="text-xs text-white/40 font-mono mb-5">Kahve fiyatına tam marka kiti.</p>
              <button
                onClick={handleBuy}
                disabled={checkoutLoading}
                className="w-full flex items-center justify-center gap-2 py-4 bg-brand-offwhite text-brand-black font-display font-black text-sm uppercase tracking-widest rounded-xl hover:bg-white transition-colors disabled:opacity-50"
              >
                {checkoutLoading ? (
                  <span className="w-4 h-4 border-2 border-brand-black/20 border-t-brand-black rounded-full animate-spin" />
                ) : (
                  <><Download size={16} /> İndir — $4.99</>
                )}
              </button>
              <p className="mt-3 text-center text-xs font-mono text-white/20">Stripe ile güvenli ödeme. Anında indirme.</p>
            </div>

            {/* Upsell */}
            <div className="p-4 rounded-xl border border-white/5 bg-white/2">
              <div className="text-xs font-mono text-white/20 mb-2">Daha fazla marka yapacaksan?</div>
              <div className="text-sm font-body text-white/40">
                <strong className="text-white/60">Starter $9/ay</strong> — 3 proje/ay, sınırsız revizyon, 1 yıl bulut saklama.
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
