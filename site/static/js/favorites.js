(function () {
  const configNode = document.getElementById("site-config");
  const config = configNode ? JSON.parse(configNode.textContent || "{}") : {};
  const apiBase = (config.favoriteApiBaseUrl || "").replace(/\/$/, "");
  const buttons = Array.from(document.querySelectorAll("[data-favorite]"));
  const STORAGE_KEY = "ai-daily-favorite-tags";

  function readTags() {
    try {
      return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));
    } catch (error) {
      return new Set();
    }
  }

  function writeTags(tags) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(tags)));
  }

  function payloadFor(button) {
    try {
      return JSON.parse(button.dataset.favorite || "{}");
    } catch (error) {
      return {};
    }
  }

  function syncCardState(button, favorited) {
    const card = button.closest(".post-card");
    if (!card) return;
    card.setAttribute("data-favorite-state", String(favorited));
  }

  function setFavoriteState(button, favorited) {
    button.classList.toggle("is-favorited", favorited);
    button.textContent = favorited ? "★" : "☆";
    button.setAttribute("aria-label", favorited ? "Favoriteタグを外す" : "Favoriteタグを付ける");
    button.setAttribute("aria-pressed", String(favorited));
    syncCardState(button, favorited);
  }

  async function loadFavorites() {
    if (buttons.length === 0) return;
    const favoriteIds = readTags();
    buttons.forEach((button) => {
      const payload = payloadFor(button);
      setFavoriteState(button, favoriteIds.has(payload.item_id));
    });
    window.dispatchEvent(new CustomEvent("favorite-state-change"));
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/favorites`, { credentials: "include" });
      if (!response.ok) throw new Error("favorite api unavailable");
      const data = await response.json();
      (data.items || []).forEach((item) => favoriteIds.add(item.item_id));
      writeTags(favoriteIds);
      buttons.forEach((button) => {
        const payload = payloadFor(button);
        setFavoriteState(button, favoriteIds.has(payload.item_id));
      });
      window.dispatchEvent(new CustomEvent("favorite-state-change"));
    } catch (error) {
      // API is optional. Local tags continue to work without it.
    }
  }

  function toggleFavorite(button) {
    const payload = payloadFor(button);
    if (!payload.item_id) return;
    const favoriteIds = readTags();
    const next = !favoriteIds.has(payload.item_id);
    if (next) favoriteIds.add(payload.item_id);
    else favoriteIds.delete(payload.item_id);
    writeTags(favoriteIds);
    setFavoriteState(button, next);
    window.dispatchEvent(new CustomEvent("favorite-state-change"));
    window.dispatchEvent(new CustomEvent("masonry:relayout"));
  }

  buttons.forEach((button) => button.addEventListener("click", () => toggleFavorite(button)));
  loadFavorites();
})();
