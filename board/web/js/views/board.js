import { projectHash } from "../router.js";
import { getBoardFilters, getProjectName, getProjects, getScope, loadProject, runId, runsFrom, setBoardFilters, setScope, taskId, taskStatus, taskTitle, tasksFrom } from "../store.js";
import { button, element, emptyState, errorState, loading } from "../ui.js";
import { riskBadge, statusBadge, verifyBadge } from "../components/badges.js";
import { openTaskDrawer } from "../components/drawer.js";

const statuses = ["pending", "running", "done", "blocked", "stalled"];

function details(payload) {
  return payload && payload.project && typeof payload.project === "object" ? { ...payload, ...payload.project } : payload || {};
}

function projectName(projectId) {
  return getProjectName(getProjects().find((project) => String(project.id ?? project.projectId ?? project.slug ?? project.name) === projectId));
}

function tabs(projectId, active) {
  const nav = element("nav", "view-tabs");
  nav.setAttribute("aria-label", "Project views");
  [["board", "Board"], ["todos", "Todos"], ["runs", "Runs"], ["reviews", "Reviews"]].forEach(([section, label]) => {
    const link = element("a", `view-tabs__link${section === active ? " view-tabs__link--active" : ""}`, label);
    link.href = projectHash(projectId, section);
    if (section === active) link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  return nav;
}

function option(value, label, selected) {
  const node = element("option", "", label);
  node.value = value;
  node.selected = value === selected;
  return node;
}

function filterBar(projectId, project, rerender) {
  const filters = getBoardFilters(projectId);
  const bar = element("form", "filter-bar");
  bar.setAttribute("aria-label", "Board filters");
  bar.addEventListener("submit", (event) => event.preventDefault());
  const scope = element("div", "scope-toggle");
  ["recent", "all"].forEach((value) => {
    const label = value === "recent" ? "Recent work" : "All history";
    const toggle = button(label, `button${getScope(projectId) === value ? " button--active" : " button--quiet"}`);
    toggle.setAttribute("aria-pressed", String(getScope(projectId) === value));
    toggle.addEventListener("click", () => {
      setScope(projectId, value);
      rerender();
    });
    scope.append(toggle);
  });
  bar.append(scope);
  const run = element("select", "");
  run.setAttribute("aria-label", "Filter by run");
  run.append(option("", "All runs", filters.run));
  runsFrom(project).forEach((item) => run.append(option(runId(item), runId(item), filters.run)));
  const risks = [...new Set(tasksFrom(project).map((task) => task.risk).filter(Boolean))].sort();
  const risk = element("select", "");
  risk.setAttribute("aria-label", "Filter by risk");
  risk.append(option("", "All risks", filters.risk));
  risks.forEach((item) => risk.append(option(String(item), String(item), filters.risk)));
  const lanes = [...new Set(tasksFrom(project).map((task) => task.lane).filter(Boolean))].sort();
  const lane = element("select", "");
  lane.setAttribute("aria-label", "Filter by lane");
  lane.append(option("", "All lanes", filters.lane));
  lanes.forEach((item) => lane.append(option(String(item), String(item), filters.lane)));
  const text = element("input", "");
  text.type = "search";
  text.placeholder = "Filter title or ID";
  text.value = filters.text;
  text.setAttribute("aria-label", "Filter task title or ID");
  const apply = () => {
    setBoardFilters(projectId, { run: run.value, risk: risk.value, lane: lane.value, text: text.value });
    rerender();
  };
  run.addEventListener("change", apply);
  risk.addEventListener("change", apply);
  lane.addEventListener("change", apply);
  text.addEventListener("input", apply);
  bar.append(run, risk, lane, text);
  return bar;
}

function matches(task, filters) {
  const haystack = `${taskTitle(task)} ${taskId(task)}`.toLowerCase();
  return (!filters.run || task.run === filters.run)
    && (!filters.risk || String(task.risk || "") === filters.risk)
    && (!filters.lane || String(task.lane || "") === filters.lane)
    && (!filters.text || haystack.includes(filters.text.toLowerCase()));
}

function taskCard(projectId, task) {
  const status = taskStatus(task);
  const card = button("", `task-card task-card--${status}`);
  const run = String(task.run || "");
  const titleSpan = element("span", "task-card__title", taskTitle(task));
  titleSpan.setAttribute("title", taskTitle(task));
  card.append(titleSpan);
  const meta = element("span", "task-card__meta");
  const idText = run ? `${taskId(task)} / ${run}` : taskId(task);
  const idChip = element("span", "task-card__id-chip", idText);
  idChip.setAttribute("title", idText);
  meta.append(idChip);
  if (task.risk) meta.append(riskBadge(task.risk));
  if (task.verify) meta.append(verifyBadge(task.verify));
  if (task.lane) meta.append(element("span", "task-card__lane", task.lane));
  card.append(meta);
  card.addEventListener("click", () => openTaskDrawer(projectId, run, taskId(task)));
  return card;
}

function column(projectId, status, tasks) {
  const column = element("section", `board-column${status === "done" ? " board-column--collapsed" : ""}`);
  const header = button("", `board-column__header${status !== "done" ? " board-column__header--static" : ""}`);
  if (status !== "done") header.disabled = true;
  header.append(element("span", "board-column__name", status), element("span", "board-column__count", String(tasks.length)));
  if (status === "done") {
    header.setAttribute("aria-expanded", "false");
    header.addEventListener("click", () => {
      const collapsed = column.classList.toggle("board-column--collapsed");
      header.setAttribute("aria-expanded", String(!collapsed));
    });
  }
  const body = element("div", "board-column__body");
  if (tasks.length === 0) body.append(emptyState("No tasks in this column."));
  tasks.forEach((task) => body.append(taskCard(projectId, task)));
  column.append(header, body);
  return column;
}

export async function renderBoard({ root, route, isCurrent, rerender }) {
  loading(root, 6);
  try {
    const project = details(await loadProject(route.projectId, getScope(route.projectId)));
    if (!isCurrent()) return;
    const page = document.createDocumentFragment();
    const header = element("header", "page-header");
    const heading = element("div", "");
    heading.append(element("h1", "", project.name || project.projectName || projectName(route.projectId)), element("p", "", "Task board · recent work is the default scope."));
    header.append(heading, tabs(route.projectId, "board"));
    page.append(header, filterBar(route.projectId, project, rerender));
    const filters = getBoardFilters(route.projectId);
    const visible = tasksFrom(project).filter((task) => matches(task, filters));
    const board = element("section", "board");
    board.setAttribute("aria-label", "Task board");
    statuses.forEach((status) => board.append(column(route.projectId, status, visible.filter((task) => taskStatus(task) === status))));
    page.append(board);
    root.replaceChildren(page);
  } catch (error) {
    if (isCurrent()) root.replaceChildren(errorState(error));
  }
}
