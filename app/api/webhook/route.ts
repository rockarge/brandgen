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

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      const { jobId } = session.metadata || {};

      if (!jobId) break;

      // Mark as paid
      await db
        .from("jobs")
        .update({
          paid: true,
          stripe_session_id: session.id,
        })
        .eq("id", jobId);

      // Trigger backend to generate unwatermarked download
      const BACKEND_URL = process.env.BACKEND_URL || "https://brandgen-api.fly.dev";
      await fetch(`${BACKEND_URL}/finalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      }).catch((e) => console.error("Finalize trigger failed:", e));

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
