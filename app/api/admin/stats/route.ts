import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const _DEBUG_URL = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || 'NONE';

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return false;
  const auth = req.headers.get("x-admin-secret") ?? req.nextUrl.searchParams.get("secret");
  return auth === secret;
}

function parseDevice(ua: string | null): "mobile" | "tablet" | "desktop" | "unknown" {
  if (!ua) return "unknown";
  if (/ipad|tablet|kindle/i.test(ua)) return "tablet";
  if (/mobile|iphone|android|blackberry|opera mini/i.test(ua)) return "mobile";
  return "desktop";
}

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
    return "Di\u011fer";
  }
}

const TIER_REVENUE: Record<string, number> = {
  starter_pack: 3900, studio_pack: 9900, pro_pack: 17900, agency: 8900,
};

const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  "claude-haiku-4-5-20251001": { input: 0.80, output: 4.0 },
  "claude-haiku-3-5-20241022": { input: 0.80, output: 4.0 },
  "claude-3-haiku-20240307":   { input: 0.25, output: 1.25 },
  "claude-sonnet-4-5":         { input: 3.0,  output: 15.0 },
  "claude-3-5-sonnet-20241022":{ input: 3.0,  output: 15.0 },
  "claude-opus-4":             { input: 15.0, output: 75.0 },
};
const BRIEF_IN = 1200, BRIEF_OUT = 2000, HTML_IN = 3900, HTML_OUT = 6000;

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const db = supabaseAdmin();
  const { data: jobs, error: jobsErr } = await db.from("jobs")
    .select("id,prompt,status,paid,tier,ai_model,stripe_session_id,created_at,expires_at,error,preview_url,download_url,brand_story,brand_story_preview,user_agent,referrer,input_tokens,output_tokens")
    .order("created_at", { ascending: false }).limit(200);
  if (jobsErr) return NextResponse.json({ error: jobsErr.message }, { status: 500 });

  const { data: credits } = await db.from("credits")
    .select("session_id,email,tier,balance,updated_at").order("updated_at", { ascending: false }).limit(200);
  const { data: pvRaw } = await db.from("page_views")
    .select("path,created_at").order("created_at", { ascending: false }).limit(1000);

  const J = jobs ?? [], C = credits ?? [], PV = pvRaw ?? [];
  const totalJobs = J.length;
  const paidJobs  = J.filter(j => j.paid).length;
  const doneJobs  = J.filter(j => j.status === "done").length;
  const errorJobs = J.filter(j => j.status === "error").length;
  const pendingJobs = J.filter(j => j.status === "pending" || j.status === "processing").length;

  const tierCounts: Record<string,number> = {};
  for (const j of J) tierCounts[j.tier] = (tierCounts[j.tier] ?? 0) + 1;

  const dev = { mobile:0, tablet:0, desktop:0, unknown:0 } as Record<string,number>;
  for (const j of J) dev[parseDevice(j.user_agent)]++;

  const allRefs: Record<string,number> = {};
  for (const j of J) { const s = parseReferrer(j.referrer); allRefs[s] = (allRefs[s] ?? 0) + 1; }
  const referrerCounts = Object.fromEntries(Object.entries(allRefs).sort((a,b)=>b[1]-a[1]).slice(0,8));

  const soloRevenue = paidJobs * 999;
  const creditRevenue = C.reduce((s,c) => s + (TIER_REVENUE[c.tier] ?? 0), 0);
  const totalRevenue = soloRevenue + creditRevenue;
  const totalCreditsPurchased = C.length;
  const totalCreditsRemaining = C.reduce((s,c) => s + (c.balance ?? 0), 0);

  const hasRealTokens = J.some(j => j.input_tokens != null);
  let totalInT = 0, totalOutT = 0, costUSD = 0;
  const hp = MODEL_PRICING["claude-haiku-4-5-20251001"];
  for (const j of J) {
    if (!j.ai_model) continue;
    if (hasRealTokens) {
      const i = j.input_tokens ?? 0, o = j.output_tokens ?? 0;
      totalInT += i; totalOutT += o;
      const p = MODEL_PRICING[j.ai_model] ?? hp;
      costUSD += (i * p.input + o * p.output) / 1e6;
    } else {
      const bp = MODEL_PRICING[j.ai_model] ?? hp;
      const bi = BRIEF_IN + Math.ceil((j.prompt?.length ?? 0) / 4);
      totalInT += bi; totalOutT += BRIEF_OUT;
      costUSD += (bi * bp.input + BRIEF_OUT * bp.output) / 1e6;
      const ho = (j.output_tokens ?? 0) > 0 ? j.output_tokens : HTML_OUT;
      const hi = HTML_IN + BRIEF_OUT;
      totalInT += hi; totalOutT += ho;
      costUSD += (hi * hp.input + ho * hp.output) / 1e6;
    }
  }
  const estimatedCostCents = Math.round(costUSD * 100);
  const profit = totalRevenue - estimatedCostCents;
  const totalPageViews = PV.length;
  const viewsByPath: Record<string,number> = {};
  for (const pv of PV) { const p2 = pv.path || "/"; viewsByPath[p2] = (viewsByPath[p2] ?? 0) + 1; }
  const jobsForClient = J.map(({ preview_html: _ph, ...rest }: any) => rest);

  return NextResponse.json({
    _debug: { supabaseUrl: _DEBUG_URL, totalJobsRaw: J.length },
    stats: { totalJobs, paidJobs, doneJobs, errorJobs, pendingJobs, tierCounts, deviceCounts: dev, referrerCounts, soloRevenue, creditRevenue, totalRevenue, totalCreditsPurchased, totalCreditsRemaining, estimatedCostCents, profit, totalInputTokens: totalInT, totalOutputTokens: totalOutT, hasRealTokens, totalPageViews, viewsByPath },
    jobs: jobsForClient, credits: C,
  });
}
