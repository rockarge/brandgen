import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) {
    return new NextResponse("Job ID gerekli", { status: 400 });
  }

  const db = supabaseAdmin();
  const { data, error } = await db
    .from("jobs")
    .select("preview_html, status")
    .eq("id", id)
    .single();

  if (error || !data) {
    console.error(`[brand-kit] 404 — id=${id} error=${JSON.stringify(error)}`);
    return new NextResponse("Bulunamad\u0131", { status: 404 });
  }

  console.log(`[brand-kit] id=${id} status=${data.status} preview_html_len=${data.preview_html?.length ?? "null"}`);

  if (data.status !== "done" || !data.preview_html) {
    return new NextResponse("Hen\u00fcz haz\u0131r de\u011fil", { status: 202 });
  }

  return new NextResponse(data.preview_html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
