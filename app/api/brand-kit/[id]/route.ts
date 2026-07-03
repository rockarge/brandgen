/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║  /api/brand-kit/[id] — HTML brand kit servis route'u                    ║
 * ║  Deploy: deploy.command (çift tıkla) → GitHub ROOT → Vercel             ║
 * ║                                                                           ║
 * ║  NE YAPAR: Supabase jobs tablosundan preview_html okur, tarayıcıya gönderir
 * ║  BAĞIMLILIK: jobs.preview_html (backend tarafından yazılır)             ║
 * ║  BOZULURSA: brand-kit sayfası açılmaz / boş gelir                       ║
 * ║  DOKUNMA: sadece HTTP response formatı veya cache header değişince       ║
 * ║  generators/ — ASLA bu dosyadan erişilmez (farklı katman: Fly.io)       ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// supabase-js bypass — native fetch ile direkt REST API
// Neden: supabase-js client module-level cache/realtime nedeniyle stale data dönüyor
type FetchResult = { status: string; preview_html: string | null } | null;

async function fetchJob(id: string): Promise<FetchResult> {
  const url = process.env.BG_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
  const key = process.env.BG_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

  try {
    const resp = await fetch(
      `${url}/rest/v1/jobs?id=eq.${id}&select=status%2Cpreview_html&limit=1`,
      {
        headers: { apikey: key, Authorization: `Bearer ${key}`, "Cache-Control": "no-store" },
        cache: "no-store",
      }
    );

    if (!resp.ok) return null;

    const arr = await resp.json();
    if (!Array.isArray(arr) || arr.length === 0) return null;
    return arr[0] as FetchResult;
  } catch {
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
