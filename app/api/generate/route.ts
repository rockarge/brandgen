import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { randomUUID } from "crypto";

const BACKEND_URL = process.env.BACKEND_URL || "https://brandgen-api.fly.dev";

export async function POST(req: NextRequest) {
  try {
    // tier: free (default Haiku) | solo | starter_pack | studio_pack | pro_pack | agency
    // Eğer cookie'de bg_session varsa tier credits tablosundan okunur
    const { prompt, tier: reqTier = "free" } = await req.json();

    if (!prompt || prompt.trim().length < 10) {
      return NextResponse.json(
        { error: "Prompt çok kısa — en az 10 karakter." },
        { status: 400 }
      );
    }

    const db = supabaseAdmin();

    // ── Credits kontrolü (paket kullanıcıları) ───────────────────────────
    let tier = reqTier;
    const sessionCookie = req.cookies.get("bg_session")?.value;
    let creditBalance = 0;

    if (sessionCookie) {
      const { data: credit } = await db
        .from("credits")
        .select("tier, balance")
        .eq("session_id", sessionCookie)
        .single();

      if (!credit) {
        // Geçersiz/silinmiş session — free olarak devam et
        tier = "free";
      } else if (credit.balance <= 0) {
        return NextResponse.json(
          { error: "Üretim haklarınız tükendi. Yeni paket alarak devam edebilirsiniz." },
          { status: 402 }
        );
      } else {
        tier = credit.tier;
        creditBalance = credit.balance;
      }
    }

    const jobId = randomUUID();
    const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();

    // Create job record in Supabase
    const { error: dbError } = await db.from("jobs").insert({
      id: jobId,
      prompt: prompt.trim(),
      status: "pending",
      expires_at: expiresAt,
    });

    if (dbError) {
      console.error("DB insert error:", dbError);
      return NextResponse.json({ error: "İş oluşturulamadı." }, { status: 500 });
    }

    // Paket kullanıcısı ise balance'ı 1 azalt (atomik — balance > 0 koruması)
    if (sessionCookie && creditBalance > 0) {
      await db
        .from("credits")
        .update({
          balance:    creditBalance - 1,
          updated_at: new Date().toISOString(),
        })
        .eq("session_id", sessionCookie)
        .gt("balance", 0); // race condition koruması
    }

    // Fire-and-forget: trigger backend generation
    fetch(`${BACKEND_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, prompt: prompt.trim(), tier }),
    }).catch((e) => console.error("Backend trigger failed:", e));

    return NextResponse.json({ jobId, tier });
  } catch (e) {
    console.error("Generate error:", e);
    return NextResponse.json({ error: "Sunucu hatası." }, { status: 500 });
  }
}
