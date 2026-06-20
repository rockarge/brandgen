import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

// Basit şifre koruması — ADMIN_SECRET env var ile karşılaştır
function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return false; // env ayarlanmamışsa erişim yok
  const auth = req.headers.get("x-admin-secret") ?? req.nextUrl.searchParams.get("secret");
  return auth === secret;
}

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = supabaseAdmin();

  // Jobs — son 200, yeniden eskiye
  const { data: jobs, error: jobsErr } = await db
    .from("jobs")
    .select("id, prompt, status, paid, tier, ai_model, stripe_session_id, created_at, expires_at, error")
    .order("created_at", { ascending: false })
    .limit(200);

  if (jobsErr) {
    return NextResponse.json({ error: jobsErr.message }, { status: 500 });
  }

  // Credits tablosu
  const { data: credits, error: creditsErr } = await db
    .from("credits")
    .select("session_id, email, tier, balance, updated_at")
    .order("updated_at", { ascending: false })
    .limit(200);

  // credits tablosu henüz oluşturulmamış olabilir — hata değil, boş döner
  const creditsData = creditsErr ? [] : (credits ?? []);

  // İstatistikler
  const totalJobs = jobs?.length ?? 0;
  const paidJobs = jobs?.filter((j) => j.paid).length ?? 0;
  const doneJobs = jobs?.filter((j) => j.status === "done").length ?? 0;
  const errorJobs = jobs?.filter((j) => j.status === "error").length ?? 0;
  const pendingJobs = jobs?.filter((j) => j.status === "pending" || j.status === "processing").length ?? 0;

  const tierCounts: Record<string, number> = {};
  for (const j of jobs ?? []) {
    tierCounts[j.tier] = (tierCounts[j.tier] ?? 0) + 1;
  }

  const totalCredits = creditsData.reduce((sum, c) => sum + (c.balance ?? 0), 0);

  return NextResponse.json({
    stats: {
      totalJobs,
      paidJobs,
      doneJobs,
      errorJobs,
      pendingJobs,
      tierCounts,
      totalCreditsPurchased: creditsData.length,
      totalCreditsRemaining: totalCredits,
    },
    jobs: jobs ?? [],
    credits: creditsData,
  });
}
