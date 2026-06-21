import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// supabase-js bypass — native fetch ile direkt REST API
// Neden: supabase-js client module-level cache/realtime nedeniyle stale data dönüyor
async function fetchJob(id: string): Promise<{ status: string; preview_html: string | null } | null> {
  const url  = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
  const key  = process.env.BG_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

  console.log(`[brand-kit/fetchJob] url=${url ? url.slice(0,30) : 'EMPTY'} keySrc=${process.env.BG_SERVICE_ROLE_KEY ? 'BG_SERVICE_ROLE_KEY' : process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SUPABASE_SERVICE_ROLE_KEY' : 'NONE'} keyHint=${key.slice(-8)}`);

  // Array query — admin/stats'ta test edilmiş, büyük preview_html ile de çalışıyor
  const resp = await fetch(
    `${url}/rest/v1/jobs?id=eq.${id}&select=status%2Cpreview_html&limit=1`,
    {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Cache-Control": "no-store",
      },
      cache: "no-store",
    }
  );

  console.log(`[brand-kit/fetchJob] id=${id} httpStatus=${resp.status}`);

  if (!resp.ok) {
    const body = await resp.text().catch(() => '');
    console.error(`[brand-kit/fetchJob] error body=${body.slice(0,200)}`);
    return null;
  }
  try {
    const arr = await resp.json();
    if (!Array.isArray(arr) || arr.length === 0) {
      console.log(`[brand-kit/fetchJob] 0 rows returned`);
      return null;
    }
    const data = arr[0];
    console.log(`[brand-kit/fetchJob] ok status=${data?.status} html_len=${data?.preview_html?.length ?? 'null'}`);
    return data;
  } catch (e) {
    console.error(`[brand-kit/fetchJob] json parse error: ${e}`);
    return null;
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) return new NextResponse("Job ID gerekli", { status: 400 });

  const data = await fetchJob(id);

  if (!data) {
    console.error(`[brand-kit] 404 — id=${id}`);
    return new NextResponse("Bulunamadı", { status: 404 });
  }

  console.log(`[brand-kit] id=${id} status=${data.status} preview_html_len=${data.preview_html?.length ?? "null"}`);

  if (data.status !== "done" || !data.preview_html) {
    return new NextResponse("Henüz hazır değil", { status: 202 });
  }

  return new NextResponse(data.preview_html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
