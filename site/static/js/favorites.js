(function () {
  const configNode = document.getElementById("site-config");
  const config = configNode ? JSON.parse(configNode.textContent || "{}") : {};
  const apiBase = (config.favoriteApiBaseUrl || "").replace(/\/$/, "");
  const buttons = Array.from(document.querySelectorAll("[data-favorite]"));

  function setUnavailable() {
    buttons.forEach((button) => {
      button.disabled = true;
      button.textContent = "Favorite機能を現在利用できません";
    });
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
          button.classList.add("is-favorited");
          button.textContent = "★ Favorited";
        }
      });
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
      button.classList.add("is-favorited");
      button.textContent = "★ Favorited";
    } catch (error) {
      button.textContent = "Favorite失敗";
      setTimeout(() => { button.textContent = "☆ Favorite"; }, 1800);
    } finally {
      button.disabled = false;
    }
  }

  buttons.forEach((button) => button.addEventListener("click", () => favorite(button)));
  loadFavorites();
})();

