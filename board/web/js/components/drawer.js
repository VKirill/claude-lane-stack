import { api } from "../api.js";
import { button, clear, element, errorState, focusTrap, loading } from "../ui.js";
import { priorityBadge, statusBadge } from "./badges.js";

const overlayRoot = () => document.getElementById("overlay-root");

export function hasOpenOverlay() {
  return overlayRoot().childElementCount > 0;
}

export function closeOverlay() {
  clear(overlayRoot());
}

function drawerShell(label) {
  closeOverlay();
  const backdrop = element("div", "drawer-backdrop");
  const drawer = element("aside", "drawer");
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-label", label);
  drawer.tabIndex = -1;
  backdrop.append(drawer);
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeOverlay();
  });
  drawer.addEventListener("keydown", (event) => focusTrap(drawer, event));
  overlayRoot().append(backdrop);
  drawer.focus();
  return drawer;
}

function drawerHeader(title) {
  const header = element("header", "drawer__header");
  header.append(element("h2", "", title));
  const close = button("×", "drawer__close");
  close.setAttribute("aria-label", "Close drawer");
  close.addEventListener("click", closeOverlay);
  header.append(close);
  return header;
}

function section(title, child) {
  const container = element("section", "drawer__section");
  container.append(element("h3", "", title), child);
  return container;
}

function scalarMeta(payload, omit = []) {
  const meta = element("dl", "drawer__meta");
  Object.entries(payload || {}).forEach(([key, value]) => {
    if (omit.includes(key) || value === null || value === undefined || typeof value === "object") return;
    meta.append(element("dt", "", key), element("dd", "", String(value)));
  });
  return meta;
}

function taskContent(task) {
  const content = document.createDocumentFragment();
  content.append(drawerHeader(String(task.title || task.id || "Task")));
  content.append(section("Task fields", scalarMeta(task, ["objective", "done_when", "report"])));

  if (task.objective) {
    content.append(section("Objective", element("pre", "drawer__pre", task.objective)));
  }
  if (Array.isArray(task.done_when) && task.done_when.length > 0) {
    const list = element("ul", "");
    task.done_when.forEach((item) => list.append(element("li", "", item)));
    content.append(section("Done when", list));
  }
  if (task.report) {
    content.append(section("Artifact report (first 60 lines)", element("pre", "drawer__pre", task.report)));
  }
  return content;
}

function todoContent(todo) {
  const meta = todo && todo.meta && typeof todo.meta === "object" ? todo.meta : {};
  const content = document.createDocumentFragment();
  content.append(drawerHeader(String(meta.title || meta.id || "Todo")));
  const metaLine = element("div", "task-card__meta");
  if (meta.status) metaLine.append(statusBadge(meta.status));
  if (meta.priority) metaLine.append(priorityBadge(meta.priority));
  if (meta.id) metaLine.append(element("span", "task-card__run", meta.id));
  content.append(metaLine, section("Todo fields", scalarMeta(meta)));
  content.append(section("Markdown body", element("pre", "drawer__pre", todo && todo.body || "")));
  return content;
}

export async function openTaskDrawer(projectId, run, taskId) {
  const drawer = drawerShell("Task details");
  loading(drawer, 6);
  try {
    const task = await api.task(projectId, run, taskId);
    clear(drawer).append(taskContent(task || {}));
  } catch (error) {
    clear(drawer).append(drawerHeader("Task details"), errorState(error));
  }
}

export async function openTodoDrawer(projectId, todoId) {
  const drawer = drawerShell("Todo details");
  loading(drawer, 5);
  try {
    const todo = await api.todo(projectId, todoId);
    clear(drawer).append(todoContent(todo || {}));
  } catch (error) {
    clear(drawer).append(drawerHeader("Todo details"), errorState(error));
  }
}
