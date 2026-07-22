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
          button.innerHTML = '<span aria-hidden="true">★</span><span class="favorite-button__label"> Favorited</span>';
          button.closest(".post-card")?.setAttribute("data-favorite-state", "true");
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
      button.classList.add("is-favorited");
      button.innerHTML = '<span aria-hidden="true">★</span><span class="favorite-button__label"> Favorited</span>';
      button.closest(".post-card")?.setAttribute("data-favorite-state", "true");
      window.dispatchEvent(new CustomEvent("favorite-state-change"));
    } catch (error) {
      button.textContent = "Favorite失敗";
      setTimeout(() => { button.innerHTML = '<span aria-hidden="true">☆</span><span class="favorite-button__label"> Favorite</span>'; }, 1800);
    } finally {
      button.disabled = false;
      window.dispatchEvent(new CustomEvent("masonry:relayout"));
    }
  }

  buttons.forEach((button) => button.addEventListener("click", () => favorite(button)));
  loadFavorites();
})();
