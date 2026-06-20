import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

// "Paketim var" modal'ından çağrılır: e-posta ile credits tablosunu sorgular,
// session_id bulunursa bg_session cookie'sini set eder.
export async function POST(req: NextRequest) {
  const { email } = await req.json();

  if (!email || typeof email !== "string" || !email.includes("@")) {
    return NextResponse.json({ error: "Geçerli bir e-posta girin." }, { status: 400 });
  }

  const db = supabaseAdmin();

  const { data, error } = await db
    .from("credits")
    .select("session_id, tier, balance")
    .eq("email", email.toLowerCase().trim())
    .gt("balance", 0)
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  if (error || !data) {
    return NextResponse.json(
      { error: "Bu e-postaya ait aktif paket bulunamadı." },
      { status: 404 }
    );
  }

  const res = NextResponse.json({
    ok:      true,
    tier:    data.tier,
    balance: data.balance,
  });

  // Cookie set et — artık bu cihazda da otomatik kullanılacak
  res.cookies.set("bg_session", data.session_id, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 90, // 90 gün
    path: "/",
  });

  return res;
}
