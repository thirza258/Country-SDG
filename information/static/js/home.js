(function () {
  "use strict";
  let live = JSON.parse(document.getElementById("live-data").textContent);
  const countries = JSON.parse(document.getElementById("map-data").textContent);
  const select = document.getElementById("map-indicator");
  const paths = Array.from(document.querySelectorAll(".map-country"));
  const detail = document.getElementById("map-detail");
  const status = document.getElementById("source-status");
  const reportNote = document.getElementById("map-note").textContent;
  const reportYear = document.querySelector(".atlas-map-panel").dataset.reportYear;
  const palette = ["#dcecf4", "#afd4e6", "#78b4d1", "#398db5", "#00689d"];
  const number = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });
  const date = new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const dateText = value => value ? date.format(new Date(value)) : "";
  const activeIndicator = () => live.indicators.find(item => item.id === select.value);
  let activePath = null;

  function valueFor(code) {
    if (select.value === "index") {
      return countries[code] ? { value: countries[code].score, year: Number(reportYear) } : null;
    }
    const indicator = activeIndicator();
    return indicator && indicator.observations[code] || null;
  }

  function describe(path) {
    const observation = valueFor(path.dataset.code);
    const indicator = activeIndicator();
    const name = countries[path.dataset.code]?.name || path.dataset.name;
    const value = observation ? number.format(observation.value) + (indicator ? "%" : " / 100") + " · " + observation.year : "No observation available";
    return { name: name, value: value, label: name + ": " + value };
  }

  function showCountry(path) {
    activePath = path;
    const description = describe(path);
    detail.firstElementChild.textContent = description.name;
    detail.lastElementChild.textContent = description.value;
  }

  function renderMap() {
    const indicator = activeIndicator();
    const values = indicator ? Object.values(indicator.observations).map(item => item.value) : [];
    const maximum = values.length ? Math.max(5, Math.ceil(Math.max(...values) / 5) * 5) : 100;
    paths.forEach(path => {
      const observation = valueFor(path.dataset.code);
      const bucket = observation ? (indicator ? Math.floor(observation.value / maximum * 5) : Math.floor((observation.value - 40) / 10)) : null;
      path.setAttribute("fill", bucket === null ? "var(--map-empty)" : palette[Math.max(0, Math.min(4, bucket))]);
      const description = describe(path);
      path.querySelector("title").textContent = description.label;
      if (path.parentNode.matches("a")) {
        path.parentNode.setAttribute("aria-label", description.label + ". Open " + reportYear + " report profile.");
      }
    });
    document.getElementById("map-title").textContent = indicator ? indicator.title + " around the world" : "SDG Index scores around the world";
    document.getElementById("legend-label").textContent = indicator ? "%" : "SDG Index";
    document.getElementById("legend-range").textContent = indicator ? Array.from({ length: 6 }, (_, i) => number.format(i * maximum / 5)).join(" / ") : "<50 / 50 / 60 / 70 / 80+";
    document.getElementById("map-note").textContent = indicator ? "UN SDG " + indicator.sdg + " · Latest available year per country. Darker = a higher percentage. Country links open " + reportYear + " report profiles." : reportNote;
    detail.firstElementChild.textContent = indicator ? indicator.title : "Explore the map";
    detail.lastElementChild.textContent = "Point to a country to see its " + (indicator ? "observation" : "score");
    if (activePath) showCountry(activePath);
  }

  paths.forEach(path => {
    path.addEventListener("pointerenter", () => showCountry(path));
    if (path.parentNode.matches("a")) path.parentNode.addEventListener("focus", () => showCountry(path));
  });
  select.addEventListener("change", renderMap);
  document.querySelectorAll("[data-measure]").forEach(button => {
    button.addEventListener("click", () => {
      select.value = button.dataset.measure;
      renderMap();
      select.focus({ preventScroll: true });
      document.querySelector(".atlas-map-panel").scrollIntoView({ block: "center" });
    });
  });

  function renderSources() {
    const resources = [live.world_bank, live.hubs, ...live.indicators];
    const fresh = resources.every(item => item.status === "fresh");
    status.dataset.status = fresh ? "fresh" : "stale";
    status.textContent = fresh ? "Sources checked · " + dateText(live.world_bank.fetched_at) : "Some sources unavailable · showing saved data where available";
    live.indicators.forEach(indicator => {
      const card = document.querySelector('[data-indicator="' + indicator.id + '"]');
      if (!card) return;
      card.querySelector('[data-field="count"]').textContent = indicator.area_count || "—";
      card.querySelector('[data-field="date"]').textContent = indicator.latest_year ? "Latest observation: " + indicator.latest_year : "Observations unavailable";
      card.querySelector('[data-field="freshness"]').textContent = indicator.fetched_at ? (indicator.status === "fresh" ? "Source checked " : "Saved data from ") + dateText(indicator.fetched_at) : "Source temporarily unavailable";
    });
    document.getElementById("dataset-date").textContent = "UN Sustainable Development Goals dataset" + (live.world_bank.published_at ? " · Release " + dateText(live.world_bank.published_at) : "") + (live.world_bank.status === "fresh" ? "" : " · Saved metadata");
    if (live.hubs.items && live.hubs.items.length) {
      const list = document.getElementById("hub-list");
      list.replaceChildren();
      live.hubs.items.forEach(hub => {
        if (!hub.url.startsWith("https://")) return;
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = hub.url;
        link.textContent = hub.title + " ↗";
        const time = document.createElement("time");
        time.dateTime = hub.modified;
        time.textContent = dateText(hub.modified);
        item.append(link, time);
        list.append(item);
      });
    }
    document.getElementById("hub-status").textContent = live.hubs.fetched_at ? (live.hubs.status === "fresh" ? "Catalogue checked " : "Saved catalogue from ") + dateText(live.hubs.fetched_at) : "SDG.org updates are temporarily unavailable.";
    renderMap();
  }

  let refreshing = false;
  let lastAttempt = 0;
  async function refresh() {
    if (refreshing || document.hidden || Date.now() - lastAttempt < 60000) return;
    refreshing = true;
    lastAttempt = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(document.getElementById("latest").dataset.endpoint, { signal: controller.signal, headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("Source request failed");
      const next = await response.json();
      if (!Array.isArray(next.indicators) || !next.world_bank || !next.hubs) throw new Error("Invalid source response");
      live = next;
      renderSources();
    } catch (_) {
      status.dataset.status = "stale";
      status.textContent = "Update unavailable · showing saved data where available";
    } finally {
      clearTimeout(timeout);
      refreshing = false;
    }
  }

  const filter = document.getElementById("table-filter");
  const rows = Array.from(document.querySelectorAll("#all-countries tbody tr"));
  const fold = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  filter.addEventListener("input", () => {
    const needle = fold(filter.value.trim());
    let visible = 0;
    rows.forEach(row => { row.hidden = !fold(row.textContent).includes(needle); if (!row.hidden) visible++; });
    document.getElementById("country-count").textContent = visible + (visible === 1 ? " country" : " countries");
    document.getElementById("no-countries").hidden = visible !== 0;
  });
  const overview = document.querySelector(".historical-overview");
  overview.addEventListener("toggle", () => {
    if (overview.open && !overview.dataset.rendered) {
      SDGCharts.lineChart(document.querySelector('[data-chart="world-trend"]'), JSON.parse(document.getElementById("chart-data").textContent).world);
      overview.dataset.rendered = "true";
    }
  });
  renderSources();
  refresh();
  setInterval(refresh, 300000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
})();
