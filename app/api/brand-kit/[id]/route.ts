import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) return new NextResponse("Job ID gerekli", { status: 400 });

  const url = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
  const key = process.env.BG_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

  const resp = await fetch(
    `${url}/rest/v1/jobs?id=eq.${id}&select=preview_html%2Cstatus`,
    { headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: 'application/vnd.pgrst.object+json' } }
  );

  const httpStatus = resp.status;
  let data: any = null;
  try { data = await resp.json(); } catch {}

  const debugH = {
    "X-Debug-URL": url.substring(0,40),
    "X-Debug-Key-Prefix": key.substring(0,30),
    "X-Debug-Supabase-HTTP": String(httpStatus),
    "X-Debug-Data-Status": data?.status ?? "null",
    "X-Debug-Preview-Len": String(data?.preview_html?.length ?? "null"),
    "X-Debug-Supabase-Error": data?.code ?? data?.message ?? "none",
  };

  if (httpStatus !== 200 || !data || data.code) {
    return new NextResponse("Supabase error", { status: 500, headers: debugH });
  }

  if (data.status !== "done" || !data.preview_html) {
    return new NextResponse("Hen\u00fcz haz\u0131r de\u011fil", { status: 202, headers: debugH });
  }

  return new NextResponse(data.preview_html, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", ...debugH },
  });
}
