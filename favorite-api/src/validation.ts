export type FavoriteRequest = {
  item_id: string;
  daily_page: string;
  source?: string;
  url?: string;
};

const ITEM_ID_RE = /^[a-z0-9_-]{3,80}$/i;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function parseFavoriteRequest(body: unknown): FavoriteRequest {
  if (!body || typeof body !== "object") throw new Error("invalid body");
  const data = body as Record<string, unknown>;
  const item_id = String(data.item_id || "");
  const daily_page = String(data.daily_page || "");
  if (!ITEM_ID_RE.test(item_id)) throw new Error("invalid item_id");
  if (!DATE_RE.test(daily_page)) throw new Error("invalid daily_page");
  return { item_id, daily_page, source: String(data.source || ""), url: String(data.url || "") };
}

export function normalizeUrl(url: string): string {
  const parsed = new URL(url);
  parsed.hash = "";
  for (const key of Array.from(parsed.searchParams.keys())) {
    if (key.startsWith("utm_") || ["fbclid", "igshid", "ref"].includes(key)) parsed.searchParams.delete(key);
  }
  if (["fxtwitter.com", "vxtwitter.com", "twitter.com", "www.twitter.com", "www.x.com"].includes(parsed.hostname)) {
    parsed.hostname = "x.com";
  }
  if (["instagram.com", "www.instagram.com"].includes(parsed.hostname)) {
    parsed.hostname = "www.instagram.com";
    parsed.search = "";
  }
  return parsed.toString().replace(/\/$/, "");
}

