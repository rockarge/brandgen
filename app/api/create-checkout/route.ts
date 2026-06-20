import { NextRequest, NextResponse } from "next/server";
import { stripe, PRICES, BillingInterval, PlanTier } from "@/lib/stripe";
import { supabaseAdmin } from "@/lib/supabase";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

// Tek seferlik paket planları (mode: payment, inline price_data)
const ONE_TIME_PACKS: PlanTier[] = ["starter_pack", "studio_pack", "pro_pack"];

export async function POST(req: NextRequest) {
  try {
    const {
      jobId,
      tier = "solo" as PlanTier,
      billing = "monthly" as BillingInterval,
    } = await req.json();

    const db = supabaseAdmin();
    let session;

    if (tier === "solo") {
      // Solo: job bazlı tek seferlik ödeme (üretim sonrası)
      if (!jobId) {
        return NextResponse.json({ error: "jobId gerekli" }, { status: 400 });
      }

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

      const plan = PRICES.solo;
      session = await stripe.checkout.sessions.create({
        mode: "payment",
        payment_method_types: ["card"],
        line_items: [
          {
            price_data: {
              currency: plan.currency,
              unit_amount: plan.amount,
              product_data: { name: plan.name, description: plan.description },
            },
            quantity: 1,
          },
        ],
        success_url: `${APP_URL}/success/${jobId}?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${APP_URL}/preview/${jobId}`,
        metadata: { jobId, tier },
        expires_at: Math.floor(Date.now() / 1000) + 30 * 60,
      });

      await db
        .from("jobs")
        .update({ stripe_session_id: session.id })
        .eq("id", jobId);

    } else if (ONE_TIME_PACKS.includes(tier)) {
      // Paket planlar: tek seferlik ödeme, jobId opsiyonel
      const plan = PRICES[tier] as { amount: number; currency: string; name: string; description: string };

      const successUrl = jobId
        ? `${APP_URL}/success/${jobId}?session_id={CHECKOUT_SESSION_ID}&pack=${tier}`
        : `${APP_URL}/?pack_purchased=${tier}&session_id={CHECKOUT_SESSION_ID}`;

      const cancelUrl = jobId
        ? `${APP_URL}/preview/${jobId}`
        : `${APP_URL}/#pricing`;

      session = await stripe.checkout.sessions.create({
        mode: "payment",
        payment_method_types: ["card"],
        line_items: [
          {
            price_data: {
              currency: plan.currency,
              unit_amount: plan.amount,
              product_data: { name: plan.name, description: plan.description },
            },
            quantity: 1,
          },
        ],
        success_url: successUrl,
        cancel_url: cancelUrl,
        metadata: { jobId: jobId ?? "", tier },
      });

      if (jobId) {
        await db
          .from("jobs")
          .update({ stripe_session_id: session.id })
          .eq("id", jobId);
      }

    } else if (tier === "agency") {
      // Agency: abonelik (inline price_data ile subscription)
      const plan = PRICES.agency;
      const priceConfig = billing === "yearly" ? plan.yearly : plan.monthly;

      const successUrl = jobId
        ? `${APP_URL}/success/${jobId}?session_id={CHECKOUT_SESSION_ID}`
        : `${APP_URL}/?subscribed=true&session_id={CHECKOUT_SESSION_ID}`;

      const cancelUrl = jobId
        ? `${APP_URL}/preview/${jobId}`
        : `${APP_URL}/#pricing`;

      session = await stripe.checkout.sessions.create({
        mode: "subscription",
        payment_method_types: ["card"],
        line_items: [
          {
            price_data: {
              currency: plan.currency,
              unit_amount: priceConfig.amount,
              recurring: { interval: priceConfig.interval },
              product_data: { name: plan.name, description: plan.description },
            },
            quantity: 1,
          },
        ],
        success_url: successUrl,
        cancel_url: cancelUrl,
        metadata: { jobId: jobId ?? "", tier, billing },
      });

      if (jobId) {
        await db
          .from("jobs")
          .update({ stripe_session_id: session.id })
          .eq("id", jobId);
      }

    } else {
      return NextResponse.json({ error: "Geçersiz plan." }, { status: 400 });
    }

    return NextResponse.json({ url: session.url });
  } catch (e) {
    console.error("Checkout error:", e);
    return NextResponse.json({ error: "Ödeme oturumu oluşturulamadı." }, { status: 500 });
  }
}
