"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Download, CheckCircle, ArrowRight } from "lucide-react";

interface DownloadData {
  download_url: string;
  brand_story: string;
  prompt: string;
  files: string[];
}

export default function SuccessPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [data, setData] = useState<DownloadData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id || !sessionId) {
      setError("Geçersiz oturum.");
      setLoading(false);
      return;
    }

    // Paket satın alımı ise session_id cookie'ye yaz (90 gün, sıfır sürtünme)
    fetch("/api/set-cookie", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {}); // sessiz hata — kritik değil

    // Finalize webhook async çalışır — max 30s, 3s aralıkla polling yap
    let attempts = 0;
    const MAX_ATTEMPTS = 10;

    const tryFetch = async () => {
      attempts++;
      try {
        const res = await fetch(`/api/download?jobId=${id}&session_id=${sessionId}`);

        if (res.status === 202) {
          // Henüz hazır değil — tekrar dene
          if (attempts < MAX_ATTEMPTS) {
            setTimeout(tryFetch, 3000);
          } else {
            setError("Dosyalar hazırlanırken zaman aşımı. Lütfen birkaç dakika bekleyip sayfayı yenile.");
            setLoading(false);
          }
          return;
        }

        if (!res.ok) {
          const d = await res.json();
          throw new Error(d.error || "İndirme bağlantısı alınamadı.");
        }

        setData(await res.json());
        setLoading(false);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Bir hata oluştu.");
        setLoading(false);
      }
    };

    tryFetch();
  }, [id, sessionId]);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-brand-gold/30 border-t-brand-gold rounded-full animate-spin mx-auto mb-4" />
          <p className="font-mono text-white/40 text-sm">
            Dosyalar hazırlanıyor…
          </p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <h2 className="font-display font-black text-2xl uppercase text-red-400 mb-4">
            Hata
          </h2>
          <p className="text-white/40 font-mono text-sm">{error}</p>
          <p className="mt-4 text-xs text-white/20 font-mono">
            Sorun devam ederse:{" "}
            <a
              href="mailto:hello@brandgen.app"
              className="underline text-brand-gold/60"
            >
              hello@brandgen.app
            </a>
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-xl text-center">
        {/* Success icon */}
        <div className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-brand-gold/10 border border-brand-gold/30 flex items-center justify-center">
          <CheckCircle size={36} className="text-brand-gold" />
        </div>

        <h1 className="font-display font-black text-4xl uppercase tracking-wide text-brand-offwhite mb-3">
          Markan hazır!
        </h1>
        <p className="text-white/40 font-mono text-sm mb-10">
          &ldquo;{data?.prompt}&rdquo;
        </p>

        {/* Download button */}
        <a
          href={data?.download_url}
          download
          className="inline-flex items-center gap-3 px-8 py-4 bg-brand-offwhite text-brand-black font-display font-black text-sm uppercase tracking-widest rounded-xl hover:bg-white transition-colors"
        >
          <Download size={18} />
          Brand Kitini İndir (.zip)
        </a>

        {/* Files included */}
        {data?.files && data.files.length > 0 && (
          <div className="mt-10 p-6 rounded-2xl border border-white/10 bg-white/3 text-left">
            <div className="text-xs font-mono text-white/30 uppercase tracking-widest mb-4">
              ZIP içeriği
            </div>
            <div className="grid grid-cols-2 gap-2">
              {data.files.map((f) => (
                <div
                  key={f}
                  className="flex items-center gap-2 text-sm font-mono text-white/40"
                >
                  <div className="w-1 h-1 rounded-full bg-brand-gold/40" />
                  {f}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Brand story */}
        {data?.brand_story && (
          <div className="mt-6 p-6 rounded-2xl border border-white/10 bg-white/3 text-left">
            <div className="text-xs font-mono text-brand-gold/60 uppercase tracking-widest mb-4">
              Brand Hikayesi
            </div>
            <p className="text-sm text-white/60 leading-relaxed font-body whitespace-pre-wrap">
              {data.brand_story}
            </p>
          </div>
        )}

        {/* Upsell */}
        <div className="mt-8 p-5 rounded-2xl border border-white/10 bg-white/3">
          <p className="text-sm text-white/50 font-body mb-4">
            Daha fazla üretim hakkı için paket al — süresi dolmaz.
          </p>
          <a
            href="/#pricing"
            className="inline-flex items-center gap-2 text-sm font-display font-bold uppercase tracking-wide text-brand-gold hover:text-brand-gold/80 transition-colors"
          >
            Paketleri Gör <ArrowRight size={14} />
          </a>
        </div>

        {/* New brand */}
        <a
          href="/"
          className="mt-6 inline-block text-sm font-mono text-white/20 hover:text-white/40 transition-colors underline"
        >
          Yeni marka oluştur
        </a>
      </div>
    </main>
  );
}
