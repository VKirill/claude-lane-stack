import { goTo, projectHash } from "../router.js";
import { getProjectName, getProjects, getScope, loadProject, runId, runsFrom, selectRun, taskStatus } from "../store.js";
import { element, emptyState, errorState, formatDate, loading } from "../ui.js";
import { statusBadge } from "../components/badges.js";

function details(payload) {
  return payload && payload.project && typeof payload.project === "object" ? { ...payload, ...payload.project } : payload || {};
}

function projectName(projectId) {
  return getProjectName(getProjects().find((project) => String(project.id ?? project.projectId ?? project.slug ?? project.name) === projectId));
}

function tabs(projectId) {
  const nav = element("nav", "view-tabs");
  nav.setAttribute("aria-label", "Project views");
  [["board", "Board"], ["todos", "Todos"], ["runs", "Runs"], ["reviews", "Reviews"]].forEach(([section, label]) => {
    const link = element("a", `view-tabs__link${section === "runs" ? " view-tabs__link--active" : ""}`, label);
    link.href = projectHash(projectId, section);
    if (section === "runs") link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  return nav;
}

function taskCounts(run) {
  const counts = new Map();
  (Array.isArray(run.tasks) ? run.tasks : []).forEach((task) => {
    const status = taskStatus(task);
    counts.set(status, (counts.get(status) || 0) + 1);
  });
  return counts;
}

function runRow(projectId, run) {
  const tasks = Array.isArray(run.tasks) ? run.tasks : [];
  const counts = taskCounts(run);
  const done = counts.get("done") || 0;
  const total = tasks.length || Number(run.totalTasks) || 0;
  const row = document.createElement("button");
  row.type = "button";
  row.className = "run-row";
  const lead = element("div", "");
  lead.append(element("div", "run-row__title", runId(run)), element("div", "run-row__meta", formatDate(run.lastActivity)));
  const progress = element("div", "");
  progress.append(element("div", "run-row__meta", `${done}/${total} done`));
  const bar = element("div", "progress");
  const value = element("div", "progress__value");
  value.style.width = `${total > 0 ? Math.min(100, Math.round(done / total * 100)) : 0}%`;
  bar.append(value);
  progress.append(bar);
  const meta = element("div", "");
  const chips = element("div", "run-row__statuses");
  [...counts.entries()].forEach(([status, count]) => {
    const chip = statusBadge(status);
    chip.textContent = `${status}:${count}`;
    chips.append(chip);
  });
  meta.append(chips);
  const merged = run.merged;
  if (merged) meta.append(element("div", "run-row__meta", `Merged ${merged.date || ""}${merged.commit ? ` · ${merged.commit}` : ""}`));
  row.append(lead, progress, meta);
  row.addEventListener("click", () => {
    selectRun(projectId, runId(run));
    goTo(projectHash(projectId));
  });
  return row;
}

export async function renderRuns({ root, route, isCurrent }) {
  loading(root, 6);
  try {
    const project = details(await loadProject(route.projectId, getScope(route.projectId)));
    if (!isCurrent()) return;
    const page = document.createDocumentFragment();
    const header = element("header", "page-header");
    const heading = element("div", "");
    heading.append(element("h1", "", "Runs"), element("p", "", `${project.name || project.projectName || projectName(route.projectId)} · newest activity first.`));
    header.append(heading, tabs(route.projectId));
    page.append(header);
    const list = element("section", "run-list");
    const runs = [...runsFrom(project)].sort((left, right) => String(right.lastActivity || "").localeCompare(String(left.lastActivity || "")));
    if (runs.length === 0) list.append(emptyState("No runs are available in the selected scope."));
    runs.forEach((run) => list.append(runRow(route.projectId, run)));
    page.append(list);
    root.replaceChildren(page);
  } catch (error) {
    if (isCurrent()) root.replaceChildren(errorState(error));
  }
}
