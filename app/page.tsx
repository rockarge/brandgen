"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Zap, Shield, Clock, X } from "lucide-react";
import Pricing from "@/components/Pricing";

const EXAMPLES = [
  "Windy Venture Capital için avant-garde B&W marka kimliği",
  "Sürdürülebilir moda markası için minimal logo ve brand hikayesi",
  "Berlin'deki bir müzik stüdyosu için deneysel tipografi odaklı kimlik",
  "İstanbul kökenli lüks kahve markası için sinematik brand kit",
];

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  // "Paketim var" modal state
  const [showPackModal, setShowPackModal] = useState(false);
  const [packEmail, setPackEmail] = useState("");
  const [packLoading, setPackLoading] = useState(false);
  const [packError, setPackError] = useState("");
  const [packSuccess, setPackSuccess] = useState<{ tier: string; balance: number } | null>(null);

  const handlePackLookup = async () => {
    if (!packEmail.includes("@")) {
      setPackError("Geçerli bir e-posta girin.");
      return;
    }
    setPackLoading(true);
    setPackError("");
    try {
      const res = await fetch("/api/lookup-credits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: packEmail }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Paket bulunamadı.");
      setPackSuccess({ tier: data.tier, balance: data.balance });
    } catch (e: unknown) {
      setPackError(e instanceof Error ? e.message : "Bir hata oluştu.");
    } finally {
      setPackLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim() || prompt.trim().length < 10) {
      setError("Biraz daha detay yaz — en az 10 karakter.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Bir hata oluştu.");
      }

      const { jobId } = await res.json();
      router.push(`/preview/${jobId}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bir hata oluştu.");
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleGenerate();
    }
  };

  return (
    <main className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-5 border-b border-white/5">
        <span className="font-display text-xl font-black tracking-widest text-brand-offwhite uppercase">
          Brand<span className="text-brand-gold">Gen</span>
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={() => { setShowPackModal(true); setPackSuccess(null); setPackError(""); setPackEmail(""); }}
            className="text-xs font-mono text-white/30 hover:text-brand-gold/70 transition-colors"
          >
            Paketim var
          </button>
          <span className="text-xs text-white/20 font-mono">
            by Windy Venture Capital
          </span>
        </div>
      </nav>

      {/* "Paketim var" Modal */}
      {showPackModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-[#0f0f0f] border border-white/10 rounded-2xl p-8 relative">
            <button
              onClick={() => setShowPackModal(false)}
              className="absolute top-4 right-4 text-white/30 hover:text-white/60 transition-colors"
            >
              <X size={16} />
            </button>

            {packSuccess ? (
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-brand-gold/10 border border-brand-gold/30 flex items-center justify-center">
                  <Zap size={20} className="text-brand-gold" />
                </div>
                <p className="font-display font-black text-brand-offwhite uppercase text-lg mb-1">
                  Paket Yüklendi
                </p>
                <p className="text-sm text-white/40 font-mono mb-6">
                  {packSuccess.balance} üretim hakkınız hazır.
                </p>
                <button
                  onClick={() => setShowPackModal(false)}
                  className="w-full py-3 bg-brand-offwhite text-brand-black rounded-xl font-display font-bold text-sm uppercase tracking-widest hover:bg-white transition-colors"
                >
                  Üretmeye Başla
                </button>
              </div>
            ) : (
              <>
                <p className="font-display font-black text-brand-offwhite uppercase text-lg mb-1">
                  Paketimi Yükle
                </p>
                <p className="text-xs text-white/30 font-mono mb-6">
                  Satın alırken kullandığın e-postayı gir.
                </p>
                <input
                  type="email"
                  value={packEmail}
                  onChange={(e) => setPackEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handlePackLookup()}
                  placeholder="email@domain.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-brand-offwhite placeholder-white/20 text-sm outline-none focus:border-brand-gold/40 transition-all font-mono mb-3"
                />
                {packError && (
                  <p className="text-xs text-red-400/80 font-mono mb-3">{packError}</p>
                )}
                <button
                  onClick={handlePackLookup}
                  disabled={packLoading}
                  className="w-full py-3 bg-brand-offwhite text-brand-black rounded-xl font-display font-bold text-sm uppercase tracking-widest hover:bg-white transition-colors disabled:opacity-40"
                >
                  {packLoading ? "Kontrol ediliyor…" : "Paketi Yükle"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-20">
        {/* Badge */}
        <div className="flex items-center gap-2 mb-8 px-4 py-2 rounded-full border border-brand-gold/30 bg-brand-gold/5">
          <Zap size={12} className="text-brand-gold" />
          <span className="text-xs font-mono text-brand-gold/80 tracking-widest uppercase">
            Beta — İlk 200 üretim ücretsiz
          </span>
        </div>

        {/* Headline */}
        <h1 className="font-display text-center font-black uppercase text-6xl sm:text-7xl md:text-8xl leading-none mb-6 text-brand-offwhite">
          Markanı
          <br />
          <span className="text-white/20">3 dakikada</span>
          <br />
          <span
            style={{
              WebkitTextStroke: "1px rgba(241,235,225,0.3)",
              color: "transparent",
            }}
          >
            yarat.
          </span>
        </h1>

        <p className="text-white/40 text-center text-lg max-w-md mb-16 leading-relaxed">
          Logo, renk paleti, tipografi, sosyal medya asset&apos;leri, brand
          hikayesi. Hepsi bir prompttan.
        </p>

        {/* Input */}
        <div className="w-full max-w-2xl">
          <div className="relative">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={EXAMPLES[0]}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-5 text-brand-offwhite placeholder-white/20 text-base resize-none outline-none focus:border-brand-gold/40 focus:bg-white/8 transition-all duration-300 font-body"
            />
            <div className="absolute bottom-4 right-4 flex items-center gap-3">
              <span className="text-xs font-mono text-white/20">⌘ Enter</span>
              <button
                onClick={handleGenerate}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-brand-offwhite text-brand-black rounded-xl font-display font-bold text-sm uppercase tracking-widest hover:bg-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 border-2 border-brand-black/30 border-t-brand-black rounded-full animate-spin" />
                    Üretiyor...
                  </span>
                ) : (
                  <>
                    Üret <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-400/80 font-mono">{error}</p>
          )}

          {/* Example chips */}
          <div className="mt-4 flex flex-wrap gap-2">
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                onClick={() => setPrompt(ex)}
                className="text-xs px-3 py-1.5 rounded-full border border-white/8 text-white/30 hover:border-white/20 hover:text-white/60 transition-all font-mono truncate max-w-xs"
              >
                {ex.length > 45 ? ex.slice(0, 45) + "…" : ex}
              </button>
            ))}
          </div>
        </div>

        {/* Social proof */}
        <div className="mt-16 flex items-center gap-8 text-center">
          <div>
            <div className="text-2xl font-display font-black text-brand-offwhite">
              1,247
            </div>
            <div className="text-xs font-mono text-white/30 mt-1">
              Marka üretildi
            </div>
          </div>
          <div className="w-px h-8 bg-white/10" />
          <div>
            <div className="text-2xl font-display font-black text-brand-offwhite">
              2.8dk
            </div>
            <div className="text-xs font-mono text-white/30 mt-1">
              Ortalama süre
            </div>
          </div>
          <div className="w-px h-8 bg-white/10" />
          <div>
            <div className="text-2xl font-display font-black text-brand-offwhite">
              $9.99
            </div>
            <div className="text-xs font-mono text-white/30 mt-1">
              Tek üretim indirme
            </div>
          </div>
        </div>
      </div>

      {/* Pricing */}
      <div className="border-t border-white/5">
        <Pricing />
      </div>

      {/* Features strip */}
      <div className="border-t border-white/5 px-6 py-8">
        <div className="max-w-4xl mx-auto grid grid-cols-3 gap-8">
          {[
            {
              icon: <Zap size={16} className="text-brand-gold" />,
              title: "Avant-garde estetik",
              desc: "Bureau Borsche, Patavatsız referans alınarak üretilir",
            },
            {
              icon: <Shield size={16} className="text-brand-gold" />,
              title: "Tam dosya paketi",
              desc: "PNG, SVG, PDF brand kit. Hepsi tek seferde.",
            },
            {
              icon: <Clock size={16} className="text-brand-gold" />,
              title: "48 saat saklama",
              desc: "Ücretsiz önizleme 48 saat erişilebilir.",
            },
          ].map((f, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="mt-0.5 p-2 rounded-lg bg-brand-gold/10 flex-shrink-0">
                {f.icon}
              </div>
              <div>
                <div className="text-sm font-display font-bold text-brand-offwhite uppercase tracking-wide">
                  {f.title}
                </div>
                <div className="text-xs text-white/30 mt-1 leading-relaxed font-mono">
                  {f.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
