import { NextRequest, NextResponse } from "next/server";

// Success page'den çağrılır: session_id'yi bg_session cookie'sine yazar
export async function POST(req: NextRequest) {
  const { session_id } = await req.json();

  if (!session_id || typeof session_id !== "string") {
    return NextResponse.json({ error: "session_id gerekli" }, { status: 400 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set("bg_session", session_id, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 90, // 90 gün
    path: "/",
  });
  return res;
}
