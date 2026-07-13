import { closeOverlay, hasOpenOverlay, openTaskDrawer, openTodoDrawer } from "./components/drawer.js";
import { openPalette } from "./components/palette.js";
import { parseRoute, projectHash, goTo } from "./router.js";
import { connectEvents } from "./sse.js";
import { getProjectId, getProjectName, getProjects, getTodoSelection, invalidate, loadProject, loadProjects, loadReviews, setTodoSelection, taskStatus, tasksFrom, todoStatus, todosFrom } from "./store.js";
import { element, pulse } from "./ui.js";
import { renderOverview } from "./views/overview.js";
import { renderBoard } from "./views/board.js";
import { renderTodos } from "./views/todos.js";
import { renderRuns } from "./views/runs.js";
import { renderReviews } from "./views/reviews.js";

const root = document.getElementById("main-content");
const projectNav = document.getElementById("project-nav");
const searchTrigger = document.getElementById("search-trigger");
const connection = document.getElementById("connection-status");
let renderVersion = 0;
let route = parseRoute();
let refreshTimer = null;

function health(summary) {
  if (summary.blocked > 0 || summary.failed) return "alert";
  if (summary.running > 0) return "active";
  return "good";
}

function reviewFailed(reviews) {
  return reviews.some((review) => {
    const verdicts = Array.isArray(review && review.verdicts) ? review.verdicts : [review && review.verdicts];
    return verdicts.some((verdict) => /fail|blocked/i.test(String(verdict || "")));
  });
}

async function projectSummary(project) {
  const id = getProjectId(project);
  try {
    const [payload, reviews] = await Promise.all([loadProject(id, "recent"), loadReviews(id)]);
    const details = payload && payload.project && typeof payload.project === "object" ? { ...payload, ...payload.project } : payload || {};
    const tasks = tasksFrom(details);
    return {
      running: tasks.filter((task) => taskStatus(task) === "running").length,
      blocked: tasks.filter((task) => taskStatus(task) === "blocked").length,
      todos: todosFrom(details).filter((todo) => !["done", "closed", "resolved"].includes(todoStatus(todo))).length,
      failed: reviewFailed(reviews),
    };
  } catch {
    return { running: 0, blocked: 0, todos: 0, failed: false };
  }
}

function projectLink(project, summary) {
  const id = getProjectId(project);
  const link = element("a", "project-link");
  link.href = projectHash(id);
  if (route.projectId === id) link.setAttribute("aria-current", "page");
  const initial = element("span", "project-link__initial", getProjectName(project).slice(0, 2).toUpperCase());
  const content = element("span", "project-link__content");
  const line = element("span", "project-link__name", getProjectName(project));
  const meta = element("span", "project-link__meta");
  const dot = element("span", `health-dot health-dot--${health(summary)}`);
  dot.setAttribute("aria-label", health(summary));
  meta.append(dot, element("span", "", `${summary.running} run`), element("span", "", `${summary.blocked} block`), element("span", "", `${summary.todos} todo`));
  content.append(line, meta);
  link.append(initial, content);
  return link;
}

async function renderSidebar(force = false) {
  try {
    await loadProjects(force);
    const projects = getProjects();
    const summaries = await Promise.all(projects.map(projectSummary));
    projectNav.replaceChildren(...projects.map((project, index) => projectLink(project, summaries[index])));
  } catch (error) {
    projectNav.replaceChildren(element("p", "", error && error.message ? error.message : "Projects are unavailable."));
  }
}

async function renderCurrent({ refreshed = false } = {}) {
  route = parseRoute();
  const version = ++renderVersion;
  closeOverlay();
  const context = {
    root,
    route,
    isCurrent: () => version === renderVersion,
    rerender: () => renderCurrent(),
  };
  if (route.name === "overview") await renderOverview(context);
  else if (route.name === "todos") await renderTodos(context);
  else if (route.name === "runs") await renderRuns(context);
  else if (route.name === "reviews") await renderReviews(context);
  else await renderBoard(context);
  if (version === renderVersion && refreshed) pulse(root);
  renderSidebar();
}

function setConnection(status) {
  connection.classList.remove("connection--connected", "connection--disconnected");
  connection.classList.add(status === "connected" ? "connection--connected" : "connection--disconnected");
  const label = connection.querySelector(".connection__label");
  if (label) label.textContent = status === "connected" ? "Live" : "Reconnecting";
}

function refreshFromEvent() {
  if (refreshTimer) window.clearTimeout(refreshTimer);
  refreshTimer = window.setTimeout(async () => {
    refreshTimer = null;
    invalidate();
    await renderSidebar(true);
    await renderCurrent({ refreshed: true });
  }, 160);
}

function chooseSearchResult(result) {
  if (!result || !result.projectId) return;
  if (result.type === "todo") {
    goTo(projectHash(result.projectId, "todos"));
    window.setTimeout(() => openTodoDrawer(result.projectId, result.id), 0);
    return;
  }
  goTo(projectHash(result.projectId));
  if (result.run) window.setTimeout(() => openTaskDrawer(result.projectId, result.run, result.id), 0);
}

function openSearch() {
  openPalette({ onChoose: chooseSearchResult });
}

function moveTodoSelection(direction) {
  if (route.name !== "todos" || hasOpenOverlay()) return false;
  const rows = [...root.querySelectorAll(".todo-row")];
  if (rows.length === 0) return false;
  const index = Math.min(rows.length - 1, Math.max(0, getTodoSelection() + direction));
  rows.forEach((row) => row.classList.toggle("todo-row--selected", Number(row.dataset.todoIndex) === index));
  setTodoSelection(index);
  rows[index].focus();
  return true;
}

searchTrigger.addEventListener("click", openSearch);
window.addEventListener("hashchange", () => renderCurrent());
document.addEventListener("keydown", (event) => {
  const target = event.target;
  const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openSearch();
    return;
  }
  if (event.key === "Escape" && hasOpenOverlay()) {
    event.preventDefault();
    closeOverlay();
    return;
  }
  if (!typing && event.key === "j" && moveTodoSelection(1)) event.preventDefault();
  if (!typing && event.key === "k" && moveTodoSelection(-1)) event.preventDefault();
});

renderSidebar();
renderCurrent();
connectEvents({ onStatus: setConnection, onUpdate: refreshFromEvent });
