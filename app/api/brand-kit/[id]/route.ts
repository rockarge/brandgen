import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const _BK_DEBUG_URL = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || 'NONE';
const _BK_DEBUG_KEY_SRC = process.env.BG_SERVICE_ROLE_KEY ? 'BG_SERVICE_ROLE_KEY' : (process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SUPABASE_SERVICE_ROLE_KEY' : 'NONE');

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) return new NextResponse("Job ID gerekli", { status: 400 });

  const db = supabaseAdmin();
  const { data, error } = await db
    .from("jobs")
    .select("preview_html, status")
    .eq("id", id)
    .single();

  const debugHeaders = {
    "X-Debug-Supabase-URL": _BK_DEBUG_URL,
    "X-Debug-Key-Src": _BK_DEBUG_KEY_SRC,
    "X-Debug-Data-Status": data?.status ?? "null",
    "X-Debug-Preview-Len": String(data?.preview_html?.length ?? "null"),
    "X-Debug-Error": error ? JSON.stringify(error).substring(0,100) : "none",
  };

  if (error || !data) {
    console.error(`[brand-kit] 404 — id=${id} error=${JSON.stringify(error)}`);
    return new NextResponse("Bulunamad\u0131", { status: 404, headers: debugHeaders });
  }

  console.log(`[brand-kit] id=${id} status=${data.status} preview_html_len=${data.preview_html?.length ?? "null"} supabase=${_BK_DEBUG_URL}`);

  if (data.status !== "done" || !data.preview_html) {
    return new NextResponse("Hen\u00fcz haz\u0131r de\u011fil", { status: 202, headers: debugHeaders });
  }

  return new NextResponse(data.preview_html, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", ...debugHeaders },
  });
}
