import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

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
    return new NextResponse("Bulunamadı", { status: 404 });
  }

  if (data.status !== "done" || !data.preview_html) {
    return new NextResponse("Henüz hazır değil", { status: 202 });
  }

  return new NextResponse(data.preview_html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
