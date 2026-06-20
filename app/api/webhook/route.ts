import { NextRequest, NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { supabaseAdmin } from "@/lib/supabase";
import Stripe from "stripe";

// Next.js App Router: raw body için bodyParser kapatmaya gerek yok
// stripe.webhooks.constructEvent req.text() ile zaten raw body okur
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature")!;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, sig, webhookSecret);
  } catch (e) {
    console.error("Webhook signature failed:", e);
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  const db = supabaseAdmin();

  // Paket tier → üretim hakkı sayısı
  const PACK_BALANCE: Record<string, number> = {
    starter_pack: 5,
    studio_pack:  15,
    pro_pack:     30,
    agency:       60,
  };

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      const { jobId, tier } = session.metadata || {};
      const email = session.customer_details?.email ?? null;

      // ── Solo / job bazlı ödeme ──────────────────────────────────────────
      if (jobId) {
        await db
          .from("jobs")
          .update({ paid: true, stripe_session_id: session.id })
          .eq("id", jobId);

        const BACKEND_URL = process.env.BACKEND_URL || "https://brandgen-api.fly.dev";
        await fetch(`${BACKEND_URL}/finalize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: jobId }),
        }).catch((e) => console.error("Finalize trigger failed:", e));
      }

      // ── Paket satın alımı → credits tablosuna yaz ───────────────────────
      if (tier && PACK_BALANCE[tier]) {
        await db.from("credits").upsert(
          {
            session_id: session.id,
            email,
            tier,
            balance:    PACK_BALANCE[tier],
            updated_at: new Date().toISOString(),
          },
          { onConflict: "session_id" }
        );
      }

      break;
    }

    case "checkout.session.expired": {
      // No action needed — job stays in DB, user can retry
      break;
    }

    default:
      console.log(`Unhandled event: ${event.type}`);
  }

  return NextResponse.json({ received: true });
}
