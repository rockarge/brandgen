import { createClient } from "@supabase/supabase-js";

// NEXT_PUBLIC_* → build-time inline; SUPABASE_* → runtime fallback
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Server-side (service role — API routes only)
export const supabaseAdmin = () =>
  createClient(supabaseUrl, process.env.SUPABASE_SERVICE_ROLE_KEY!, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

export type Job = {
  id: string;
  prompt: string;
  status: "pending" | "processing" | "done" | "error";
  preview_url: string | null;
  download_url: string | null;
  brand_story: string | null;
  brand_story_preview: string | null;
  stripe_session_id: string | null;
  paid: boolean;
  error: string | null;
  expires_at: string;
  created_at: string;
};
