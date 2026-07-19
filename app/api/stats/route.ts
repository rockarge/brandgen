/**
 * /api/stats — Public sayaçlar (landing page)
 * Döner: { generated, freeRemaining }
 *   generated:     status='done' job sayısı (gerçek üretim sayısı)
 *   freeRemaining: 200 kotasından kalan ücretsiz üretim hakkı
 *
 * 20 Tem 2026 (Serhat direktifi): freeRemaining artık SADECE BAŞARILI (done)
 * free üretimleri düşer — hatalı/yarım kalan job'lar kotayı yemez. Önceden tüm
 * free job'lar sayılıyordu; landing "90 üretildi · 92 kaldı" gibi tutarsız
 * görünüyordu (200-90=110 beklenirken). Kural: kalan = kota - başarılı üretim.
 * 5 dk CDN cache — her sayfa yüklemesinde DB'ye gitmez.
 */
import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";
// 20 Tem 2026: Next Data Cache, supabase-js'in outbound fetch'ini URL bazında
// önbellekleyip iki sayacın FARKLI anlardan gelmesine yol açtı (canlıda 90/109
// tutarsızlığı — matematiksel olarak imkansız kombinasyon). Kapatıldı:
export const fetchCache = "force-no-store";

const FREE_QUOTA = 200;

export async function GET() {
  try {
    const db = supabaseAdmin();
    // TEK sorgu, TEK anlık görüntü — iki sayaç aynı sonuç kümesinden türetilir,
    // tutarsızlık sınıfı (cache/yarış) mimari olarak imkansız hale gelir.
    // NOT: PostgREST satır limiti (varsayılan 1000) — done sayısı 1000'i aşarsa
    // count-bazlı sorguya dönülmeli (o gün geldiğinde güzel bir gün olacak).
    const { data, error } = await db
      .from("jobs")
      .select("tier")
      .eq("status", "done")
      .limit(5000);
    if (error) throw error;
    const doneAll = data?.length ?? 0;
    const doneFree = (data ?? []).filter((r) => r.tier === "free").length;
    const res = NextResponse.json({
      generated: doneAll,
      freeRemaining: Math.max(0, FREE_QUOTA - doneFree),
    });
    res.headers.set(
      "Cache-Control",
      "public, s-maxage=300, stale-while-revalidate=600"
    );
    return res;
  } catch {
    // Sayaçlar kozmetik — hata durumunda sayfa kırılmasın
    return NextResponse.json({ generated: null, freeRemaining: null });
  }
}
