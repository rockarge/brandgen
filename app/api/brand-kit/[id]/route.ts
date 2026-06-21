import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// supabase-js bypass — native fetch ile direkt REST API
// Neden: supabase-js client module-level cache/realtime nedeniyle stale data dönüyor
async function fetchJob(id: string): Promise<{ status: string; preview_html: string | null } | null> {
  const url  = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
  const key  = process.env.BG_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

  const resp = await fetch(
    `${url}/rest/v1/jobs?id=eq.${id}&select=preview_html%2Cstatus`,
    {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: "application/vnd.pgrst.object+json",
      },
      cache: "no-store",
    }
  );

  if (resp.status === 406) return null;
  if (!resp.ok) return null;
  try { return await resp.json(); } catch { return null; }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) return new NextResponse("Job ID gerekli", { status: 400 });

  const data = await fetchJob(id);

  if (!data) {
    console.error(`[brand-kit] 404 \u2014 id=${id}`);
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
