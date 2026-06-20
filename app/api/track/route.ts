import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const { path } = await req.json();
    const user_agent = req.headers.get("user-agent");
    const referrer   = req.headers.get("referer") ?? req.headers.get("referrer") ?? null;

    const db = supabaseAdmin();
    await db.from("page_views").insert({
      path: path || "/",
      user_agent,
      referrer,
    });

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ ok: false });
  }
}
