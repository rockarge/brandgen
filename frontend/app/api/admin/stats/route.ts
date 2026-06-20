import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return false;
  const auth = req.headers.get("x-admin-secret") ?? req.nextUrl.searchParams.get("secret");
  return auth === secret;
}

// Cihaz tespiti
function parseDevice(ua: string | null): "mobile" | "tablet" | "desktop" | "unknown" {
  if (!ua) return "unknown";
  if (/ipad|tablet|kindle/i.test(ua)) return "tablet";
  if (/mobile|iphone|android|blackberry|opera mini/i.test(ua)) return "mobile";
  return "desktop";
}

// Referrer temizleme
function parseReferrer(ref: string | null): string {
  if (!ref) return "Direkt";
  try {
    const host = new URL(ref).hostname.replace(/^www\./, "");
    const map: Record<string, string> = {
      "google.com": "Google", "bing.com": "Bing", "yahoo.com": "Yahoo",
      "facebook.com": "Facebook", "instagram.com": "Instagram",
      "twitter.com": "X/Twitter", "x.com": "X/Twitter",
      "linkedin.com": "LinkedIn", "reddit.com": "Reddit",
      "t.co": "X/Twitter", "tiktok.com": "TikTok",
      "brandgen.no1a.com": "Dahili",
    };
    return map[host] || host;
  } catch {
    return "Diğer";
  }
}

// Gelir hesabı (sent cinsinden)
const TIER_REVENUE: Record<string, number> = {
  starter_pack: 3900,
  studio_pack:  9900,
  pro_pack:    17900,
  agency:       8900,
};

export async function GET(req: NextRequest) {
  // v2.1 — cache bust
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = supabaseAdmin();

  // Jobs — son 200, tüm alanlar
  const { data: jobs, error: jobsErr } = await db
    .from("jobs")
    .select("id, prompt, status, paid, tier, ai_model, stripe_session_id, created_at, expires_at, error, preview_url, download_url, brand_story, brand_story_preview, user_agent, referrer")
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

  const creditsData = creditsErr ? [] : (credits ?? []);
  const jobsData = jobs ?? [];

  // ── İstatistikler ──────────────────────────────────────────────────────────

  const totalJobs   = jobsData.length;
  const paidJobs    = jobsData.filter(j => j.paid).length;
  const doneJobs    = jobsData.filter(j => j.status === "done").length;
  const errorJobs   = jobsData.filter(j => j.status === "error").length;
  const pendingJobs = jobsData.filter(j => j.status === "pending" || j.status === "processing").length;

  // Tier dağılımı
  const tierCounts: Record<string, number> = {};
  for (const j of jobsData) {
    tierCounts[j.tier] = (tierCounts[j.tier] ?? 0) + 1;
  }

  // Cihaz dağılımı
  const deviceCounts = { mobile: 0, tablet: 0, desktop: 0, unknown: 0 };
  for (const j of jobsData) {
    deviceCounts[parseDevice(j.user_agent)]++;
  }

  // Referrer dağılımı (top 8)
  const allRefs: Record<string, number> = {};
  for (const j of jobsData) {
    const src = parseReferrer(j.referrer);
    allRefs[src] = (allRefs[src] ?? 0) + 1;
  }
  const referrerCounts = Object.fromEntries(
    Object.entries(allRefs).sort((a, b) => b[1] - a[1]).slice(0, 8)
  );

  // Gelir hesabı
  const soloRevenue   = paidJobs * 999; // $9.99 × paid job sayısı
  const creditRevenue = creditsData.reduce((s, c) => s + (TIER_REVENUE[c.tier] ?? 0), 0);
  const totalRevenue  = soloRevenue + creditRevenue;

  const totalCreditsPurchased = creditsData.length;
  const totalCreditsRemaining = creditsData.reduce((s, c) => s + (c.balance ?? 0), 0);

  return NextResponse.json({
    stats: {
      totalJobs,
      paidJobs,
      doneJobs,
      errorJobs,
      pendingJobs,
      tierCounts,
      deviceCounts,
      referrerCounts,
      soloRevenue,
      creditRevenue,
      totalRevenue,
      totalCreditsPurchased,
      totalCreditsRemaining,
    },
    jobs: jobsData,
    credits: creditsData,
  });
}
