import { api } from "../api.js";
import { button, clear, element, emptyState, focusTrap } from "../ui.js";
import { badge } from "./badges.js";
import { closeOverlay } from "./drawer.js";

const overlayRoot = () => document.getElementById("overlay-root");

function fuzzyScore(query, result) {
  const haystack = `${result.title || ""} ${result.id || ""}`.toLowerCase();
  let cursor = 0;
  let score = 0;
  for (const char of query.toLowerCase()) {
    const found = haystack.indexOf(char, cursor);
    if (found < 0) return -1;
    score += found === cursor ? 4 : 1;
    cursor = found + 1;
  }
  return score;
}

function resultList(results, selected, choose) {
  const list = element("div", "palette__results");
  if (results.length === 0) {
    list.append(emptyState("No matching tasks or todos. Try an ID or another title word."));
    return list;
  }
  results.forEach((result, index) => {
    const row = button("", `palette__result${index === selected ? " palette__result--selected" : ""}`);
    row.append(
      badge(result.type || "item", "neutral"),
      element("span", "palette__title", result.title || result.id || "Untitled"),
      element("span", "palette__meta", `${result.projectName || result.projectId || "project"} · ${result.id || ""}`),
    );
    row.addEventListener("click", () => choose(result));
    list.append(row);
  });
  return list;
}

export function openPalette({ onChoose }) {
  closeOverlay();
  const backdrop = element("div", "palette-backdrop");
  const palette = element("section", "palette");
  palette.setAttribute("role", "dialog");
  palette.setAttribute("aria-modal", "true");
  palette.setAttribute("aria-label", "Global search");
  const input = element("input", "palette__input");
  input.type = "search";
  input.placeholder = "Search tasks and todos…";
  input.setAttribute("aria-label", "Search tasks and todos");
  const resultsRoot = element("div", "palette__results");
  resultsRoot.append(emptyState("Searches all projects. Enter a task or todo title or ID."));
  palette.append(input, resultsRoot);
  backdrop.append(palette);
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeOverlay();
  });
  palette.addEventListener("keydown", (event) => focusTrap(palette, event));
  overlayRoot().append(backdrop);

  let timer = null;
  let selected = 0;
  let results = [];
  let request = 0;

  const choose = (result) => {
    closeOverlay();
    onChoose(result);
  };
  const render = () => {
    clear(resultsRoot).append(resultList(results, selected, choose));
  };
  const search = async () => {
    const query = input.value.trim();
    const requestId = ++request;
    selected = 0;
    if (!query) {
      results = [];
      clear(resultsRoot).append(emptyState("Searches all projects. Enter a task or todo title or ID."));
      return;
    }
    try {
      const payload = await api.search(query);
      if (requestId !== request) return;
      results = (Array.isArray(payload && payload.results) ? payload.results : [])
        .map((result) => ({ result, score: fuzzyScore(query, result) }))
        .filter(({ score }) => score >= 0)
        .sort((a, b) => b.score - a.score)
        .map(({ result }) => result);
      render();
    } catch {
      if (requestId !== request) return;
      results = [];
      clear(resultsRoot).append(emptyState("Search is temporarily unavailable."));
    }
  };

  input.addEventListener("input", () => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(search, 100);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && results.length > 0) {
      event.preventDefault();
      selected = (selected + 1) % results.length;
      render();
    } else if (event.key === "ArrowUp" && results.length > 0) {
      event.preventDefault();
      selected = (selected - 1 + results.length) % results.length;
      render();
    } else if (event.key === "Enter" && results[selected]) {
      event.preventDefault();
      choose(results[selected]);
    }
  });
  input.focus();
}
