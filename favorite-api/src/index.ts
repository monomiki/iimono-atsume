import { Env, assertAuthenticated, corsHeaders } from "./auth";
import { postFavoriteToDiscord } from "./discord";
import { dedupeExists, getFavorite, listFavorites, putFavorite } from "./storage";
import { normalizeUrl, parseFavoriteRequest } from "./validation";

async function jsonResponse(env: Env, request: Request, body: unknown, status = 200): Promise<Response> {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(env, request.headers.get("origin")) },
  });
}

async function loadPublishedItem(env: Env, itemId: string): Promise<any | null> {
  const url = `${env.PUBLIC_DATA_BASE_URL.replace(/\/$/, "")}/data/items/${itemId}.json`;
  const response = await fetch(url, { cf: { cacheTtl: 60 } });
  if (!response.ok) return null;
  return await response.json();
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders(env, request.headers.get("origin")) });
    const url = new URL(request.url);
    try {
      if (url.pathname === "/api/favorites" && request.method === "GET") {
        assertAuthenticated(request, env);
        return jsonResponse(env, request, { items: await listFavorites(env) });
      }
      if (url.pathname.startsWith("/api/favorites/") && request.method === "GET") {
        assertAuthenticated(request, env);
        const itemId = url.pathname.split("/").pop() || "";
        return jsonResponse(env, request, { item: await getFavorite(env, itemId) });
      }
      if (url.pathname === "/api/favorites" && request.method === "POST") {
        assertAuthenticated(request, env);
        const length = Number(request.headers.get("content-length") || "0");
        if (length > 4096) return jsonResponse(env, request, { error: "request too large" }, 413);
        const parsed = parseFavoriteRequest(await request.json());
        const item = await loadPublishedItem(env, parsed.item_id);
        if (!item || item.daily_page !== parsed.daily_page) return jsonResponse(env, request, { error: "item not found" }, 404);
        if (parsed.url && normalizeUrl(parsed.url) !== normalizeUrl(item.normalized_url || item.url)) return jsonResponse(env, request, { error: "url mismatch" }, 400);
        const dedupeKey = normalizeUrl(item.normalized_url || item.url);
        const existing = await getFavorite(env, parsed.item_id);
        if (existing || await dedupeExists(env, dedupeKey)) return jsonResponse(env, request, { status: "already_favorited", item_id: parsed.item_id });
        const dailyUrl = `${env.PUBLIC_DATA_BASE_URL.replace(/\/$/, "")}/daily/${parsed.daily_page}/`;
        const discord = await postFavoriteToDiscord(env.DISCORD_CLIPBOARD_WEBHOOK_URL, item, dailyUrl);
        await putFavorite(env, { item_id: parsed.item_id, dedupe_key: dedupeKey, daily_page: parsed.daily_page, favorited_at: new Date().toISOString(), discord_status: discord.status, discord_message_id: discord.id });
        return jsonResponse(env, request, { status: "favorited", item_id: parsed.item_id, discord_status: discord.status });
      }
      if (url.pathname.startsWith("/api/favorites/") && request.method === "DELETE") {
        assertAuthenticated(request, env);
        return jsonResponse(env, request, { status: "delete_not_enabled" }, 405);
      }
      return jsonResponse(env, request, { error: "not found" }, 404);
    } catch (error) {
      const message = error instanceof Error && error.message === "unauthorized" ? "unauthorized" : "bad request";
      return jsonResponse(env, request, { error: message }, message === "unauthorized" ? 401 : 400);
    }
  },
};

