import { api } from "./api.js";

const state = {
  projects: [],
  projectCache: new Map(),
  reviewsCache: new Map(),
  scopes: new Map(),
  boardFilters: new Map(),
  runSelections: new Map(),
  todoSelection: 0,
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function readProjects(payload) {
  if (Array.isArray(payload)) return payload;
  return asArray(payload && payload.projects);
}

export function getProjectId(project) {
  return String(project && (project.id ?? project.projectId ?? project.slug ?? project.name) || "");
}

export function getProjectName(project) {
  return String(project && (project.name ?? project.projectName ?? project.id ?? project.slug) || "Untitled project");
}

export function getScope(projectId) {
  return state.scopes.get(projectId) || "recent";
}

export function setScope(projectId, scope) {
  state.scopes.set(projectId, scope === "all" ? "all" : "recent");
}

export function getBoardFilters(projectId) {
  return state.boardFilters.get(projectId) || { run: "", risk: "", lane: "", text: "" };
}

export function setBoardFilters(projectId, patch) {
  state.boardFilters.set(projectId, { ...getBoardFilters(projectId), ...patch });
}

export function selectRun(projectId, run) {
  state.runSelections.set(projectId, run || "");
  setBoardFilters(projectId, { run: run || "" });
}

export function getSelectedRun(projectId) {
  return state.runSelections.get(projectId) || "";
}

export function setTodoSelection(index) {
  state.todoSelection = Math.max(0, index);
}

export function getTodoSelection() {
  return state.todoSelection;
}

export async function loadProjects(force = false) {
  if (!force && state.projects.length > 0) return state.projects;
  const payload = await api.projects();
  state.projects = readProjects(payload);
  return state.projects;
}

export function getProjects() {
  return state.projects;
}

export async function loadProject(projectId, scope = getScope(projectId), force = false) {
  const normalizedScope = scope === "all" ? "all" : "recent";
  const key = `${projectId}:${normalizedScope}`;
  if (!force && state.projectCache.has(key)) return state.projectCache.get(key);
  const payload = await api.project(projectId, normalizedScope);
  state.projectCache.set(key, payload || {});
  return payload || {};
}

export async function loadReviews(projectId, force = false) {
  if (!force && state.reviewsCache.has(projectId)) return state.reviewsCache.get(projectId);
  const payload = await api.reviews(projectId);
  const reviews = asArray(payload && payload.reviews);
  state.reviewsCache.set(projectId, reviews);
  return reviews;
}

export function invalidate() {
  state.projectCache.clear();
  state.reviewsCache.clear();
}

export function runsFrom(project) {
  return asArray(project && project.runs);
}

export function runId(run) {
  return String(run && (run.slug ?? run.id ?? run.run ?? run.name) || "");
}

export function tasksFrom(project) {
  const directTasks = asArray(project && project.tasks);
  const runTasks = runsFrom(project).flatMap((run) => asArray(run && run.tasks).map((task) => ({
    ...task,
    run: task && (task.run ?? task.runSlug) || runId(run),
  })));
  const tasks = directTasks.length > 0 ? directTasks : runTasks;
  return tasks.map((task) => ({ ...task, run: task && (task.run ?? task.runSlug) || "" }));
}

export function todosFrom(project) {
  return asArray(project && project.todos);
}

export function taskId(task) {
  return String(task && (task.id ?? task.taskId ?? task.title) || "");
}

export function taskTitle(task) {
  return String(task && (task.title ?? task.name ?? task.id) || "Untitled task");
}

export function taskStatus(task) {
  const value = String(task && task.status || "pending").toLowerCase();
  return ["pending", "running", "done", "blocked", "stalled"].includes(value) ? value : "pending";
}

export function todoId(todo) {
  return String(todo && (todo.id ?? todo.todoId ?? todo.title) || "");
}

export function todoTitle(todo) {
  return String(todo && (todo.title ?? todo.name ?? todo.id) || "Untitled todo");
}

export function todoPriority(todo) {
  const value = String(todo && todo.priority || "low").toLowerCase();
  return ["high", "medium", "low"].includes(value) ? value : "low";
}

export function todoStatus(todo) {
  return String(todo && todo.status || "other").toLowerCase();
}
