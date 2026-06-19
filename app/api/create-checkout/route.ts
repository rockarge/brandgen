import { NextRequest, NextResponse } from "next/server";
import { stripe, PRICES, BillingInterval, PlanTier } from "@/lib/stripe";
import { supabaseAdmin } from "@/lib/supabase";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export async function POST(req: NextRequest) {
  try {
    const {
      jobId,
      tier = "single" as PlanTier,
      billing = "monthly" as BillingInterval,
    } = await req.json();

    if (!jobId) {
      return NextResponse.json({ error: "jobId gerekli" }, { status: 400 });
    }

    // Verify job exists
    const db = supabaseAdmin();
    const { data: job, error } = await db
      .from("jobs")
      .select("id, status, paid")
      .eq("id", jobId)
      .single();

    if (error || !job) {
      return NextResponse.json({ error: "İş bulunamadı." }, { status: 404 });
    }

    if (job.paid) {
      return NextResponse.json({
        url: `${APP_URL}/success/${jobId}?already_paid=true`,
      });
    }

    if (job.status !== "done") {
      return NextResponse.json(
        { error: "Üretim henüz tamamlanmadı." },
        { status: 400 }
      );
    }

    let session;

    if (tier === "single") {
      // One-time payment
      session = await stripe.checkout.sessions.create({
        mode: "payment",
        payment_method_types: ["card"],
        line_items: [
          {
            price_data: {
              currency: PRICES.single.currency,
              unit_amount: PRICES.single.amount,
              product_data: {
                name: PRICES.single.name,
                description: PRICES.single.description,
              },
            },
            quantity: 1,
          },
        ],
        success_url: `${APP_URL}/success/${jobId}?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${APP_URL}/preview/${jobId}`,
        metadata: { jobId, tier },
        expires_at: Math.floor(Date.now() / 1000) + 30 * 60, // 30 min
      });
    } else {
      // Subscription tiers (starter / pro / agency) — aylık veya yıllık
      const planPrices = PRICES[tier as keyof typeof PRICES] as {
        monthly: string;
        yearly: string;
      };
      const priceId =
        billing === "yearly" ? planPrices.yearly : planPrices.monthly;

      session = await stripe.checkout.sessions.create({
        mode: "subscription",
        payment_method_types: ["card"],
        line_items: [{ price: priceId, quantity: 1 }],
        success_url: `${APP_URL}/success/${jobId}?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${APP_URL}/preview/${jobId}`,
        metadata: { jobId, tier, billing },
      });
    }

    // Store session id
    await db
      .from("jobs")
      .update({ stripe_session_id: session.id })
      .eq("id", jobId);

    return NextResponse.json({ url: session.url });
  } catch (e) {
    console.error("Checkout error:", e);
    return NextResponse.json({ error: "Ödeme oturumu oluşturulamadı." }, { status: 500 });
  }
}
