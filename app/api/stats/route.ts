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

const FREE_QUOTA = 200;

export async function GET() {
  try {
    const db = supabaseAdmin();
    const [doneRes, freeRes] = await Promise.all([
      db.from("jobs").select("id", { count: "exact", head: true }).eq("status", "done"),
      db.from("jobs").select("id", { count: "exact", head: true }).eq("tier", "free").eq("status", "done"),
    ]);
    const res = NextResponse.json({
      generated: doneRes.count ?? 0,
      freeRemaining: Math.max(0, FREE_QUOTA - (freeRes.count ?? 0)),
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
