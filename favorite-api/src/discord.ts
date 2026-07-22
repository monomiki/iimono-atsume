export async function postFavoriteToDiscord(webhookUrl: string, item: any, dailyUrl: string): Promise<{ status: "sent" | "pending"; id?: string }> {
  if (!webhookUrl) return { status: "pending" };
  const response = await fetch(webhookUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      content: "⭐ Favoriteに追加されました",
      embeds: [{
        title: item.title,
        url: item.normalized_url || item.url,
        description: String(item.excerpt || "").slice(0, 240),
        fields: [
          { name: "カテゴリ", value: item.category || "unknown", inline: true },
          { name: "推薦スコア", value: String(item.score || "-"), inline: true },
          { name: "収集日", value: item.daily_page || "", inline: true },
          { name: "日次まとめ", value: dailyUrl, inline: false },
        ],
        footer: { text: "AI Daily Collection" },
      }],
    }),
  });
  if (!response.ok) return { status: "pending" };
  const text = await response.text();
  if (!text) return { status: "sent" };
  try {
    const data = JSON.parse(text);
    return { status: "sent", id: data.id };
  } catch {
    return { status: "sent" };
  }
}

