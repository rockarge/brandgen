import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get("id");
  if (!jobId) {
    return NextResponse.json({ error: "job id gerekli" }, { status: 400 });
  }

  const db = supabaseAdmin();
  const { data, error } = await db
    .from("jobs")
    .select(
      "id, status, prompt, preview_url, preview_html_url, brand_story_preview, brief_data, error, expires_at"
    )
    .eq("id", jobId)
    .single();

  if (error || !data) {
    return NextResponse.json({ error: "İş bulunamadı." }, { status: 404 });
  }

  return NextResponse.json(data);
}
