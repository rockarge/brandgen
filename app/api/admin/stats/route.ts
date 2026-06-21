import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

// DEBUG: hangi Supabase URL kullaniliyor?
const _DEBUG_URL = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || 'NONE';

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return false;
  const auth = req.headers.get("x-admin-secret") ?? req.nextUrl.searchParams.get("secret");
  return auth === secret;
}

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = supabaseAdmin();
  const { data: jobs, error: jobsErr } = await db
    .from("jobs")
    .select("id,prompt,status,paid")
    .order("created_at", { ascending: false })
    .limit(5);

  return NextResponse.json({
    _debug: { supabaseUrl: _DEBUG_URL, jobCount: jobs?.length ?? 0, firstId: jobs?.[0]?.id ?? null },
    jobs: jobs ?? [],
    error: jobsErr?.message ?? null
  });
}
