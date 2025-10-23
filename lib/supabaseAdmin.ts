import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

let cachedClient: SupabaseClient | null = null;

export const hasSupabaseAdmin = Boolean(supabaseUrl && supabaseServiceRoleKey);

export function getSupabaseAdmin(): SupabaseClient | null {
  if (!hasSupabaseAdmin) {
    return null;
  }
  if (!cachedClient) {
    cachedClient = createClient(supabaseUrl!, supabaseServiceRoleKey!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });
  }
  return cachedClient;
}
