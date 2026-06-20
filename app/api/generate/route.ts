import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { randomUUID } from "crypto";

const BACKEND_URL = process.env.BACKEND_URL || "https://brandgen-api.fly.dev";

export async function POST(req: NextRequest) {
  try {
    // tier: free (default Haiku) | solo | starter_pack | studio_pack | pro_pack | agency
    const { prompt, tier = "free" } = await req.json();

    if (!prompt || prompt.trim().length < 10) {
      return NextResponse.json(
        { error: "Prompt çok kısa — en az 10 karakter." },
        { status: 400 }
      );
    }

    const jobId = randomUUID();
    const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();

    // Create job record in Supabase
    const db = supabaseAdmin();
    const { error: dbError } = await db.from("jobs").insert({
      id: jobId,
      prompt: prompt.trim(),
      status: "pending",
      expires_at: expiresAt,
    });

    if (dbError) {
      console.error("DB insert error:", dbError);
      return NextResponse.json({ error: "İş oluşturulamadı." }, { status: 500 });
    }

    // Fire-and-forget: trigger backend generation
    // Backend processes async, updates Supabase when done
    fetch(`${BACKEND_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, prompt: prompt.trim(), tier }),
    }).catch((e) => console.error("Backend trigger failed:", e));

    return NextResponse.json({ jobId });
  } catch (e) {
    console.error("Generate error:", e);
    return NextResponse.json({ error: "Sunucu hatası." }, { status: 500 });
  }
}
