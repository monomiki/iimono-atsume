(function () {
  const configNode = document.getElementById("site-config");
  const config = configNode ? JSON.parse(configNode.textContent || "{}") : {};
  const apiBase = (config.favoriteApiBaseUrl || "").replace(/\/$/, "");
  const buttons = Array.from(document.querySelectorAll("[data-favorite]"));

  function setUnavailable() {
    buttons.forEach((button) => {
      button.disabled = true;
      button.textContent = "☆";
      button.setAttribute("aria-label", "Favorite機能を現在利用できません");
    });
  }

  function setFavoriteState(button, favorited) {
    button.classList.toggle("is-favorited", favorited);
    button.textContent = favorited ? "★" : "☆";
    button.setAttribute("aria-label", favorited ? "Favorited" : "Favorite");
    button.closest(".post-card")?.setAttribute("data-favorite-state", String(favorited));
  }

  async function loadFavorites() {
    if (!apiBase || buttons.length === 0) return;
    try {
      const response = await fetch(`${apiBase}/api/favorites`, { credentials: "include" });
      if (!response.ok) throw new Error("favorite api unavailable");
      const data = await response.json();
      const favoriteIds = new Set((data.items || []).map((item) => item.item_id));
      buttons.forEach((button) => {
        const payload = JSON.parse(button.dataset.favorite || "{}");
        if (favoriteIds.has(payload.item_id)) {
          setFavoriteState(button, true);
        }
      });
      window.dispatchEvent(new CustomEvent("favorite-state-change"));
    } catch (error) {
      setUnavailable();
    }
  }

  async function favorite(button) {
    if (!apiBase) {
      setUnavailable();
      return;
    }
    const payload = JSON.parse(button.dataset.favorite || "{}");
    button.disabled = true;
    try {
      const response = await fetch(`${apiBase}/api/favorites`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("favorite failed");
      setFavoriteState(button, true);
      window.dispatchEvent(new CustomEvent("favorite-state-change"));
    } catch (error) {
      button.textContent = "!";
      button.setAttribute("aria-label", "Favorite失敗");
      setTimeout(() => { setFavoriteState(button, false); }, 1800);
    } finally {
      button.disabled = false;
      window.dispatchEvent(new CustomEvent("masonry:relayout"));
    }
  }

  buttons.forEach((button) => button.addEventListener("click", () => favorite(button)));
  loadFavorites();
})();
