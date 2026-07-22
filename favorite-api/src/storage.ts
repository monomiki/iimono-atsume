import { Env } from "./auth";

export type FavoriteRecord = {
  item_id: string;
  dedupe_key: string;
  daily_page: string;
  favorited_at: string;
  discord_status: "sent" | "pending" | "tagged";
  discord_message_id?: string;
};

export async function getFavorite(env: Env, itemId: string): Promise<FavoriteRecord | null> {
  return await env.FAVORITES.get(`favorite:${itemId}`, "json") as FavoriteRecord | null;
}

export async function listFavorites(env: Env): Promise<FavoriteRecord[]> {
  const listed = await env.FAVORITES.list({ prefix: "favorite:" });
  const records = await Promise.all(listed.keys.map((key) => env.FAVORITES.get(key.name, "json") as Promise<FavoriteRecord | null>));
  return records.filter(Boolean) as FavoriteRecord[];
}

export async function putFavorite(env: Env, record: FavoriteRecord): Promise<void> {
  await env.FAVORITES.put(`favorite:${record.item_id}`, JSON.stringify(record));
  await env.FAVORITES.put(`dedupe:${record.dedupe_key}`, record.item_id);
}

export async function dedupeExists(env: Env, dedupeKey: string): Promise<boolean> {
  return Boolean(await env.FAVORITES.get(`dedupe:${dedupeKey}`));
}
