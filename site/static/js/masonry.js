(function () {
  const ROW_HEIGHT = 8;
  const GAP = 16;
  let scheduled = false;

  function grids() {
    return Array.from(document.querySelectorAll("[data-masonry]"));
  }

  function layoutGrid(grid) {
    const cards = Array.from(grid.querySelectorAll(".post-card:not([hidden])"));
    grid.style.setProperty("--masonry-row", `${ROW_HEIGHT}px`);
    cards.forEach((card) => {
      card.style.gridRowEnd = "auto";
      const height = card.getBoundingClientRect().height;
      const span = Math.max(1, Math.ceil((height + GAP) / (ROW_HEIGHT + GAP)));
      card.style.gridRowEnd = `span ${span}`;
    });
  }

  function relayout() {
    scheduled = false;
    document.documentElement.classList.add("masonry-ready");
    grids().forEach(layoutGrid);
  }

  function scheduleLayout() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(relayout);
  }

  function collapseLongText(card) {
    const body = card.querySelector("[data-collapsible]");
    if (!body || body.dataset.collapsibleReady) return;
    body.dataset.collapsibleReady = "true";
    const lineHeight = parseFloat(getComputedStyle(body).lineHeight) || 24;
    const maxHeight = lineHeight * 10;
    if (body.scrollHeight <= maxHeight + 4) return;
    body.classList.add("is-collapsed");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "read-more-button";
    button.textContent = "続きを読む";
    button.addEventListener("click", () => {
      const collapsed = body.classList.toggle("is-collapsed");
      button.textContent = collapsed ? "続きを読む" : "折りたたむ";
      scheduleLayout();
    });
    body.after(button);
  }

  function wireDetails(card) {
    card.querySelectorAll("details").forEach((details) => {
      if (details.dataset.layoutReady) return;
      details.dataset.layoutReady = "true";
      details.addEventListener("toggle", scheduleLayout);
    });
  }

  function wireTallMedia(card) {
    card.querySelectorAll(".post-card__media").forEach((media) => {
      if (media.dataset.tallReady) return;
      media.dataset.tallReady = "true";
      requestAnimationFrame(() => {
        if (media.scrollHeight < 720) return;
        media.classList.add("post-card__media--very-tall");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "image-expand-button";
        button.textContent = "画像全体を見る";
        button.addEventListener("click", () => {
          const expanded = media.classList.toggle("is-expanded");
          button.textContent = expanded ? "画像を折りたたむ" : "画像全体を見る";
          scheduleLayout();
        });
        media.after(button);
        scheduleLayout();
      });
    });
  }

  function applyFilters() {
    const params = new URLSearchParams(window.location.search);
    const kind = params.get("view") || "all";
    const category = params.get("category") || "";
    const source = params.get("source") || "";
    const date = params.get("date") || "";
    const favoriteOnly = params.get("favorite") === "true";
    const sort = params.get("sort") || "score";

    document.querySelectorAll(".filter-chip").forEach((chip) => {
      chip.classList.toggle("is-active", chip.dataset.filterKind === kind || (kind === "all" && chip.dataset.filterKind === "all"));
    });
    const categoryField = document.getElementById("category-filter");
    const sourceField = document.getElementById("source-filter");
    const dateField = document.getElementById("date-filter");
    const sortField = document.getElementById("sort-filter");
    if (categoryField) categoryField.value = category;
    if (sourceField) sourceField.value = source;
    if (dateField) dateField.value = date;
    if (sortField) sortField.value = sort;

    grids().forEach((grid) => {
      const cards = Array.from(grid.querySelectorAll(".post-card"));
      cards.forEach((card) => {
        const matchesKind =
          kind === "all" ||
          (kind === "high" && (Number(card.dataset.score || "0") >= 60 || card.dataset.destination === "high")) ||
          (kind === "discovery" && card.dataset.discovery === "true") ||
          kind === "favorite";
        const matchesCategory = !category || card.dataset.category === category;
        const matchesSource = !source || card.dataset.source === source;
        const matchesDate = !date || (card.dataset.date || "").startsWith(date);
        const matchesFavorite = !favoriteOnly || card.dataset.favoriteState === "true";
        const show = matchesKind && matchesCategory && matchesSource && matchesDate && matchesFavorite;
        card.hidden = !show;
      });
      const visible = cards.filter((card) => !card.hidden);
      visible.sort((a, b) => {
        if (sort === "favorite") {
          const favoriteDelta = Number(b.dataset.favoriteState === "true") - Number(a.dataset.favoriteState === "true");
          if (favoriteDelta) return favoriteDelta;
          return Number(b.dataset.score || "0") - Number(a.dataset.score || "0");
        }
        if (sort === "new") return String(b.dataset.date || "").localeCompare(String(a.dataset.date || ""));
        return Number(b.dataset.score || "0") - Number(a.dataset.score || "0");
      });
      visible.forEach((card) => grid.appendChild(card));
    });
    scheduleLayout();
  }

  function setParam(name, value) {
    const params = new URLSearchParams(window.location.search);
    if (value) params.set(name, value);
    else params.delete(name);
    const query = params.toString();
    history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
    applyFilters();
  }

  function wireFilters() {
    document.querySelectorAll(".filter-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const kind = chip.dataset.filterKind || "all";
        const params = new URLSearchParams(window.location.search);
        if (kind === "all") {
          params.delete("view");
          params.delete("favorite");
        } else {
          params.set("view", kind);
          if (kind === "favorite") params.set("favorite", "true");
          else params.delete("favorite");
        }
        const query = params.toString();
        history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
        applyFilters();
      });
    });
    const category = document.getElementById("category-filter");
    const source = document.getElementById("source-filter");
    const date = document.getElementById("date-filter");
    const sort = document.getElementById("sort-filter");
    if (category) category.addEventListener("change", () => setParam("category", category.value));
    if (source) source.addEventListener("change", () => setParam("source", source.value));
    if (date) date.addEventListener("change", () => setParam("date", date.value));
    if (sort) sort.addEventListener("change", () => setParam("sort", sort.value));
  }

  function wireDensity() {
    const button = document.querySelector("[data-density-toggle]");
    const compact = localStorage.getItem("density") === "compact";
    document.documentElement.classList.toggle("is-compact-density", compact);
    if (button) {
      button.classList.toggle("is-compact", compact);
      button.textContent = compact ? "コンパクト表示" : "標準表示";
      button.addEventListener("click", () => {
        const next = !document.documentElement.classList.contains("is-compact-density");
        document.documentElement.classList.toggle("is-compact-density", next);
        button.classList.toggle("is-compact", next);
        button.textContent = next ? "コンパクト表示" : "標準表示";
        localStorage.setItem("density", next ? "compact" : "standard");
        scheduleLayout();
      });
    }
  }

  function initCards() {
    document.querySelectorAll(".post-card").forEach((card) => {
      collapseLongText(card);
      wireDetails(card);
      wireTallMedia(card);
      card.querySelectorAll("img, video").forEach((media) => {
        media.addEventListener("load", scheduleLayout, { once: false });
        media.addEventListener("loadedmetadata", scheduleLayout, { once: false });
      });
    });
  }

  function observe() {
    const resizeObserver = new ResizeObserver(() => scheduleLayout());
    grids().forEach((grid) => resizeObserver.observe(grid));
    document.querySelectorAll(".post-card").forEach((card) => resizeObserver.observe(card));
    const mutationObserver = new MutationObserver(() => {
      initCards();
      scheduleLayout();
    });
    grids().forEach((grid) => mutationObserver.observe(grid, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "class"] }));
    window.addEventListener("resize", scheduleLayout);
    window.addEventListener("favorite-state-change", applyFilters);
    window.addEventListener("masonry:relayout", scheduleLayout);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initCards();
    wireFilters();
    wireDensity();
    observe();
    applyFilters();
    scheduleLayout();
  });
})();
