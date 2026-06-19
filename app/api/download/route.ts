import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { stripe } from "@/lib/stripe";

export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get("jobId");
  const sessionId = req.nextUrl.searchParams.get("session_id");

  if (!jobId || !sessionId) {
    return NextResponse.json({ error: "Eksik parametreler." }, { status: 400 });
  }

  const db = supabaseAdmin();

  // Verify stripe session is paid
  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId);
    if (session.payment_status !== "paid") {
      return NextResponse.json({ error: "Ödeme tamamlanmamış." }, { status: 403 });
    }
    if (session.metadata?.jobId !== jobId) {
      return NextResponse.json({ error: "Geçersiz oturum." }, { status: 403 });
    }
  } catch {
    return NextResponse.json({ error: "Ödeme doğrulanamadı." }, { status: 403 });
  }

  const { data: job, error } = await db
    .from("jobs")
    .select("id, download_url, brand_story, prompt, paid, files_list")
    .eq("id", jobId)
    .single();

  if (error || !job) {
    return NextResponse.json({ error: "İş bulunamadı." }, { status: 404 });
  }

  if (!job.paid || !job.download_url) {
    return NextResponse.json(
      { error: "Dosyalar henüz hazır değil. Lütfen birkaç saniye bekle." },
      { status: 202 }
    );
  }

  return NextResponse.json({
    download_url: job.download_url,
    brand_story: job.brand_story,
    prompt: job.prompt,
    files: job.files_list || [],
  });
}
